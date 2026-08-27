"""Registered LV-009 preflight and reader generation runner."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import os
import subprocess
import time
import urllib.error
from collections import Counter, defaultdict
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from analysis.hh001_endpoints import contains_gold, normalize
from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.hh001_stats import exact_sign_test
from analysis.locomo_nf_development import sha256_file
from analysis.lv002_live import _gold_records, majority
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX
from analysis.lv009_exploration import ARMS, PROMPTS, ROOT, SELECTIONS, ordered_schedule, load_blind_population
from analysis.lv009_runtime import SERVER, complete


REGISTRATION = ROOT / "LV_009_PRE_REGISTRATION.md"
PART1 = ROOT / "artifacts" / "part1" / "part1.json"
TOKEN_AUDIT = ROOT / "artifacts" / "part1" / "token_audit.json"
READER_PROBES = ROOT / "artifacts" / "part1" / "reader_probes.json"
JUDGE_PROBES = ROOT / "artifacts" / "part1" / "judge_probes.json"
PREFLIGHT = ROOT / "artifacts" / "preflight" / "preflight.json"
ANSWERS = ROOT / "artifacts" / "run" / "answers.jsonl"
GENERATION_SUMMARY = ROOT / "artifacts" / "run" / "generation_summary.json"
BLIND_SURFACE = ROOT / "artifacts" / "scoring" / "blind_surface.jsonl.gz"
BLIND_MAPPING = ROOT / "artifacts" / "scoring" / "blind_mapping.sealed.json"
JUDGMENTS = ROOT / "artifacts" / "scoring" / "blind_judgments.jsonl"
JUDGMENT_SUMMARY = ROOT / "artifacts" / "scoring" / "judgment_summary.json"
RESULT = ROOT / "artifacts" / "result" / "result.json"
PER_ITEM = ROOT / "artifacts" / "result" / "per_item.csv"
MODEL_SOURCE = Path(r"C:\Users\muzaf\.cache\huggingface\hub\models--unsloth--Qwen3.8-27B-GGUF\snapshots\f1bfb127c64f7072bdd2cad55f258b9c8b2910fe\Qwen3.8-27B-UD-Q4_K_XL.gguf")
SERVER_BINARY = Path(r"C:\Users\muzaf\.unsloth\llama.cpp\build\bin\Release\llama-server.exe")
MODEL_SOURCE_SHA256 = "bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372"
SERVER_BINARY_SHA256 = "125e0938a280cba46c803a60178e51826203e030abacce03367a22108720f7ac"
REGISTRATION_SHA256 = "b0b6c7806ecdf8dd9be6f070ff4595d749a72feab1eb3add8e851d05eb7cf8bb"
PART1_SHA256 = "4a2a275d2658ee05eeefd4887706fedcf398e75ba08d83732ad5be192230da13"
PROMPTS_SHA256 = "98a0d0a3e00f78dfa222bd6d2cb6c49093dd7ae5f5f005b2a8de1412d14fc454"
SELECTIONS_SHA256 = "35ab1fd17299163dfd11b1b6d84f583203982f9325e2e56bc38ed08129802315"
READER_LIMIT = 8_192
JUDGE_LIMIT = 4_096
JUDGE_SEEDS = (9_100, 9_101, 9_102)
PRIMARY_CATEGORIES = (1, 2, 3, 4)
DEVELOPMENT_IDS = frozenset({"conv-41", "conv-42", "conv-47", "conv-48"})
COMPARISONS = (
    ("FULL_vs_PAIRWISE", "PAIRWISE", "COMMUNITY_QB"),
    ("QUESTION_EACH_INCREMENT", "COMMUNITY_QB", "COMMUNITY_QEACH"),
    ("COMMUNITY_vs_PAIRWISE", "PAIRWISE", "COMMUNITY"),
    ("QUESTION_REPEAT_INCREMENT", "COMMUNITY", "COMMUNITY_QB"),
    ("QUESTION_EACH_vs_PAIRWISE", "PAIRWISE", "COMMUNITY_QEACH"),
)


class LV009LiveError(RuntimeError):
    pass


def _read_prompts() -> list[dict[str, Any]]:
    with gzip.open(PROMPTS, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def _append_fsynced(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")
        handle.flush()
        os.fsync(handle.fileno())


def _write_gzip_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def _read_gzip_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _git_sealed(*paths: Path) -> bool:
    repo = ROOT.parents[2]
    relative = [str(path.relative_to(repo)).replace("\\", "/") for path in paths]
    tracked = subprocess.run(
        ["git", "ls-files", "--error-unmatch", *relative], cwd=repo, capture_output=True
    ).returncode == 0
    clean = subprocess.run(
        ["git", "diff", "--quiet", "HEAD", "--", *relative], cwd=repo
    ).returncode == 0
    return tracked and clean


def blind_id(comparison_key: str, arm: str) -> str:
    return hashlib.sha256(
        f"lv009-blind-v1\0{comparison_key}\0{arm}".encode("utf-8")
    ).hexdigest()


def judge_prompt(item: Mapping[str, Any]) -> str:
    return (
        render_judge_prompt(str(item["question"]), str(item["gold"]), str(item["answer"]))
        + CLOSED_THINK_SUFFIX
        + "VERDICT:"
    )


def _get(path: str) -> dict[str, Any]:
    import urllib.request
    with urllib.request.urlopen(SERVER + path, timeout=30.0) as response:
        return json.loads(response.read().decode("utf-8"))


def _gpu_record() -> dict[str, Any]:
    result = subprocess.run(
        ["nvidia-smi", "--query-gpu=name,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits"],
        text=True, capture_output=True, check=True,
    )
    fields = [value.strip() for value in result.stdout.strip().split(",")]
    if len(fields) != 4:
        raise LV009LiveError("unexpected nvidia-smi output")
    record = {"name": fields[0], "total_mib": int(fields[1]), "used_mib": int(fields[2]), "free_mib": int(fields[3])}
    record["resident"] = record["name"] == "NVIDIA GeForce RTX 5090" and record["used_mib"] >= 20_000
    return record


def validate_answer_schedule(rows: Sequence[Mapping[str, Any]], prompts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected = {(row["comparison_key"], arm) for row in prompts for arm in ARMS}
    actual = [(row["comparison_key"], row["arm"]) for row in rows]
    completed = {
        (row["comparison_key"], row["arm"])
        for row in rows
        if row.get("response", {}).get("complete") and row.get("response", {}).get("response_bytes", 0) > 0
    }
    return {
        "rows": len(rows), "expected": len(expected),
        "duplicates": len(actual) - len(set(actual)),
        "missing": len(expected - set(actual)), "extra": len(set(actual) - expected),
        "completed": len(completed),
        "length_stops": sum(row.get("response", {}).get("stop_type") == "limit" for row in rows),
        "pass": len(rows) == len(expected) and len(actual) == len(set(actual)) and set(actual) == expected and completed == expected,
    }


def _structural_checks(prompts: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    set_exact = element_exact = reminders = qeach_active = 0
    for row in prompts:
        selected = set(row["selected_ids"])
        baseline_hashes = row["arms"]["PAIRWISE"]["episode_element_sha256"]
        groups = len(row["arms"]["COMMUNITY_QB"]["groups"])
        reminder = f"<question_reminder>Question to answer: {row['question']}</question_reminder>"
        for arm in ARMS:
            value = row["arms"][arm]
            set_exact += len(value["emitted_ids"]) == len(selected) and set(value["emitted_ids"]) == selected
            element_exact += value["episode_element_sha256"] == baseline_hashes
        count = row["arms"]["COMMUNITY_QEACH"]["prompt"].count(reminder)
        reminders += count == groups - 1
        qeach_active += groups >= 2 and row["arms"]["COMMUNITY_QEACH"]["prompt_sha256"] != row["arms"]["COMMUNITY_QB"]["prompt_sha256"]
    return {
        "set_exact": set_exact, "expected_set_exact": len(prompts) * len(ARMS),
        "element_exact": element_exact, "expected_element_exact": len(prompts) * len(ARMS),
        "reminder_rows": reminders, "qeach_active_rows": qeach_active,
    }


def run_preflight() -> dict[str, Any]:
    anchors = {
        "registration": sha256_file(REGISTRATION) == REGISTRATION_SHA256,
        "part1": sha256_file(PART1) == PART1_SHA256,
        "prompts": sha256_file(PROMPTS) == PROMPTS_SHA256,
        "selections": sha256_file(SELECTIONS) == SELECTIONS_SHA256,
        "model_source": sha256_file(MODEL_SOURCE) == MODEL_SOURCE_SHA256,
        "server_binary": sha256_file(SERVER_BINARY) == SERVER_BINARY_SHA256,
        "registration_ancestor": subprocess.run(
            ["git", "merge-base", "--is-ancestor", "950a17f1", "HEAD"],
            cwd=ROOT.parents[2], capture_output=True,
        ).returncode == 0,
    }
    if not all(anchors.values()):
        raise LV009LiveError(f"registered anchor drift: {anchors}")
    prompts = _read_prompts()
    if len(prompts) != 1_986 or len({row["comparison_key"] for row in prompts}) != 1_986:
        raise LV009LiveError("prompt population drift")
    primary = [row for row in prompts if row["category"] in (1, 2, 3, 4)]
    checks = _structural_checks(prompts)
    token_audit = json.loads(TOKEN_AUDIT.read_text(encoding="utf-8"))
    reader_probes = json.loads(READER_PROBES.read_text(encoding="utf-8"))
    judge_probes = json.loads(JUDGE_PROBES.read_text(encoding="utf-8"))
    props = _get("/props")
    params = props["default_generation_settings"]["params"]
    gpu = _gpu_record()
    passing = (
        len(primary) == 1_540
        and checks["set_exact"] == checks["expected_set_exact"]
        and checks["element_exact"] == checks["expected_element_exact"]
        and checks["reminder_rows"] == 1_986
        and checks["qeach_active_rows"] >= 1_540
        and token_audit["rows"] == 7_944
        and token_audit["all_context_safe_at_reader_cap"]
        and reader_probes["all_nonempty"] and reader_probes["all_context_safe"]
        and judge_probes["all_nonempty"] and all(row["parseable_surface"] for row in judge_probes["rows"])
        and int(props["total_slots"]) == 1
        and int(props["default_generation_settings"]["n_ctx"]) == 65_536
        and params["speculative.types"] == "none"
        and gpu["resident"]
    )
    result = {
        "schema": "lv009-preflight-v1", "status": "PASS" if passing else "FAIL",
        "anchors": anchors, "population": {"rows": len(prompts), "primary": len(primary), "prompts": len(prompts) * len(ARMS)},
        "checks": checks, "token_audit": token_audit, "reader_probes": reader_probes,
        "judge_probes": judge_probes, "server": {"props": props, "gpu": gpu},
        "registration_commit": "950a17f1",
    }
    _write_json(PREFLIGHT, result)
    if not passing:
        raise LV009LiveError("LV-009 Preflight failed")
    return result


def run_generation() -> dict[str, Any]:
    preflight = json.loads(PREFLIGHT.read_text(encoding="utf-8")) if PREFLIGHT.exists() else run_preflight()
    if preflight.get("status") != "PASS":
        raise LV009LiveError("generation requires passing Preflight")
    prompts = _read_prompts()
    by_key = {row["comparison_key"]: row for row in prompts}
    existing = _read_jsonl(ANSWERS)
    validation = validate_answer_schedule(existing, prompts)
    if validation["duplicates"] or validation["extra"]:
        raise LV009LiveError("existing answer ledger has duplicate or extra keys")
    completed = {(row["comparison_key"], row["arm"]) for row in existing}
    schedule = ordered_schedule(load_blind_population())
    started = time.time()
    for comparison_key, arm, seed in schedule:
        if (comparison_key, arm) in completed:
            continue
        prompt_row = by_key[comparison_key]
        prompt = prompt_row["arms"][arm]["prompt"]
        attempts = []
        for attempt in range(2):
            try:
                response = complete(prompt, seed=seed, n_predict=READER_LIMIT)
            except (OSError, TimeoutError, urllib.error.URLError) as error:
                attempts.append({"attempt": attempt + 1, "transport_error": repr(error)})
                if attempt == 0:
                    continue
                raise LV009LiveError("unresolved mechanical transport failure") from error
            text = response.pop("_text")
            response["complete"] = True
            response["text"] = text
            attempts.append({"attempt": attempt + 1, "transport_error": None})
            break
        if response["prompt_tokens"] + READER_LIMIT >= 65_536:
            raise LV009LiveError("reader context overflow")
        gpu = _gpu_record()
        if not gpu["resident"]:
            raise LV009LiveError("GPU residency lost")
        _append_fsynced(ANSWERS, {
            "comparison_key": comparison_key, "sample_id": prompt_row["sample_id"],
            "source_index": prompt_row["source_index"], "category": prompt_row["category"],
            "arm": arm, "seed": seed, "prompt_sha256": prompt_row["arms"][arm]["prompt_sha256"],
            "attempts": attempts, "response": response,
        })
        completed.add((comparison_key, arm))
    rows = _read_jsonl(ANSWERS)
    validation = validate_answer_schedule(rows, prompts)
    summary = {
        "schema": "lv009-generation-summary-v1", "validation": validation,
        "answers_sha256": sha256_file(ANSWERS), "wall_seconds": round(time.time() - started, 3),
        "gpu_after": _gpu_record(), "server_after": _get("/props"),
    }
    _write_json(GENERATION_SUMMARY, summary)
    if not validation["pass"]:
        raise LV009LiveError("generation schedule incomplete")
    return summary


def prepare_blind() -> dict[str, Any]:
    if BLIND_SURFACE.exists() or BLIND_MAPPING.exists():
        raise LV009LiveError("blind artifacts already exist")
    if not GENERATION_SUMMARY.exists() or not _git_sealed(ANSWERS, GENERATION_SUMMARY):
        raise LV009LiveError("answers and generation summary must be committed before blinding")
    summary = json.loads(GENERATION_SUMMARY.read_text(encoding="utf-8"))
    answers = _read_jsonl(ANSWERS)
    prompts = _read_prompts()
    if not summary["validation"]["pass"] or sha256_file(ANSWERS) != summary["answers_sha256"]:
        raise LV009LiveError("sealed complete answers required")
    if not validate_answer_schedule(answers, prompts)["pass"]:
        raise LV009LiveError("answer schedule failed at blind boundary")
    gold = _gold_records()
    surface: list[dict[str, Any]] = []
    mapping: dict[str, Any] = {}
    for row in answers:
        if int(row["category"]) not in PRIMARY_CATEGORIES:
            continue
        record = gold[(str(row["sample_id"]), int(row["source_index"]))]
        identifier = blind_id(str(row["comparison_key"]), str(row["arm"]))
        surface.append({
            "blind_id": identifier,
            "question": record["question"],
            "gold": record["gold"],
            "answer": row["response"]["text"],
        })
        mapping[identifier] = {
            "comparison_key": row["comparison_key"],
            "arm": row["arm"],
        }
    surface.sort(key=lambda row: row["blind_id"])
    if len(surface) != 6_160 or len(mapping) != 6_160:
        raise LV009LiveError("blind population drift")
    _write_gzip_rows(BLIND_SURFACE, surface)
    _write_json(BLIND_MAPPING, {"schema": "lv009-blind-mapping-v1", "mapping": mapping})
    return {
        "surface": len(surface),
        "surface_sha256": sha256_file(BLIND_SURFACE),
        "mapping_sha256": sha256_file(BLIND_MAPPING),
    }


def validate_judgments(
    rows: Sequence[Mapping[str, Any]], surface: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    actual = [(str(row["blind_id"]), int(row["judge_pass"]), int(row["seed"])) for row in rows]
    expected = {
        (str(item["blind_id"]), judge_pass, seed)
        for item in surface
        for judge_pass, seed in enumerate(JUDGE_SEEDS)
    }
    counts = Counter(key[0] for key in actual)
    parseable = all(isinstance(row.get("verdict"), bool) for row in rows)
    passing = (
        len(rows) == len(expected)
        and len(actual) == len(set(actual))
        and set(actual) == expected
        and len(counts) == len(surface)
        and all(value == 3 for value in counts.values())
        and parseable
    )
    return {
        "rows": len(rows), "expected": len(expected), "ids": len(counts),
        "duplicates": len(actual) - len(set(actual)), "missing": len(expected - set(actual)),
        "extra": len(set(actual) - expected), "three_each": all(value == 3 for value in counts.values()),
        "parseable": parseable, "length_stops": sum(row.get("stop_type") == "limit" for row in rows),
        "pass": passing,
    }


def run_judging() -> dict[str, Any]:
    if not BLIND_SURFACE.exists() or not BLIND_MAPPING.exists():
        raise LV009LiveError("blind artifacts required")
    if not _git_sealed(BLIND_SURFACE, BLIND_MAPPING):
        raise LV009LiveError("blind surface and sealed mapping must be committed before judging")
    surface = _read_gzip_rows(BLIND_SURFACE)
    existing = _read_jsonl(JUDGMENTS)
    expected = {
        (str(item["blind_id"]), judge_pass, seed)
        for item in surface
        for judge_pass, seed in enumerate(JUDGE_SEEDS)
    }
    actual = {(str(row["blind_id"]), int(row["judge_pass"]), int(row["seed"])) for row in existing}
    if len(existing) != len(actual) or not actual.issubset(expected):
        raise LV009LiveError("existing judgment ledger is not a unique registered subset")
    for item in surface:
        prompt = judge_prompt(item)
        for judge_pass, seed in enumerate(JUDGE_SEEDS):
            key = (str(item["blind_id"]), judge_pass, seed)
            if key in actual:
                continue
            response = complete(prompt, seed=seed, n_predict=JUDGE_LIMIT, temperature=0.2)
            generated = response.pop("_text")
            try:
                verdict, reason = parse_judge_verdict(generated)
            except Exception as error:
                raise LV009LiveError(f"unparseable judgment {key}") from error
            if response["prompt_tokens"] + JUDGE_LIMIT >= 65_536:
                raise LV009LiveError("judge context overflow")
            gpu = _gpu_record()
            if not gpu["resident"]:
                raise LV009LiveError("GPU residency lost during judging")
            _append_fsynced(JUDGMENTS, {
                "blind_id": item["blind_id"], "judge_pass": judge_pass, "seed": seed,
                "verdict": verdict, "reason": reason, **response,
            })
            actual.add(key)
    rows = _read_jsonl(JUDGMENTS)
    validation = validate_judgments(rows, surface)
    summary = {
        "schema": "lv009-judgment-summary-v1", "calls": len(rows),
        "judgments_sha256": sha256_file(JUDGMENTS), "validation": validation,
        "gpu_after": _gpu_record(), "server_after": _get("/props"),
    }
    _write_json(JUDGMENT_SUMMARY, summary)
    if not validation["pass"]:
        raise LV009LiveError("judgment completeness failed")
    return summary


def _load_mapping() -> dict[str, Any]:
    if not JUDGMENT_SUMMARY.exists() or not _git_sealed(JUDGMENTS, JUDGMENT_SUMMARY):
        raise LV009LiveError("judgments must be complete and committed before mapping opens")
    summary = json.loads(JUDGMENT_SUMMARY.read_text(encoding="utf-8"))
    if not summary["validation"]["pass"] or sha256_file(JUDGMENTS) != summary["judgments_sha256"]:
        raise LV009LiveError("judgment seal mismatch")
    return json.loads(BLIND_MAPPING.read_text(encoding="utf-8"))["mapping"]


def _paired(rows: Sequence[Mapping[str, Any]], baseline: str, treatment: str) -> dict[str, Any]:
    gains = sum(bool(row[treatment]) and not bool(row[baseline]) for row in rows)
    losses = sum(bool(row[baseline]) and not bool(row[treatment]) for row in rows)
    n = len(rows)
    return {
        "n": n, "baseline_correct": sum(bool(row[baseline]) for row in rows),
        "treatment_correct": sum(bool(row[treatment]) for row in rows),
        "gains": gains, "losses": losses, "ties": n - gains - losses,
        "net": gains - losses, "percentage_point_difference": 100 * (gains - losses) / n if n else 0.0,
        "p_treatment": exact_sign_test(gains, losses), "p_control": exact_sign_test(losses, gains),
    }


def _holm_rejections(values: Mapping[str, float], alpha: float = 0.01) -> set[str]:
    ordered = sorted(values.items(), key=lambda item: (item[1], item[0]))
    rejected: set[str] = set()
    for index, (name, value) in enumerate(ordered):
        if value <= alpha / (len(ordered) - index):
            rejected.add(name)
        else:
            break
    return rejected


def _distribution(values: Sequence[int | float]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "n": len(ordered), "min": ordered[0], "median": median(ordered),
        "p95": ordered[(19 * len(ordered)) // 20], "max": ordered[-1],
    }


def analyze() -> dict[str, Any]:
    mapping = _load_mapping()
    answers = _read_jsonl(ANSWERS)
    judgments = _read_jsonl(JUDGMENTS)
    gold = _gold_records()
    prompts = {row["comparison_key"]: row for row in _read_prompts()}
    by_blind: dict[str, list[bool]] = defaultdict(list)
    for row in judgments:
        by_blind[str(row["blind_id"])].append(bool(row["verdict"]))
    if set(by_blind) != set(mapping) or any(len(values) != 3 for values in by_blind.values()):
        raise LV009LiveError("blind judgment join failed")
    verdicts = {
        (str(value["comparison_key"]), str(value["arm"])): majority(by_blind[identifier])
        for identifier, value in mapping.items()
    }
    item_map: dict[str, dict[str, Any]] = {}
    category5 = {arm: [] for arm in ARMS}
    containment_map: dict[tuple[str, str], bool] = {}
    response_meta = {arm: [] for arm in ARMS}
    for row in answers:
        key, arm = str(row["comparison_key"]), str(row["arm"])
        record = gold[(str(row["sample_id"]), int(row["source_index"]))]
        response_meta[arm].append(row["response"])
        if int(row["category"]) == 5:
            category5[arm].append(normalize(row["response"]["text"]) == "i don t know")
            continue
        item = item_map.setdefault(key, {
            "comparison_key": key, "sample_id": row["sample_id"],
            "source_index": row["source_index"], "category": int(row["category"]),
            "split": "development" if row["sample_id"] in DEVELOPMENT_IDS else "transfer",
        })
        item[arm] = verdicts[(key, arm)]
        containment_map[(key, arm)] = contains_gold(row["response"]["text"], record["gold"])
    items = [item_map[key] for key in sorted(item_map)]
    if len(items) != 1_540 or any(set(ARMS) - set(row) for row in items):
        raise LV009LiveError("analysis item join failed")
    comparisons: dict[str, Any] = {}
    primary_p: dict[str, float] = {}
    for name, baseline, treatment in COMPARISONS:
        combined = _paired(items, baseline, treatment)
        strata: dict[str, Any] = {
            "development": _paired([row for row in items if row["split"] == "development"], baseline, treatment),
            "transfer": _paired([row for row in items if row["split"] == "transfer"], baseline, treatment),
        }
        for category in PRIMARY_CATEGORIES:
            strata[f"category_{category}"] = _paired([row for row in items if row["category"] == category], baseline, treatment)
        for sample_id in sorted({str(row["sample_id"]) for row in items}):
            strata[sample_id] = _paired([row for row in items if row["sample_id"] == sample_id], baseline, treatment)
        containment_rows = [
            {baseline: containment_map[(row["comparison_key"], baseline)], treatment: containment_map[(row["comparison_key"], treatment)]}
            for row in items
        ]
        comparisons[name] = {
            "baseline": baseline, "treatment": treatment, "semantic": combined,
            "containment": _paired(containment_rows, baseline, treatment), "strata": strata,
        }
        if name in ("FULL_vs_PAIRWISE", "QUESTION_EACH_INCREMENT"):
            primary_p[name] = combined["p_treatment"]
    primary_holm = _holm_rejections(primary_p)
    for name in ("FULL_vs_PAIRWISE", "QUESTION_EACH_INCREMENT"):
        comparison = comparisons[name]
        semantic, strata = comparison["semantic"], comparison["strata"]
        regression_family = {key: value["p_control"] for key, value in strata.items() if key.startswith("category_") or key.startswith("conv-")}
        regression_rejections = _holm_rejections(regression_family)
        category_raw_guard = any(strata[f"category_{category}"]["net"] <= -10 for category in PRIMARY_CATEGORIES)
        guard = bool(regression_rejections) or category_raw_guard
        works = (
            semantic["net"] >= 31 and name in primary_holm and strata["transfer"]["net"] > 0 and not guard
        )
        carries = (
            not works and semantic["net"] >= 16 and semantic["p_treatment"] <= 0.05
            and strata["transfer"]["net"] > 0 and not guard
        )
        comparison["registered"] = {
            "works": works, "carries_signal": carries,
            "primary_holm_rejected": name in primary_holm,
            "regression_holm_rejections": sorted(regression_rejections),
            "category_raw_guard": category_raw_guard,
        }
    full = comparisons["FULL_vs_PAIRWISE"]["registered"]
    each = comparisons["QUESTION_EACH_INCREMENT"]["registered"]
    each_full = comparisons["QUESTION_EACH_vs_PAIRWISE"]
    each_full_safe = (
        each_full["semantic"]["net"] >= 31 and each_full["semantic"]["p_treatment"] <= 0.01
        and each_full["strata"]["transfer"]["net"] > 0
    )
    if each["works"] and each_full_safe:
        disposition = "QEACH_SELECTED"
    elif full["works"] and each["carries_signal"]:
        disposition = "QB_SELECTED_QEACH_SIGNAL"
    elif full["works"]:
        disposition = "QB_SELECTED"
    elif (full["carries_signal"] or each["carries_signal"]) and each_full["semantic"]["net"] >= 0:
        disposition = "RENDERER_CARRIES_SIGNAL"
    elif not full["works"] and not full["carries_signal"] and not each["works"] and not each["carries_signal"] and each_full["semantic"]["net"] >= 0:
        disposition = "PAIRWISE_RETAINED"
    else:
        disposition = "RENDERER_REGRESSION_OR_MIXED"
    result = {
        "schema": "lv009-result-v1", "disposition": disposition,
        "totals": {arm: sum(bool(row[arm]) for row in items) for arm in ARMS},
        "comparisons": comparisons, "primary_holm_rejections": sorted(primary_holm),
        "category5_exact_refusal": {arm: {"refusals": sum(values), "n": len(values)} for arm, values in category5.items()},
        "judge_disagreement_answers": sum(len(set(values)) > 1 for values in by_blind.values()),
        "response_tokens": {arm: _distribution([int(row["output_tokens"]) for row in values]) for arm, values in response_meta.items()},
        "prompt_tokens": {arm: _distribution([int(row["prompt_tokens"]) for row in values]) for arm, values in response_meta.items()},
        "wall_seconds": {arm: _distribution([float(row["wall_seconds"]) for row in values]) for arm, values in response_meta.items()},
        "length_stops": {arm: sum(row["stop_type"] == "limit" for row in values) for arm, values in response_meta.items()},
        "block_chars": {arm: _distribution([int(row["arms"][arm]["block_chars"]) for row in prompts.values()]) for arm in ARMS},
        "artifacts": {"answers_sha256": sha256_file(ANSWERS), "judgments_sha256": sha256_file(JUDGMENTS), "mapping_sha256": sha256_file(BLIND_MAPPING)},
        "calls": {"reader": 7_944, "judge": 18_480, "embedding": 0},
        "claim_boundary": "internal full-LoCoMO Qwen3.8 renderer comparison; not an official benchmark score, reader-model generality, deployment, or retrieval adoption claim",
    }
    _write_json(RESULT, result)
    PER_ITEM.parent.mkdir(parents=True, exist_ok=True)
    with PER_ITEM.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(items[0]))
        writer.writeheader()
        writer.writerows(items)
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("phase", choices=("preflight", "generate", "blind", "judge", "analyze"))
    args = parser.parse_args()
    actions = {
        "preflight": run_preflight, "generate": run_generation, "blind": prepare_blind,
        "judge": run_judging, "analyze": analyze,
    }
    print(json.dumps(actions[args.phase](), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
