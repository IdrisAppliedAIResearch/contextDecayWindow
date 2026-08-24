"""Gate and drive both HH-003 episodic-chat arms through the HH-002 harness."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any, Sequence

from analysis.hh002_batch import (
    BatchLedger,
    BatchRequest,
    answer_request,
    judge_request,
    run_scheduled,
    text_of,
    usage_of,
)
from analysis.hh002_batch_run import build_contexts, log
from analysis.hh002_dataset import load_corpus
from analysis.hh002_harness import DEFAULT_MODEL, Usage, deterministic_metrics
from analysis.hh002_run import DATASET, Prediction, _read_json, _write_json, score
from analysis.hh003_arms import EpisodicArm, SharedEmbedder
from episodic import __version__ as episodic_version
from openai import OpenAI
from retrieval_bakeoff.embedding import CarriedEmbedder

REPO = Path(__file__).resolve().parents[2]
BASE = REPO / "experiments/comparisons/hh_003/artifacts"
RUN = BASE / "run"
PREFLIGHT = BASE / "preflight"
PREREG_SHA = "ea5cf2b6"
ARMS = ("A_EPISODIC", "A_EPISODIC_ASPECT")
MODEL = "gpt-4o-mini-2024-07-18"
EXPECTED_CONTROLS = {
    "A_CDW/predictions.json": "37601e42b9f24fb6a6d01d78911f2b33a7a0554b568fff1151d3964353ae5628",
    "A_CDW/judged_r1.json": "367210a4b6aa37c763db23abd46a33810b6953bdb92be291146f8b8277d9d3cc",
    "A_RAG/predictions.json": "bc49bb20a6172dcfa68e3ef825487c776674afaf0f95e19cf9509d4dcaea68af",
    "A_RAG/judged_r1.json": "dd3ff262f3a1b27fc22a445c2f578676974c547a2eca6df1120f5cbe9a24c374",
    "A_FULL/predictions.json": "a6f82d0ed63eedb3aa1c84472c7ac978e5db6e5c8d5323cdf23ecbc712a150c9",
    "A_FULL/judged_r1.json": "467521c8e972d3728fac93b772ab453b3708f4d26607ecba16e1062e6ee6649a",
}


class HH003GateError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=REPO, check=True, capture_output=True, text=True
    ).stdout.strip()


def verify_offline_gates(*, require_contexts: bool = False) -> dict[str, Any]:
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", PREREG_SHA, "HEAD"], cwd=REPO
    ).returncode:
        raise HH003GateError(f"pre-registration {PREREG_SHA} is not an ancestor")

    cc007 = REPO / "experiments/components/episodic_chat/artifacts/cc007"
    port = json.loads((cc007 / "preflight.json").read_text(encoding="utf-8"))
    activation = json.loads((cc007 / "activation.json").read_text(encoding="utf-8"))
    if port.get("status") != "PASS" or activation.get("status") != "PASS":
        raise HH003GateError("CC-007 exploration artifacts do not pass")
    if port["pf6"]["mismatches"] or activation["mismatches"]:
        raise HH003GateError("CC-007 reproduction contains mismatches")

    controls = REPO / "experiments/comparisons/hh_002/artifacts"
    observed: dict[str, str] = {}
    for relative, expected in EXPECTED_CONTROLS.items():
        observed[relative] = _sha256(controls / relative)
        if observed[relative] != expected:
            raise HH003GateError(f"HH-002 control drifted: {relative}")

    contexts: dict[str, Any] = {}
    if require_contexts:
        for arm in ARMS:
            context_path = RUN / arm / "contexts.json"
            payload = _read_json(context_path) or {}
            items = payload.get("items", {})
            if len(items) != 1540:
                raise HH003GateError(f"{arm} has {len(items)}/1540 contexts")
            breaches = sum(
                item["detail"]["retrieval_chars_delivered"] > 32_000
                for item in items.values()
            )
            mutated = sum(not item["detail"]["store_unchanged"] for item in items.values())
            contexts[arm] = {
                "items": len(items),
                "budget_breaches": breaches,
                "store_mutations": mutated,
                "contexts_sha256": _sha256(context_path),
            }
            if breaches or mutated:
                raise HH003GateError(f"{arm} failed context invariants")
        left = (_read_json(RUN / ARMS[0] / "contexts.json") or {})["items"]
        right = (_read_json(RUN / ARMS[1] / "contexts.json") or {})["items"]
        different = sum(left[key]["context"] != right[key]["context"] for key in left)
        if different == 0:
            raise HH003GateError("ASPECT treatment is inert on all 1,540 items")
        contexts["different_payloads"] = different

    return {
        "schema": "hh003-gates-v1",
        "status": "PASS",
        "preregistration_commit": _git("rev-parse", PREREG_SHA),
        "head": _git("rev-parse", "HEAD"),
        "episodic_tree": _git("rev-parse", "HEAD:episodic"),
        "episodic_version": episodic_version,
        "runner_sha256": _sha256(Path(__file__)),
        "arms_sha256": _sha256(Path(__file__).with_name("hh003_arms.py")),
        "control_sha256": observed,
        "cc007_port_groups": port["pf6"]["actual_trace_groups"],
        "cc007_activation_payloads": activation["exact_final_payload_matches"],
        "contexts": contexts,
    }


class _ContextClient:
    usage = Usage()


def build_all_contexts() -> tuple[dict[str, dict[str, dict[str, Any]]], SharedEmbedder]:
    gate = verify_offline_gates()
    _write_json(PREFLIGHT / "g0_g2.json", gate)
    conversations = load_corpus(DATASET)
    shared = SharedEmbedder(CarriedEmbedder())
    arms = (
        EpisodicArm(RUN, aspect_enabled=False, embedder=shared),
        EpisodicArm(RUN, aspect_enabled=True, embedder=shared),
    )
    contexts: dict[str, dict[str, dict[str, Any]]] = {}
    for arm in arms:
        contexts[arm.name] = build_contexts(
            arm, conversations, _ContextClient(), RUN / arm.name
        )
    gate = verify_offline_gates(require_contexts=True)
    gate["prefix_replay"] = verify_prefix_replay(conversations, arms)
    gate["embedding_cache"] = {"hits": shared.hits, "misses": shared.misses}
    _write_json(PREFLIGHT / "g3_contexts.json", gate)
    return contexts, shared


def verify_prefix_replay(conversations, arms, prefix_items: int = 8) -> dict[str, Any]:
    conversation = conversations[0]
    questions = conversation.scored_questions[:prefix_items]
    result: dict[str, Any] = {}
    for arm in arms:
        state = arm.prepare(conversation, None)
        try:
            before = state.db_path.read_bytes()
            first = [arm.context(state, question, None) for question in questions]
            second = [arm.context(state, question, None) for question in questions]
            after = state.db_path.read_bytes()
        finally:
            arm.close_state(state)
        first_identity = [
            (payload, {key: value for key, value in detail.items() if key != "latency_ms"})
            for payload, _, detail in first
        ]
        second_identity = [
            (payload, {key: value for key, value in detail.items() if key != "latency_ms"})
            for payload, _, detail in second
        ]
        if first_identity != second_identity or before != after:
            raise HH003GateError(f"{arm.name} prefix replay is not byte-identical")
        result[arm.name] = {
            "items": len(questions),
            "byte_identical": True,
            "store_unchanged": True,
            "payload_sha256": [
                hashlib.sha256(payload.encode("utf-8")).hexdigest()
                for payload, _, _ in first
            ],
        }
    return result


def _load_contexts() -> dict[str, dict[str, dict[str, Any]]]:
    return {
        arm: (_read_json(RUN / arm / "contexts.json") or {})["items"]
        for arm in ARMS
    }


def _records(path: Path) -> dict[str, dict[str, Any]]:
    return {row["key"]: row for row in ((_read_json(path) or {}).get("records", []))}


def _assert_paid_preconditions() -> dict[str, Any]:
    gate = verify_offline_gates(require_contexts=True)
    committed_gate = _read_json(PREFLIGHT / "g3_contexts.json") or {}
    for field in ("runner_sha256", "arms_sha256", "episodic_tree"):
        if committed_gate.get(field) != gate.get(field):
            raise HH003GateError(f"committed G3 {field} does not match current code")
    for arm in ARMS:
        expected = committed_gate.get("contexts", {}).get(arm, {}).get(
            "contexts_sha256"
        )
        observed = gate["contexts"][arm]["contexts_sha256"]
        if expected != observed:
            raise HH003GateError(f"{arm} context cache does not match committed G3")
    dirty = _git("status", "--porcelain", "--untracked-files=no")
    if dirty:
        raise HH003GateError("tracked worktree is dirty before paid submission")
    if not os.environ.get("OPENAI_API_KEY"):
        raise HH003GateError("OPENAI_API_KEY is not set")
    committed = _git("ls-files", str(PREFLIGHT.relative_to(REPO) / "g3_contexts.json"))
    if not committed:
        raise HH003GateError("G3 context gate is not committed")
    gate["clean_tracked_worktree"] = True
    return gate


def _save_answers(
    prefix: str,
    results: dict[str, dict[str, Any]],
    contexts: dict[str, dict[str, dict[str, Any]]],
) -> None:
    arm = prefix.rsplit(".answers", 1)[0]
    path = RUN / arm / "predictions.json"
    done = _records(path)
    failures = 0
    for key, body in results.items():
        if "error" in body:
            failures += 1
            continue
        item = contexts[arm][key]
        prompt_tokens, completion_tokens = usage_of(body)
        done[key] = asdict(Prediction(
            sample_id=item["sample_id"], source_index=item["source_index"],
            category=item["category"], question=item["question"], answer=item["answer"],
            response=text_of(body), context_chars=item["context_chars"],
            units_delivered=item["units_delivered"], search_time=item["search_time"],
            response_time=0.0, prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens, cached_tokens=0,
        )) | {"key": key}
    _write_json(path, {"arm": arm, "model": MODEL, "transport": "batch",
                       "failures": failures,
                       "records": sorted(done.values(), key=lambda row: row["key"])})


def run_answers(poll_seconds: int) -> None:
    gate = _assert_paid_preconditions()
    _write_json(RUN / "run_precondition.json", gate)
    contexts = _load_contexts()
    work: list[tuple[str, list[BatchRequest]]] = []
    for arm in ARMS:
        done = _records(RUN / arm / "predictions.json")
        pending = [key for key in sorted(contexts[arm]) if key not in done]
        if pending:
            work.append((f"{arm}.answers", [
                answer_request(key, contexts[arm][key]["question"],
                               contexts[arm][key]["context"], MODEL)
                for key in pending
            ]))
    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    ledger = BatchLedger.load(RUN / "batch_ledger.json")
    if work:
        run_scheduled(client, work, ledger, poll_seconds, study="HH-003",
                      log=log, on_result=lambda p, r: _save_answers(p, r, contexts))
    for arm in ARMS:
        if len(_records(RUN / arm / "predictions.json")) != 1540:
            raise HH003GateError(f"{arm} answers are incomplete")


def run_judging(poll_seconds: int) -> None:
    _assert_paid_preconditions()
    predictions: dict[str, dict[str, dict[str, Any]]] = {
        arm: _records(RUN / arm / "predictions.json") for arm in ARMS
    }
    if any(len(rows) != 1540 for rows in predictions.values()):
        raise HH003GateError("all 3,080 answers must be sealed before judging")
    work: list[tuple[str, list[BatchRequest]]] = []
    for arm in ARMS:
        done = _records(RUN / arm / "judged_r1.json")
        pending = [row for key, row in sorted(predictions[arm].items()) if key not in done]
        if pending:
            work.append((f"{arm}.judge.r1", [
                judge_request(row["key"], row["question"], row["answer"],
                              row["response"], MODEL) for row in pending
            ]))

    def save(prefix: str, results: dict[str, dict[str, Any]]) -> None:
        arm = prefix.partition(".judge.r1")[0]
        path = RUN / arm / "judged_r1.json"
        done = _records(path)
        for key, body in results.items():
            prediction = predictions[arm][key]
            try:
                label = str(json.loads(text_of(body))["label"]) if "error" not in body else "__MALFORMED__"
            except Exception:  # noqa: BLE001
                label = "__MALFORMED__"
            metrics = deterministic_metrics(prediction["response"], prediction["answer"])
            done[key] = {"key": key, "sample_id": prediction["sample_id"],
                         "source_index": prediction["source_index"],
                         "category": prediction["category"],
                         "llm_score": int(label == "CORRECT"), "judge_label": label,
                         "f1": metrics["f1"], "exact_match": metrics["exact_match"]}
        _write_json(path, {"arm": arm, "replicate": 1, "transport": "batch",
                           "records": sorted(done.values(), key=lambda row: row["key"])})

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], max_retries=0)
    ledger = BatchLedger.load(RUN / "batch_ledger.json")
    if work:
        run_scheduled(client, work, ledger, poll_seconds, study="HH-003", log=log,
                      on_result=save)
    summary = {arm: score(list(_records(RUN / arm / "judged_r1.json").values()))
               for arm in ARMS}
    _write_json(RUN / "summary.json", {"model": MODEL, "arms": summary})
    for arm, result in summary.items():
        log(f"[{arm}] llm_score={result['llm_score']*100:.2f}% "
            f"f1={result['f1']:.4f} n={result['n']}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Drive registered HH-003")
    parser.add_argument("stage", choices=("gates", "contexts", "answers", "judge"))
    parser.add_argument("--poll-seconds", type=int, default=30)
    args = parser.parse_args(argv)
    if args.stage == "gates":
        print(json.dumps(verify_offline_gates(), sort_keys=True))
    elif args.stage == "contexts":
        build_all_contexts()
    elif args.stage == "answers":
        run_answers(args.poll_seconds)
    else:
        run_judging(args.poll_seconds)
    return 0


if __name__ == "__main__":
    sys.exit(main())
