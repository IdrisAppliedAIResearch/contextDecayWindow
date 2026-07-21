"""Replay Study 004 truncation prompts to measure their natural completion length."""

import argparse
import hashlib
import json
import os
import time
from pathlib import Path
from urllib.request import Request, urlopen

from src.inference.provider import RULE_DETECTION_INSTRUCTION


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PROMPT_DIR = (
    REPOSITORY_ROOT
    / "experiments"
    / "study_004"
    / "runs"
    / "study_004_full_001_failed_truncation"
    / "condition_c"
    / "constructed_prompts"
)
DEFAULT_OUTPUT_DIR = (
    REPOSITORY_ROOT
    / "experiments"
    / "study_004"
    / "verification"
    / "response_budget_a005"
)
TURNS = (8, 9, 10)
REPLAY_CEILING = 4096
PROPOSED_BUDGET = 2048
TARGET_MAXIMUM = 1800
RECONSIDER_THRESHOLD = 1900


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def _request_json(url: str, payload: dict | None = None) -> dict:
    if payload is None:
        request = Request(url, method="GET")
    else:
        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
    with urlopen(request, timeout=900) as response:
        return json.loads(response.read().decode("utf-8"))


def _build_exact_server_prompt(constructed_prompt: str) -> str:
    augmented_prompt = (
        f"{constructed_prompt}\n\n{RULE_DETECTION_INSTRUCTION}"
    )
    return f"{augmented_prompt}\n<think>\n</think>\n"


def _summarize(turn: int, response: dict, elapsed_seconds: float) -> dict:
    tokens = int(response.get("tokens_predicted", 0))
    content = response.get("content", "")
    stopped_limit = bool(response.get("stopped_limit", False))
    natural_completion = not stopped_limit and tokens < REPLAY_CEILING
    return {
        "turn": turn,
        "tokens_predicted": tokens,
        "characters": len(content),
        "elapsed_seconds": elapsed_seconds,
        "tokens_per_second": tokens / elapsed_seconds if elapsed_seconds else 0.0,
        "stop_type": response.get("stop_type"),
        "stopped_eos": response.get("stopped_eos"),
        "stopped_limit": stopped_limit,
        "natural_completion": natural_completion,
        "fits_2048": natural_completion and tokens < PROPOSED_BUDGET,
        "margin_to_2048": PROPOSED_BUDGET - tokens,
        "at_or_below_target_1800": natural_completion and tokens <= TARGET_MAXIMUM,
        "reconsider_required": (not natural_completion) or tokens > RECONSIDER_THRESHOLD,
        "contains_rule_detection_tag": "<rule_detection>" in content,
        "final_240_characters": content[-240:],
    }


def _write_report(output_dir: Path, summaries: list[dict]) -> None:
    all_fit = all(item["fits_2048"] for item in summaries)
    all_target = all(item["at_or_below_target_1800"] for item in summaries)
    reconsider = any(item["reconsider_required"] for item in summaries)
    lines = [
        "# Study 004 A005 Response-Budget Sufficiency Verification",
        "",
        f"- Replay ceiling: {REPLAY_CEILING:,} tokens",
        f"- Proposed production budget: {PROPOSED_BUDGET:,} tokens",
        f"- Target natural completion: <= {TARGET_MAXIMUM:,} tokens",
        f"- Reconsider threshold: > {RECONSIDER_THRESHOLD:,} tokens",
        "- Sampling settings: omitted, matching the production server-default payload",
        f"- All naturally completed below 2,048: {all_fit}",
        f"- All met the <=1,800 target: {all_target}",
        f"- Reconsideration required: {reconsider}",
        "",
        "| Turn | Tokens | Stop type | Natural? | Margin to 2,048 | <=1,800? | Reconsider? |",
        "|---:|---:|---|---|---:|---|---|",
    ]
    for item in summaries:
        lines.append(
            "| {turn} | {tokens_predicted:,} | {stop_type} | "
            "{natural_completion} | {margin_to_2048:,} | "
            "{at_or_below_target_1800} | {reconsider_required} |".format(
                **item
            )
        )
    lines.extend(["", "## Exact response endings", ""])
    for item in summaries:
        ending = item["final_240_characters"].replace("\n", " ")
        lines.extend([
            f"### Turn {item['turn']}",
            "",
            f"`{ending}`",
            "",
        ])
    (output_dir / "verification_report.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--prompt-dir", type=Path, default=DEFAULT_PROMPT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()

    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite existing verification artifacts: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)

    server_url = os.environ.get(
        "CDW_INFERENCE_SERVER_URL", "http://127.0.0.1:8000"
    ).rstrip("/")
    server_props = _request_json(f"{server_url}/props")
    (output_dir / "server_props.json").write_text(
        json.dumps(server_props, indent=2), encoding="utf-8"
    )

    summaries = []
    for turn in TURNS:
        prompt_path = args.prompt_dir / f"turn_{turn:03d}.txt"
        constructed_prompt = prompt_path.read_text(encoding="utf-8")
        exact_prompt = _build_exact_server_prompt(constructed_prompt)
        payload = {
            "prompt": exact_prompt,
            "n_predict": REPLAY_CEILING,
            "reasoning_format": "none",
            "stream": False,
        }
        started = time.perf_counter()
        response = _request_json(f"{server_url}/completion", payload)
        elapsed = time.perf_counter() - started
        summary = _summarize(turn, response, elapsed)
        summary["constructed_prompt_sha256"] = _sha256(constructed_prompt)
        summary["exact_server_prompt_sha256"] = _sha256(exact_prompt)
        summaries.append(summary)
        (output_dir / f"turn_{turn:03d}_response.json").write_text(
            json.dumps(
                {
                    "turn": turn,
                    "request_parameters": {
                        "n_predict": REPLAY_CEILING,
                        "reasoning_format": "none",
                        "stream": False,
                        "sampling_parameters": "server defaults (omitted)",
                    },
                    "constructed_prompt_sha256": summary[
                        "constructed_prompt_sha256"
                    ],
                    "exact_server_prompt_sha256": summary[
                        "exact_server_prompt_sha256"
                    ],
                    "elapsed_seconds": elapsed,
                    "response": response,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    (output_dir / "summary.json").write_text(
        json.dumps(summaries, indent=2), encoding="utf-8"
    )
    _write_report(output_dir, summaries)

    if any(item["reconsider_required"] for item in summaries):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
