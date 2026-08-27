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
SERVER = "http://127.0.0.1:11434"
MODEL = "lv008-qwen38-q4:latest"


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


def _read_prompts() -> list[dict[str, Any]]:
    with gzip.open(LV007_PROMPTS, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _read_answers() -> list[dict[str, Any]]:
    with LV007_ANSWERS.open("r", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _generate(prompt: str, seed: int, cap: int) -> dict[str, Any]:
    started = time.perf_counter()
    payload = _request(
        "/api/generate",
        {
            "model": MODEL,
            "prompt": prompt,
            "raw": True,
            "think": False,
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "seed": seed,
                "num_ctx": 65_536,
                "num_predict": cap,
                "temperature": 0.6,
                "top_p": 0.95,
                "top_k": 20,
                "min_p": 0.0,
                "repeat_penalty": 1.0,
            },
        },
    )
    text = str(payload.get("response", "")).strip()
    if not text:
        raise LV008ExplorationError("Ollama returned an empty completion")
    done_reason = str(payload.get("done_reason", ""))
    return {
        "response_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
        "stop_type": done_reason,
        "seed": seed,
        "prompt_tokens": int(payload.get("prompt_eval_count", 0) or 0),
        "output_tokens": int(payload.get("eval_count", 0) or 0),
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

    version = _request("/api/version")
    show = _request("/api/show", {"model": MODEL})
    process_before = _request("/api/ps")
    repeats = {str(cap): [_generate(prompt, FAILED_SEED, cap) for _ in range(2)] for cap in CAPS}
    process_after = _request("/api/ps")
    loaded = [row for row in process_after.get("models", []) if row.get("name") == MODEL]
    gpu_only = bool(loaded) and all(int(row.get("size_vram", 0)) == int(row.get("size", -1)) for row in loaded)
    byte_identical = {
        cap: repeats[str(cap)][0]["response_sha256"] == repeats[str(cap)][1]["response_sha256"]
        for cap in CAPS
    }
    natural_stop = {
        cap: all(row["stop_type"] != "length" and row["output_tokens"] < cap for row in repeats[str(cap)])
        for cap in CAPS
    }
    cross_cap_identical = repeats["2048"][0]["response_sha256"] == repeats["4096"][0]["response_sha256"]
    status = "RUNTIME_VIABLE" if gpu_only and all(byte_identical.values()) and natural_stop[4096] else "NO_VIABLE_RUNTIME"
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
            "ollama_version": version.get("version"),
            "model_alias": MODEL,
            "model_digest": loaded[0].get("digest") if loaded else None,
            "model_details": show.get("details"),
            "context": loaded[0].get("context_length") if loaded else None,
            "size": loaded[0].get("size") if loaded else None,
            "size_vram": loaded[0].get("size_vram") if loaded else None,
            "speculative_decoding": "not enabled or exposed by the frozen Ollama API call",
        },
        "repeats": repeats,
        "checks": {
            "byte_identical_within_cap": byte_identical,
            "natural_stop": natural_stop,
            "cross_cap_identical": cross_cap_identical,
            "gpu_only": gpu_only,
        },
        "process": {"before": process_before, "after": process_after},
        "absorbing_states": {
            "output_cap": "a completion that reaches its common cap stops by length and invalidates the run before judging",
            "reader_change": "Qwen3.8 Q4 outputs cannot complete or repair the stopped Qwen3.6 Q6 LV-007 schedule; all arms must be regenerated",
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
