"""Run one calibrated, blind EC-001 rater-family pass."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

from src.analysis.ec001_longmemeval import (  # noqa: E402
    AMENDMENT_004_SHA,
    assert_repository_ready,
    sha256_file,
)
from src.analysis.ec001_tier2 import (  # noqa: E402
    build_label_prompt,
    build_rationale_prompt,
    parse_binary_label,
)


def _jsonl(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _post_json(url: str, payload: dict, headers: dict) -> dict:
    body = json.dumps(payload).encode("utf-8")
    for attempt in range(6):
        request = Request(
            url,
            data=body,
            headers={"Content-Type": "application/json", **headers},
            method="POST",
        )
        try:
            with urlopen(request, timeout=900) as response:
                result = json.loads(response.read().decode("utf-8"))
            if not isinstance(result, dict):
                raise RuntimeError("Rater endpoint returned a non-object")
            return result
        except (HTTPError, URLError) as error:
            if attempt == 5:
                raise
            delay = 2 ** attempt
            print(f"Rater request retry in {delay}s: {error}")
            time.sleep(delay)
    raise AssertionError("unreachable")


def _get_json(url: str) -> dict:
    with urlopen(Request(url, method="GET"), timeout=60) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not isinstance(result, dict):
        raise RuntimeError("Rater endpoint returned a non-object")
    return result


def _validate_local_server(config: dict, server_url: str | None) -> dict | None:
    if config["provider"] != "llama_cpp":
        return None
    if not server_url:
        raise RuntimeError("Local rater requires --server-url")
    props = _get_json(server_url.rstrip("/") + "/props")
    if props.get("total_slots") != 1:
        raise RuntimeError("Local rater server must expose one slot")
    if props.get("model_alias") != config["model_alias"]:
        raise RuntimeError("Local rater server model alias mismatch")
    if props.get("build_info") != config["server_build_info"]:
        raise RuntimeError("Local rater server build mismatch")
    params = props.get("default_generation_settings", {}).get("params", {})
    if params.get("speculative.types") != "none":
        raise RuntimeError("Local rater speculative decoding is enabled")
    return props


class RaterClient:
    def __init__(self, config: dict, server_url: str | None) -> None:
        self.config = config
        self.server_url = server_url
        self.call_count = 0

    def complete(self, prompt: str, *, max_tokens: int) -> str:
        self.call_count += 1
        provider = self.config["provider"]
        if provider == "openai":
            env_name = str(self.config["api_key_env"])
            api_key = os.environ.get(env_name)
            if not api_key:
                raise RuntimeError(f"Missing rater API key env: {env_name}")
            result = _post_json(
                str(self.config["base_url"]).rstrip("/")
                + "/chat/completions",
                {
                    "model": self.config["model_id"],
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "seed": int(self.config["seed"]),
                    "max_completion_tokens": max_tokens,
                },
                {"Authorization": f"Bearer {api_key}"},
            )
            return str(result["choices"][0]["message"]["content"]).strip()
        if provider == "llama_cpp":
            if not self.server_url:
                raise RuntimeError("Local rater requires --server-url")
            result = _post_json(
                self.server_url.rstrip("/") + "/completion",
                {
                    "prompt": f"{prompt}\n<think>\n</think>\n",
                    "n_predict": max_tokens,
                    "reasoning_format": "none",
                    "temperature": 0,
                    "seed": int(self.config["seed"]),
                    "stream": False,
                },
                {},
            )
            return str(result.get("content", "")).strip()
        raise RuntimeError(f"Unsupported rater provider: {provider}")


def _validate_runtime(runtime: dict, family_id: str) -> dict:
    if runtime.get("amendment_004_sha") != AMENDMENT_004_SHA:
        raise RuntimeError("Runtime record predates Amendment 004")
    raters = runtime.get("raters")
    if not isinstance(raters, list) or len(raters) != 3:
        raise RuntimeError("Runtime must lock exactly three raters")
    families = [str(row["model_family"]).casefold() for row in raters]
    if len(set(families)) != 3 or "qwen" in families:
        raise RuntimeError("Raters must be three non-Qwen model families")
    matches = [row for row in raters if row["family_id"] == family_id]
    if len(matches) != 1:
        raise RuntimeError(f"Unknown or duplicate family id: {family_id}")
    config = matches[0]
    if config["provider"] == "llama_cpp":
        model_path = Path(str(config["model_path"]))
        if sha256_file(model_path) != config["model_sha256"]:
            raise RuntimeError(f"{family_id} model hash mismatch")
    return config


def _calibrate(client: RaterClient, cases: list[dict]) -> list[dict]:
    results: list[dict] = []
    for case in cases:
        prompt = build_label_prompt(
            str(case["question_type"]),
            str(case["question"]),
            str(case["reference_answer"]),
            str(case["response"]),
            abstention=bool(case["abstention"]),
        )
        surface = client.complete(prompt, max_tokens=10)
        label = parse_binary_label(surface)
        expected = bool(case["expected_label"])
        results.append(
            {
                "calibration_id": case["calibration_id"],
                "expected_label": expected,
                "observed_label": label,
                "response": surface,
                "pass": label == expected,
            }
        )
    if not all(row["pass"] for row in results):
        raise RuntimeError(f"Rater calibration failed: {results}")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--packets", type=Path, required=True)
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--runtime-record", type=Path, required=True)
    parser.add_argument("--family-id", required=True)
    parser.add_argument("--server-url")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    repository = assert_repository_ready(require_clean=True)
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite rater output: {args.output}")
    runtime = json.loads(args.runtime_record.read_text(encoding="utf-8"))
    config = _validate_runtime(runtime, args.family_id)
    server_props = _validate_local_server(config, args.server_url)
    client = RaterClient(config, args.server_url)
    calibration = _calibrate(
        client,
        json.loads(args.calibration.read_text(encoding="utf-8")),
    )

    packets = _jsonl(args.packets)
    packets.sort(
        key=lambda row: (
            hashlib.sha256(
                f"{args.family_id}\0{row['anon_id']}".encode("utf-8")
            ).hexdigest(),
            row["anon_id"],
        )
    )
    started = time.time()
    outputs: list[dict] = []
    for index, packet in enumerate(packets, 1):
        if packet["mechanical_zero"]:
            label = False
            label_surface = "MECHANICAL_ZERO"
            rationale = (
                "The response is mechanically zero because it is "
                f"{packet['mechanical_zero_reason']}."
            )
            rater_called = False
        else:
            label_surface = client.complete(
                str(packet["label_prompt"]),
                max_tokens=10,
            )
            label = parse_binary_label(label_surface)
            rationale = client.complete(
                build_rationale_prompt(str(packet["label_prompt"]), label),
                max_tokens=160,
            ).strip()
            if not rationale:
                raise RuntimeError(
                    f"Missing rationale for {packet['anon_id']}"
                )
            rater_called = True
        outputs.append(
            {
                "anon_id": packet["anon_id"],
                "family_id": args.family_id,
                "model_family": config["model_family"],
                "model_id": config["model_id"],
                "label": label,
                "label_response": label_surface,
                "rationale": rationale,
                "rater_called": rater_called,
                "mechanical_zero": packet["mechanical_zero"],
            }
        )
        if index % 10 == 0 or index == len(packets):
            print(f"{index:3d}/{len(packets)} {args.family_id} scores")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in outputs:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    header_path = args.output.with_suffix(args.output.suffix + ".header.json")
    header_path.write_text(
        json.dumps(
            {
                "record": "EC-001 blind rater pass",
                "head": repository["head"],
                "family_id": args.family_id,
                "model_family": config["model_family"],
                "model_id": config["model_id"],
                "provider": config["provider"],
                "server_props": server_props,
                "calibration": calibration,
                "calibration_status": "PASS",
                "packets_sha256": sha256_file(args.packets),
                "runtime_record_sha256": sha256_file(args.runtime_record),
                "question_count": len(outputs),
                "call_count": client.call_count,
                "started_utc": datetime.fromtimestamp(
                    started, timezone.utc
                ).isoformat(),
                "finished_utc": datetime.now(timezone.utc).isoformat(),
                "output_sha256": sha256_file(args.output),
            },
            indent=2,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    print(f"Rater pass complete: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
