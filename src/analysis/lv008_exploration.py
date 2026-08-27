"""Label-blind Part 1 exploration for an LV-007 reader continuation."""

from __future__ import annotations

import gzip
import hashlib
import json
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Mapping

from analysis.locomo_nf_development import sha256_file
from analysis.tc001_exploration import REPO_ROOT


ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_008"
OUTPUT = ROOT / "artifacts" / "part1_exploration.json"
LV007_ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_007"
LV007_PROMPTS = LV007_ROOT / "artifacts" / "preflight" / "prompts.jsonl.gz"
LV007_ANSWERS = LV007_ROOT / "artifacts" / "run" / "answers.jsonl"
LV007_SUMMARY = LV007_ROOT / "artifacts" / "run" / "generation_summary.json"
LV007_STOP = LV007_ROOT / "LV_007_STOP.md"

LV007_PROMPTS_SHA256 = "dc40d134e0e281fd0a064371620ce2a9a99f8f4a39855d3f32072ca9a844e9d9"
LV007_ANSWERS_SHA256 = "da1f8f62ba571ab17660091610077b1171b72a8a529d984fbad5962f04141f22"
LV007_SUMMARY_SHA256 = "97a428cab42d9721c9c6af2d7b648113c0f4d76a1a2cf389e9be6677db05928f"
LV007_STOP_SHA256 = "d1497d7aadc47f6f4afb67361d5f3face895dc6d07142dffefbfbb9412b74957"

FAILED_KEY = "7fd147b3cb2deb3677b72ea650c8453b67ff7f6a2e84e36d1d887c7a14608c85"
FAILED_ARM = "COMMUNITY"
FAILED_REPLICATE = 0
FAILED_SEED = 5005
CAPS = (2048, 4096)
SERVER = "http://127.0.0.1:8000"


class LV008ExplorationError(RuntimeError):
    pass


def _request(path: str, body: Mapping[str, Any] | None = None) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{SERVER}{path}",
        data=None if body is None else json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="GET" if body is None else "POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=900.0) as response:
            return json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError) as error:
        raise LV008ExplorationError(f"llama-server request failed at {path}: {error}") from error


def _metrics() -> dict[str, float]:
    try:
        with urllib.request.urlopen(f"{SERVER}/metrics", timeout=30.0) as response:
            lines = response.read().decode("utf-8").splitlines()
    except (urllib.error.URLError, TimeoutError) as error:
        raise LV008ExplorationError(f"llama-server metrics failed: {error}") from error
    wanted = {
        "llamacpp:spec_decode_num_draft_tokens_total",
        "llamacpp:spec_decode_num_accepted_tokens_total",
        "llamacpp:spec_decode_num_drafts_total",
    }
    values: dict[str, float] = {}
    for line in lines:
        if not line or line.startswith("#") or "{" in line:
            continue
        name, _, raw = line.partition(" ")
        if name in wanted:
            values[name] = float(raw)
    return values


def _read_prompts() -> list[dict[str, Any]]:
    with gzip.open(LV007_PROMPTS, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_answers() -> list[dict[str, Any]]:
    with LV007_ANSWERS.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _generate(prompt: str, seed: int, cap: int) -> dict[str, Any]:
    started = time.perf_counter()
    payload = _request(
        "/completion",
        {
            "prompt": prompt,
            "seed": seed,
            "n_predict": cap,
            "temperature": 0.6,
            "top_p": 0.95,
            "top_k": 20,
            "min_p": 0.0,
            "repeat_penalty": 1.0,
            "stream": False,
        },
    )
    text = str(payload.get("content", "")).strip()
    if not text:
        raise LV008ExplorationError("llama-server returned an empty completion")
    settings = payload.get("generation_settings", {})
    return {
        "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "stop_type": str(payload.get("stop_type", "")),
        "seed": seed,
        "prompt_tokens": int(payload.get("tokens_evaluated", 0) or 0),
        "output_tokens": int(payload.get("tokens_predicted", 0) or 0),
        "speculative_types": str(settings.get("speculative.types", "")),
        "wall_seconds": round(time.perf_counter() - started, 3),
    }


def run(output: Path = OUTPUT) -> dict[str, Any]:
    anchors = {
        LV007_PROMPTS: LV007_PROMPTS_SHA256,
        LV007_ANSWERS: LV007_ANSWERS_SHA256,
        LV007_SUMMARY: LV007_SUMMARY_SHA256,
        LV007_STOP: LV007_STOP_SHA256,
    }
    if any(sha256_file(path) != expected for path, expected in anchors.items()):
        raise LV008ExplorationError("LV-007 stop anchor drift")
    if (LV007_ROOT / "artifacts" / "scoring" / "blind_surface.jsonl.gz").exists():
        raise LV008ExplorationError("LV-007 blind surface unexpectedly exists")

    answers = _read_answers()
    summary = json.loads(LV007_SUMMARY.read_text(encoding="utf-8"))
    truncated = [row for row in answers if row["response"]["done_reason"] == "length"]
    if (
        len(answers) != 255
        or len(truncated) != 1
        or summary["validation"]["truncated"] != 1
        or summary["validation"]["missing"] != 0
        or summary["validation"]["duplicates"] != 0
    ):
        raise LV008ExplorationError("LV-007 stopped schedule drift")
    failed = truncated[0]
    identity = (
        failed["comparison_key"],
        failed["arm"],
        int(failed["replicate"]),
        int(failed["response"]["seed"]),
    )
    if identity != (FAILED_KEY, FAILED_ARM, FAILED_REPLICATE, FAILED_SEED):
        raise LV008ExplorationError("LV-007 failed answer identity drift")

    prompt_row = next(row for row in _read_prompts() if row["comparison_key"] == FAILED_KEY)
    prompt = prompt_row["arms"][FAILED_ARM]["prompt"]
    if hashlib.sha256(prompt.encode("utf-8")).hexdigest() != failed["prompt_sha256"]:
        raise LV008ExplorationError("failed prompt digest drift")

    props = _request("/props")
    params = props["default_generation_settings"]["params"]
    if params.get("speculative.types") != "none":
        raise LV008ExplorationError("server default enables speculative decoding")
    metrics_before = _metrics()
    repeats = {str(cap): [_generate(prompt, FAILED_SEED, cap) for _ in range(2)] for cap in CAPS}
    metrics_after = _metrics()
    no_speculative_work = all(metrics_after.get(key, 0.0) == metrics_before.get(key, 0.0) for key in metrics_before)
    byte_identical = {
        cap: repeats[str(cap)][0]["response_sha256"] == repeats[str(cap)][1]["response_sha256"]
        for cap in CAPS
    }
    natural_stop = {
        cap: all(row["stop_type"] != "limit" and row["output_tokens"] < cap for row in repeats[str(cap)])
        for cap in CAPS
    }
    cross_cap_identical = repeats["2048"][0]["response_sha256"] == repeats["4096"][0]["response_sha256"]
    status = "RUNTIME_VIABLE" if no_speculative_work and all(byte_identical.values()) and natural_stop[4096] else "NO_VIABLE_RUNTIME"
    result = {
        "schema": "lv008-part1-exploration-v2",
        "status": status,
        "behavioral_identity": {
            "lv007_stop": "all 255 scheduled reader answers exist, but one COMMUNITY answer ended by length at 2048 tokens, so LV-007 cannot be judged",
            "candidate_continuation": "regenerate all three frozen prompt arms with a different Qwen3.8 reader under one common cap; this is a reader replication, not an LV-007 repair",
        },
        "inputs": {
            "answers": len(answers),
            "truncated": len(truncated),
            "failed_identity": {
                "comparison_key": FAILED_KEY,
                "arm": FAILED_ARM,
                "replicate": FAILED_REPLICATE,
                "seed": FAILED_SEED,
            },
            "prompt_sha256": failed["prompt_sha256"],
            "anchors": {path.name: sha256_file(path) for path in anchors},
        },
        "runtime": {
            "server": SERVER,
            "build_info": props.get("build_info"),
            "model_alias": props.get("model_alias"),
            "model_ftype": props.get("model_ftype"),
            "context": props["default_generation_settings"].get("n_ctx"),
            "default_speculative_types": params.get("speculative.types"),
        },
        "repeats": repeats,
        "checks": {
            "byte_identical_within_cap": byte_identical,
            "natural_stop": natural_stop,
            "cross_cap_identical": cross_cap_identical,
            "no_speculative_work": no_speculative_work,
        },
        "metrics": {"before": metrics_before, "after": metrics_after},
        "absorbing_states": {
            "output_cap": "a completion that reaches its common cap stops as limit and invalidates the run before judging",
            "reader_change": "Qwen3.8 outputs cannot complete or repair the stopped Qwen3.5 LV-007 schedule; all arms must be regenerated",
        },
        "surrogate_audit": {
            "can_pass_while_false": True,
            "residual": "one prompt stopping naturally and replaying byte-identically does not prove all 255 calls will stop naturally or that compact rendering improves answers",
        },
        "labels_opened": False,
        "answer_text_opened_by_operator": False,
        "calls": {"reader": 4, "judge": 0, "embedding": 0},
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    print(json.dumps(run(), indent=2, sort_keys=True))
