from __future__ import annotations

import math
import os
import platform
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any, Protocol, Sequence

import numpy as np

from src.analysis.sal001_shared import (
    MODEL_BYTES,
    MODEL_SHA256,
    SEED,
    artifact_identity,
    canonical_digest,
    read_json,
    sha256_file,
    write_json,
)


N_CTX = 6144
N_BATCH = 256
N_UBATCH = 256
EXPECTED_VOCAB = 248_320


class SAL001ScoreError(RuntimeError):
    pass


class TokenModel(Protocol):
    scores: np.ndarray

    def tokenize(
        self, text: bytes, add_bos: bool = False, special: bool = True
    ) -> list[int]: ...

    def eval(self, tokens: Sequence[int]) -> None: ...

    def reset(self) -> None: ...


class SessionFormatter(Protocol):
    def __call__(self, *, messages: list[dict[str, str]]) -> Any: ...


def changed_interval(full: Sequence[int], blank: Sequence[int]) -> tuple[int, int]:
    prefix = 0
    limit = min(len(full), len(blank))
    while prefix < limit and full[prefix] == blank[prefix]:
        prefix += 1
    suffix = 0
    while (
        suffix < len(full) - prefix
        and suffix < len(blank) - prefix
        and full[len(full) - 1 - suffix] == blank[len(blank) - 1 - suffix]
    ):
        suffix += 1
    end = len(full) - suffix
    if prefix >= end:
        raise SAL001ScoreError("User content produced an empty token interval")
    if list(full[:prefix]) + list(full[prefix:end]) + list(full[end:]) != list(full):
        raise SAL001ScoreError("Token interval reconstruction failed")
    return prefix, end


def _render_tokens(
    model: TokenModel,
    formatter: SessionFormatter,
    messages: list[dict[str, str]],
) -> list[int]:
    rendered = formatter(messages=messages).prompt
    return model.tokenize(
        rendered.encode("utf-8"), add_bos=False, special=True
    )


def user_intervals(
    model: TokenModel,
    formatter: SessionFormatter,
    messages: list[dict[str, str]],
) -> tuple[list[int], list[tuple[int, int]]]:
    full = _render_tokens(model, formatter, messages)
    intervals: list[tuple[int, int]] = []
    for message_index in range(0, len(messages), 2):
        if messages[message_index]["role"] != "user":
            raise SAL001ScoreError("Expected strict user/assistant message pairs")
        blank_messages = [dict(message) for message in messages]
        blank_messages[message_index]["content"] = ""
        blank = _render_tokens(model, formatter, blank_messages)
        start, end = changed_interval(full, blank)
        if start == 0:
            raise SAL001ScoreError("Cannot score a token without a preceding row")
        intervals.append((start, end))
    for left, right in zip(intervals, intervals[1:]):
        if left[1] > right[0]:
            raise SAL001ScoreError("User token intervals overlap")
    return full, intervals


def token_negative_log_probability(
    logits: np.ndarray, token_id: int
) -> float:
    row = np.asarray(logits, dtype=np.float64)
    maximum = float(np.max(row))
    log_normalizer = maximum + math.log(
        float(np.exp(row - maximum).sum(dtype=np.float64))
    )
    value = log_normalizer - float(row[token_id])
    if not math.isfinite(value):
        raise SAL001ScoreError("Non-finite token negative log probability")
    return value


def score_session(
    model: TokenModel,
    formatter: SessionFormatter,
    session: dict[str, Any],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    exchanges = session["exchanges"]
    messages: list[dict[str, str]] = []
    for exchange in exchanges:
        messages.extend(
            (
                {"role": "user", "content": str(exchange["user"])},
                {"role": "assistant", "content": str(exchange["assistant"])},
            )
        )
    full_tokens, intervals = user_intervals(model, formatter, messages)
    if len(full_tokens) > N_CTX:
        raise SAL001ScoreError(
            f"Session {session['session_sha256']} has {len(full_tokens)} tokens"
        )
    model.reset()
    model.eval(full_tokens)
    rows: list[dict[str, Any]] = []
    for exchange, (start, end) in zip(exchanges, intervals, strict=True):
        values = [
            token_negative_log_probability(model.scores[index - 1], full_tokens[index])
            for index in range(start, end)
        ]
        token_ids = [int(value) for value in full_tokens[start:end]]
        rows.append(
            {
                "session_sha256": session["session_sha256"],
                "exchange_index": int(exchange["exchange_index"]),
                "content_sha256": exchange["content_sha256"],
                "rendered_token_sha256": canonical_digest(token_ids),
                "content_token_count": len(token_ids),
                "content_token_ids": token_ids,
                "preceding_rendered_token_count": start,
                "mean_nll": float(sum(values) / len(values)),
            }
        )
    return rows, {
        "session_sha256": session["session_sha256"],
        "rendered_token_count": len(full_tokens),
        "rendered_token_sha256": canonical_digest(
            [int(value) for value in full_tokens]
        ),
        "exchange_count": len(exchanges),
    }


def _idf_features(records: list[dict[str, Any]]) -> None:
    document_frequency: Counter[int] = Counter()
    for record in records:
        document_frequency.update(set(record["content_token_ids"]))
    count = len(records)
    for record in records:
        values = [
            math.log((1 + count) / (1 + document_frequency[token_id])) + 1
            for token_id in record["content_token_ids"]
        ]
        record["mean_content_token_idf"] = float(sum(values) / len(values))


def fit_label_free_adjustment(
    records: list[dict[str, Any]], session_lengths: dict[str, int]
) -> dict[str, Any]:
    _idf_features(records)
    matrix: list[list[float]] = []
    outcome: list[float] = []
    for record in records:
        exchange_count = session_lengths[record["session_sha256"]]
        position = (
            record["exchange_index"] / (exchange_count - 1)
            if exchange_count > 1
            else 0.0
        )
        features = [
            1.0,
            math.log1p(record["content_token_count"]),
            record["mean_content_token_idf"],
            position,
            math.log1p(record["preceding_rendered_token_count"]),
        ]
        matrix.append(features)
        outcome.append(record["mean_nll"])
        record["normalized_exchange_position"] = float(position)
    x = np.asarray(matrix, dtype=np.float64)
    y = np.asarray(outcome, dtype=np.float64)
    coefficients, _residuals, rank, singular_values = np.linalg.lstsq(
        x, y, rcond=None
    )
    if int(rank) != x.shape[1]:
        raise SAL001ScoreError("Label-free adjustment is rank deficient")
    fitted = x @ coefficients
    residual = y - fitted
    if not np.isfinite(residual).all():
        raise SAL001ScoreError("Label-free adjustment produced non-finite output")
    for record, fitted_value, residual_value in zip(
        records, fitted, residual, strict=True
    ):
        record["fitted_nll"] = float(fitted_value)
        record["adjusted_salience"] = float(residual_value)
    correlations: dict[str, float] = {}
    feature_names = (
        "intercept",
        "log1p_content_token_count",
        "mean_content_token_idf",
        "normalized_exchange_position",
        "log1p_preceding_rendered_token_count",
    )
    for index, name in enumerate(feature_names[1:], start=1):
        correlations[name] = float(np.corrcoef(x[:, index], residual)[0, 1])
    return {
        "feature_names": list(feature_names),
        "coefficients": [float(value) for value in coefficients],
        "rank": int(rank),
        "condition_number": float(singular_values[0] / singular_values[-1]),
        "residual_feature_correlations": correlations,
        "residual_mean": float(np.mean(residual)),
        "residual_std": float(np.std(residual)),
    }


def validate_manifest(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    if set(manifest) != {"schema", "dataset_sha256", "sessions"}:
        raise SAL001ScoreError("Scorer manifest has unauthorized top-level fields")
    if manifest["schema"] != "sal001-label-free-scorer-manifest-v1":
        raise SAL001ScoreError("Scorer manifest schema mismatch")
    sessions = manifest["sessions"]
    if not isinstance(sessions, list) or not sessions:
        raise SAL001ScoreError("Scorer manifest has no sessions")
    prior = ""
    for session in sessions:
        if set(session) != {"session_sha256", "exchange_count", "exchanges"}:
            raise SAL001ScoreError("Session has unauthorized fields")
        if session["session_sha256"] <= prior:
            raise SAL001ScoreError("Session hashes are not strictly sorted")
        prior = session["session_sha256"]
        exchanges = session["exchanges"]
        if session["exchange_count"] != len(exchanges):
            raise SAL001ScoreError("Session exchange count mismatch")
        for index, exchange in enumerate(exchanges):
            if set(exchange) != {
                "exchange_index",
                "content_sha256",
                "user",
                "assistant",
            }:
                raise SAL001ScoreError("Exchange has unauthorized fields")
            if exchange["exchange_index"] != index:
                raise SAL001ScoreError("Exchange indices are not contiguous")
            if not str(exchange["user"]).strip():
                raise SAL001ScoreError("Empty user content is not scoreable")
    return sessions


def _build_model(model_path: Path) -> tuple[Any, Any, dict[str, Any]]:
    import llama_cpp
    from llama_cpp import Llama
    from llama_cpp.llama_chat_format import Jinja2ChatFormatter

    if model_path.stat().st_size != MODEL_BYTES or sha256_file(model_path) != MODEL_SHA256:
        raise SAL001ScoreError("Pinned surprisal model identity mismatch")
    model = Llama(
        model_path=str(model_path),
        n_gpu_layers=-1,
        n_ctx=N_CTX,
        n_batch=N_BATCH,
        n_ubatch=N_UBATCH,
        logits_all=True,
        flash_attn=True,
        seed=SEED,
        verbose=False,
    )
    if model.n_vocab() != EXPECTED_VOCAB:
        raise SAL001ScoreError("Pinned vocabulary size mismatch")
    template = model.metadata["tokenizer.chat_template"]
    formatter = Jinja2ChatFormatter(
        template=template,
        bos_token=model.detokenize([model.token_bos()], special=True).decode("utf-8"),
        eos_token=model.detokenize([model.token_eos()], special=True).decode("utf-8"),
        add_generation_prompt=False,
    )
    metadata = {
        "llama_cpp_version": llama_cpp.__version__,
        "model_sha256": MODEL_SHA256,
        "model_bytes": MODEL_BYTES,
        "vocabulary_size": model.n_vocab(),
        "chat_template_sha256": canonical_digest(template),
        "seed": SEED,
        "n_ctx": N_CTX,
        "n_batch": N_BATCH,
        "n_ubatch": N_UBATCH,
        "n_gpu_layers": -1,
        "flash_attention": True,
        "logits_all": True,
        "parallel": 1,
        "speculative_decoding": False,
    }
    return model, formatter, metadata


def _synthetic_probe(model: TokenModel, formatter: SessionFormatter) -> dict[str, Any]:
    def make_session(content: str) -> dict[str, Any]:
        return {
            "session_sha256": canonical_digest(content),
            "exchanges": [
                {
                    "exchange_index": 0,
                    "content_sha256": canonical_digest("The sky is blue."),
                    "user": "The sky is blue.",
                    "assistant": "Yes, the sky often appears blue.",
                },
                {
                    "exchange_index": 1,
                    "content_sha256": canonical_digest(content),
                    "user": content,
                    "assistant": "Acknowledged.",
                },
            ],
        }

    predictable, _ = score_session(model, formatter, make_session("The sky is blue."))
    surprising, _ = score_session(
        model, formatter, make_session("The access phrase is qzv-91-xkappa-773.")
    )
    predictable_repeat, _ = score_session(
        model, formatter, make_session("The sky is blue.")
    )
    a = predictable[1]["mean_nll"]
    b = surprising[1]["mean_nll"]
    a2 = predictable_repeat[1]["mean_nll"]
    return {
        "predictable_mean_nll": a,
        "surprising_mean_nll": b,
        "predictable_repeat_mean_nll": a2,
        "repeat_exact": a == a2,
        "surprising_higher": b > a,
    }


def _runtime_environment() -> dict[str, Any]:
    gpu = subprocess.run(
        [
            "nvidia-smi",
            "--query-gpu=name,driver_version,memory.total",
            "--format=csv,noheader",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "gpu": gpu.stdout.strip() if gpu.returncode == 0 else "UNAVAILABLE",
        "pid": os.getpid(),
    }


def run(
    manifest_path: Path,
    model_path: Path,
    output_path: Path,
    *,
    session_limit: int | None = None,
) -> dict[str, Any]:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite score artifact: {output_path}")
    source_path = Path(__file__)
    source_sha_before = sha256_file(source_path)
    manifest = read_json(manifest_path)
    sessions = validate_manifest(manifest)
    if session_limit is not None:
        if session_limit <= 0:
            raise ValueError("session_limit must be positive")
        sessions = sessions[:session_limit]
    model, formatter, model_metadata = _build_model(model_path)
    started = time.perf_counter()
    records: list[dict[str, Any]] = []
    session_records: list[dict[str, Any]] = []
    for session in sessions:
        rows, session_row = score_session(model, formatter, session)
        records.extend(rows)
        session_records.append(session_row)
    session_lengths = {
        session["session_sha256"]: int(session["exchange_count"])
        for session in sessions
    }
    adjustment = fit_label_free_adjustment(records, session_lengths)
    synthetic = _synthetic_probe(model, formatter)
    elapsed = time.perf_counter() - started
    for record in records:
        del record["content_token_ids"]
    core = {
        "schema": "sal001-label-free-scores-v1",
        "manifest_sha256": sha256_file(manifest_path),
        "manifest_canonical_digest": canonical_digest(manifest),
        "model": model_metadata,
        "session_limit": session_limit,
        "sessions": session_records,
        "records": records,
        "adjustment": adjustment,
        "synthetic_probe": synthetic,
    }
    result = {
        **core,
        "deterministic_digest": canonical_digest(core),
        "runtime": {
            **_runtime_environment(),
            "elapsed_seconds": elapsed,
            "rendered_tokens": sum(
                row["rendered_token_count"] for row in session_records
            ),
            "rendered_tokens_per_second": (
                sum(row["rendered_token_count"] for row in session_records) / elapsed
            ),
        },
        "inputs": {
            "manifest": artifact_identity(manifest_path),
            "model": artifact_identity(model_path),
        },
        "source_sha256_before": source_sha_before,
    }
    source_sha_after = sha256_file(source_path)
    if source_sha_after != source_sha_before:
        raise SAL001ScoreError("Scorer source changed during decoding")
    result["source_sha256_after"] = source_sha_after
    write_json(output_path, result)
    return result

