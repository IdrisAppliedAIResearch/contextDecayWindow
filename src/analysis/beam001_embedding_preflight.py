"""BEAM-001 exact-input gate for the amended OpenAI embedder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence

import tiktoken

from analysis.beam001_adapter import adapt_conversation, load_mechanism_surface

REPO_ROOT = Path(__file__).resolve().parents[2]
MECHANISM_SURFACE = (
    REPO_ROOT
    / "experiments/comparisons/beam_001/artifacts/corpus/mechanism_surface.jsonl.gz"
)
ARTIFACT = (
    REPO_ROOT
    / "experiments/comparisons/beam_001/artifacts/preflight/openai_input_limit.json"
)
MODEL = "text-embedding-3-small"
DIMENSIONS = 1_024
TOKENIZER = "cl100k_base"
MAX_INPUT_TOKENS = 8_192
OFFICIAL_REFERENCE = (
    "https://developers.openai.com/api/reference/resources/embeddings/methods/create"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def episode_text(episode: dict[str, Any]) -> str:
    return (
        f"User: {episode['user_message']}\n"
        f"Assistant: {episode['assistant_message']}"
    )


def _distribution(values: Sequence[int]) -> dict[str, int | None]:
    if not values:
        return {
            "n": 0,
            "min": None,
            "p05": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "max": None,
        }
    ordered = sorted(values)

    def percentile(fraction: float) -> int:
        return ordered[round((len(ordered) - 1) * fraction)]

    return {
        "n": len(ordered),
        "min": ordered[0],
        "p05": percentile(0.05),
        "p25": percentile(0.25),
        "median": percentile(0.50),
        "p75": percentile(0.75),
        "p95": percentile(0.95),
        "max": ordered[-1],
    }


def evaluate(rows: Iterable[dict[str, Any]]) -> dict[str, Any]:
    encoding = tiktoken.get_encoding(TOKENIZER)
    episode_lengths: list[int] = []
    question_lengths: list[int] = []
    oversized: list[dict[str, Any]] = []
    conversation_count = 0
    for row in rows:
        conversation_count += 1
        for episode in adapt_conversation(row):
            tokens = len(encoding.encode(episode_text(episode)))
            episode_lengths.append(tokens)
            if tokens > MAX_INPUT_TOKENS:
                oversized.append(
                    {
                        "conversation_key": episode["conversation_key"],
                        "episode_key": episode["episode_key"],
                        "turn_number": episode["turn_number"],
                        "tokens": tokens,
                        "excess_tokens": tokens - MAX_INPUT_TOKENS,
                    }
                )
        for question in row["questions"]:
            question_lengths.append(len(encoding.encode(question["question"])))

    gate = not oversized and all(value <= MAX_INPUT_TOKENS for value in question_lengths)
    return {
        "behavioral_identity": (
            "Embed each exact public-store episode text and each exact question as "
            "one OpenAI embeddings input, with no truncation or segmentation."
        ),
        "model": MODEL,
        "dimensions": DIMENSIONS,
        "tokenizer": TOKENIZER,
        "max_input_tokens": MAX_INPUT_TOKENS,
        "official_reference": OFFICIAL_REFERENCE,
        "conversations": conversation_count,
        "episode_tokens": {
            **_distribution(episode_lengths),
            "total": sum(episode_lengths),
            "over_limit": len(oversized),
        },
        "question_tokens": {
            **_distribution(question_lengths),
            "total": sum(question_lengths),
            "over_limit": sum(value > MAX_INPUT_TOKENS for value in question_lengths),
        },
        "oversized_episodes": oversized,
        "gate": "PASS" if gate else "FAIL",
        "disposition": (
            "READY_FOR_TWO_REQUEST_SMOKE"
            if gate
            else "EMBEDDING_INPUT_NOT_IDENTIFIED"
        ),
        "api_requests_made": 0,
        "outcomes_opened": False,
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, delete=False, newline="\n"
    ) as handle:
        temporary = Path(handle.name)
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    temporary.replace(path)


def run(
    mechanism_path: Path = MECHANISM_SURFACE,
    artifact_path: Path = ARTIFACT,
) -> dict[str, Any]:
    result = evaluate(load_mechanism_surface(mechanism_path))
    result["mechanism_surface_sha256"] = sha256_file(mechanism_path)
    result["script_sha256"] = sha256_file(Path(__file__))
    _write_json(artifact_path, result)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mechanism", type=Path, default=MECHANISM_SURFACE)
    parser.add_argument("--artifact", type=Path, default=ARTIFACT)
    args = parser.parse_args()
    result = run(args.mechanism, args.artifact)
    summary = {
        "gate": result["gate"],
        "disposition": result["disposition"],
        "episodes": result["episode_tokens"]["n"],
        "oversized_episodes": result["episode_tokens"]["over_limit"],
        "max_episode_tokens": result["episode_tokens"]["max"],
        "questions": result["question_tokens"]["n"],
        "api_requests_made": result["api_requests_made"],
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if result["gate"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
