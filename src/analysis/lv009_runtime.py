"""Runtime audit and live-call primitives for LV-009."""

from __future__ import annotations

import gzip
import hashlib
import json
import os
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from statistics import median
from typing import Any, Mapping, Sequence

from analysis.lv009_exploration import ARMS, PROMPTS, ROOT, reader_seed
from analysis.hh001_prompt import parse_judge_verdict, render_judge_prompt
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX


SERVER = "http://127.0.0.1:8000"
TOKEN_AUDIT = ROOT / "artifacts" / "part1" / "token_audit.json"
READER_PROBES = ROOT / "artifacts" / "part1" / "reader_probes.json"
LV008_PROMPTS = ROOT.parent / "live_validation_008" / "artifacts" / "preflight" / "prompts.jsonl.gz"
LV008_CAPPED_KEY = "c0be5dc5bb6a516c1deed9f06c5c9cac280f332ce134f31733e55c3dbd4bb891"
JUDGE_PROBES = ROOT / "artifacts" / "part1" / "judge_probes.json"
LV008_BLIND_SURFACE = ROOT.parent / "live_validation_008" / "artifacts" / "scoring" / "blind_surface.jsonl.gz"
LV008_JUDGMENTS = ROOT.parent / "live_validation_008" / "artifacts" / "scoring" / "blind_judgments.jsonl"


class LV009RuntimeError(RuntimeError):
    pass


def _post(path: str, payload: Mapping[str, Any], timeout: float = 900.0) -> dict[str, Any]:
    request = urllib.request.Request(
        SERVER + path,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def tokenize(prompt: str) -> int:
    payload = _post("/tokenize", {"content": prompt, "add_special": False}, timeout=120.0)
    tokens = payload.get("tokens")
    if not isinstance(tokens, list):
        raise LV009RuntimeError("llama.cpp tokenizer returned no token list")
    return len(tokens)


def _distribution(values: Sequence[int]) -> dict[str, Any]:
    ordered = sorted(values)
    return {
        "n": len(values),
        "min": ordered[0],
        "p05": ordered[len(ordered) // 20],
        "median": median(ordered),
        "p95": ordered[(19 * len(ordered)) // 20],
        "max": ordered[-1],
    }


def run_token_audit(output: Path = TOKEN_AUDIT, workers: int | None = None) -> dict[str, Any]:
    cells: list[tuple[str, str, str, int, int]] = []
    with gzip.open(PROMPTS, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            for arm in ARMS:
                prompt = row["arms"][arm]["prompt"]
                cells.append((row["comparison_key"], arm, prompt, len(prompt), len(row["arms"]["COMMUNITY_QB"]["groups"])))
    worker_count = workers or min(32, os.cpu_count() or 1)
    started = time.perf_counter()
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        counts = list(executor.map(lambda cell: tokenize(cell[2]), cells))
    rows = [
        {
            "comparison_key": cell[0],
            "arm": cell[1],
            "prompt_sha256": hashlib.sha256(cell[2].encode("utf-8")).hexdigest(),
            "prompt_chars": cell[3],
            "community_groups": cell[4],
            "prompt_tokens": count,
        }
        for cell, count in zip(cells, counts, strict=True)
    ]
    if len(rows) != 7_944 or len({(row["comparison_key"], row["arm"]) for row in rows}) != 7_944:
        raise LV009RuntimeError("token audit population drift")
    highest = sorted(rows, key=lambda row: (-row["prompt_tokens"], row["comparison_key"], row["arm"]))[:20]
    result = {
        "schema": "lv009-token-audit-v1",
        "server": SERVER,
        "workers": worker_count,
        "wall_seconds": round(time.perf_counter() - started, 3),
        "rows": len(rows),
        "context_limit": 65_536,
        "all_context_safe_at_reader_cap": all(row["prompt_tokens"] + 8_192 < 65_536 for row in rows),
        "prompt_tokens": _distribution([row["prompt_tokens"] for row in rows]),
        "prompt_chars": _distribution([row["prompt_chars"] for row in rows]),
        "highest_risk": highest,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def complete(prompt: str, *, seed: int, n_predict: int, temperature: float = 0.6) -> dict[str, Any]:
    started = time.perf_counter()
    payload = _post(
        "/completion",
        {
            "prompt": prompt,
            "n_predict": n_predict,
            "seed": seed,
            "temperature": temperature,
            "top_p": 0.95 if temperature == 0.6 else 0.9,
            "top_k": 20,
            "min_p": 0.0,
            "repeat_penalty": 1.0,
            "presence_penalty": 0.0,
            "reasoning_format": "none",
            "cache_prompt": True,
            "stream": False,
        },
    )
    content = str(payload.get("content", ""))
    if not content:
        raise LV009RuntimeError("llama.cpp returned empty content")
    return {
        "_text": content,
        "response_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "response_bytes": len(content.encode("utf-8")),
        "prompt_tokens": int(payload.get("tokens_evaluated", 0) or 0),
        "output_tokens": int(payload.get("tokens_predicted", 0) or 0),
        "stop_type": str(payload.get("stop_type", "")),
        "seed": seed,
        "wall_seconds": round(time.perf_counter() - started, 3),
    }


def run_reader_probes(output: Path = READER_PROBES) -> dict[str, Any]:
    audit = json.loads(TOKEN_AUDIT.read_text(encoding="utf-8"))
    highest = audit["highest_risk"][0]
    prompts: dict[str, dict[str, Any]] = {}
    max_groups: tuple[int, str, str] | None = None
    with gzip.open(PROMPTS, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["comparison_key"] == highest["comparison_key"]:
                prompts["maximum_tokens"] = {
                    "comparison_key": row["comparison_key"],
                    "arm": highest["arm"],
                    "prompt": row["arms"][highest["arm"]]["prompt"],
                }
            groups = len(row["arms"]["COMMUNITY_QB"]["groups"])
            candidate = (groups, row["comparison_key"], row["arms"]["COMMUNITY_QEACH"]["prompt"])
            if max_groups is None or candidate[:2] > max_groups[:2]:
                max_groups = candidate
    if max_groups is None or "maximum_tokens" not in prompts:
        raise LV009RuntimeError("risk prompt selection failed")
    prompts["maximum_communities"] = {
        "comparison_key": max_groups[1], "arm": "COMMUNITY_QEACH", "prompt": max_groups[2]
    }
    with gzip.open(LV008_PROMPTS, "rt", encoding="utf-8") as handle:
        prior = next(json.loads(line) for line in handle if json.loads(line)["comparison_key"] == LV008_CAPPED_KEY)
    prompts["lv008_capped_reader"] = {
        "comparison_key": LV008_CAPPED_KEY,
        "arm": "COMMUNITY_QB",
        "prompt": prior["arms"]["COMMUNITY_QB"]["prompt"],
        "seed": 5008,
    }
    rows = []
    for name, probe in prompts.items():
        seed = int(probe.get("seed", reader_seed(probe["comparison_key"])))
        result = complete(probe["prompt"], seed=seed, n_predict=8_192)
        result.pop("_text")
        rows.append({
            "name": name,
            "comparison_key": probe["comparison_key"],
            "arm": probe["arm"],
            "prompt_sha256": hashlib.sha256(probe["prompt"].encode("utf-8")).hexdigest(),
            **result,
        })
    result = {
        "schema": "lv009-reader-probes-v1",
        "calls": len(rows),
        "all_nonempty": all(row["response_bytes"] > 0 for row in rows),
        "all_context_safe": all(row["prompt_tokens"] + 8_192 < 65_536 for row in rows),
        "rows": rows,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


def run_judge_probes(output: Path = JUDGE_PROBES) -> dict[str, Any]:
    capped: list[tuple[str, int]] = []
    with LV008_JUDGMENTS.open("r", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row.get("done_reason") == "length":
                capped.append((str(row["blind_id"]), 9005 + int(row["judge_pass"])))
    if len(capped) != 7 or len(set(capped)) != 7:
        raise LV009RuntimeError("LV-008 capped judge population drift")
    needed = {blind_id for blind_id, _ in capped}
    surfaces: dict[str, dict[str, Any]] = {}
    with gzip.open(LV008_BLIND_SURFACE, "rt", encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            if row["blind_id"] in needed:
                surfaces[row["blind_id"]] = row
    rows = []
    for blind_id, seed in capped:
        surface = surfaces[blind_id]
        prompt = render_judge_prompt(surface["question"], surface["gold"], surface["answer"]) + CLOSED_THINK_SUFFIX + "VERDICT:"
        response = complete(prompt, seed=seed, n_predict=4_096, temperature=0.2)
        generated = response.pop("_text")
        # Parser success is the only imported property; prior correctness is ignored.
        try:
            parse_judge_verdict(generated)
        except Exception:
            parseable = False
        else:
            parseable = True
        rows.append({"blind_id": blind_id, "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(), **response, "parseable_surface": parseable})
    result = {
        "schema": "lv009-judge-probes-v1",
        "calls": len(rows),
        "all_nonempty": all(row["response_bytes"] > 0 for row in rows),
        "rows": rows,
    }
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    run_token_audit()
