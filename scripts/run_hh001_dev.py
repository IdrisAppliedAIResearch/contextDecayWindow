"""HH-001 development runner.

Modes, in the order they must be executed:

    pilot     contamination probe, timing, and the first observation of Mem0
    capture   populate the embedding cache every arm reads from
    commit    write and hash the six pre-commitments
    run       generate, seal, judge, gate, analyze
    report    render the committed result

Nothing runs by default and no mode is implied by another. ``run`` refuses to
start unless ``commit`` has already written a commitments file, because the
whole point of §6 is that the numbers were fixed first.

    python scripts/run_hh001_dev.py pilot --contamination 50
    python scripts/run_hh001_dev.py capture
    python scripts/run_hh001_dev.py commit --subsample 300 --replicates 3
    python scripts/run_hh001_dev.py run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from analysis.hh001_arms import (  # noqa: E402
    MEM0_IMPORT_HINT,
    CdwPairArm,
    FullContextArm,
    Mem0Arm,
    NoMemoryArm,
    RagFixedArm,
    chunk_text,
    mem0_available,
)
from analysis.hh001_commitments import (  # noqa: E402
    Commitments,
    default_commitments,
    plan_digest,
)
from analysis.hh001_corpus import (  # noqa: E402
    BUDGET,
    HOLDOUT_IDS,
    adversarial_population,
    load_corpus,
    primary_population,
    select_subsample,
    subsample_manifest,
)
from analysis.hh001_cost import CountingEmbedder, Ledger  # noqa: E402
from analysis.hh001_prompt import render_reader_prompt, template_manifest  # noqa: E402
from analysis.hh001_run import run as run_pipeline  # noqa: E402
from analysis.hh001_stats import reachability  # noqa: E402

ARTIFACTS = REPO_ROOT / "experiments/comparisons/hh_001/artifacts/dev"
DATASET = Path(os.environ.get("HH001_LOCOMO_PATH", r"C:\Users\muzaf\Downloads\locomo10.json"))
CACHE = ARTIFACTS / "hh001_embeddings.db"
COMMITMENTS = ARTIFACTS / "commitments.json"

#: A1's ceiling has to fit the reader's window. The holdout's longest
#: conversation is 90,034 characters, so this arm can overflow; the allowance
#: is passed in explicitly and any shortfall is recorded on the block.
READER_CONTEXT_TOKENS = int(os.environ.get("HH001_READER_CTX", "32768"))
READER_CHARS_PER_TOKEN = 4
READER_PROMPT_RESERVE = 2_000


def reader_char_allowance() -> int:
    return READER_CONTEXT_TOKENS * READER_CHARS_PER_TOKEN - READER_PROMPT_RESERVE


def _write(path: Path, payload: Any) -> str:
    import hashlib

    path.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(payload, ensure_ascii=True, indent=1, sort_keys=True) + "\n").encode(
        "utf-8"
    )
    path.write_bytes(raw)
    return hashlib.sha256(raw).hexdigest()


def make_embedder(mode: str = "reuse") -> Callable[[str], Any]:
    """The one embedder every arm that embeds shares (plan §4)."""
    from episodic import EmbeddingCache
    from retrieval_bakeoff.embedding import CarriedEmbedder

    model_path = Path(os.environ["CDW_EMBEDDING_MODEL_PATH"])
    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    cache = EmbeddingCache(CACHE, mode=mode, embedder=delegate)
    return cache


def make_mem0_client() -> Any:
    """Mem0 configured onto this programme's local models.

    Both choices are forced by the plan and neither is a Mem0 default: the
    embedder is the carried Qwen3 so the contrast is architecture rather than
    embedder quality, and the LLM is the local reader so no arm runs on a
    substrate the others do not.
    """
    if not mem0_available():
        raise SystemExit(MEM0_IMPORT_HINT)
    from mem0 import Memory  # type: ignore[import-not-found]

    server = os.environ.get("CDW_INFERENCE_SERVER_URL", "").rstrip("/")
    if not server:
        raise SystemExit(
            "Set CDW_INFERENCE_SERVER_URL so the Mem0 arm runs on the same "
            "local reader as every other arm."
        )
    return Memory.from_config(
        {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": os.environ.get("HH001_MEM0_MODEL", "local"),
                    "openai_base_url": f"{server}/v1",
                    "api_key": "not-used-by-llama-cpp",
                    "temperature": 0.0,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": os.environ.get("HH001_MEM0_EMBED_MODEL", "local-embed"),
                    "openai_base_url": f"{server}/v1",
                    "api_key": "not-used-by-llama-cpp",
                },
            },
        }
    )


# --------------------------------------------------------------------------
# pilot
# --------------------------------------------------------------------------


def cmd_pilot(args: argparse.Namespace) -> int:
    """The two cheap checks that come first, plus the Mem0 observation.

    Contamination runs A0 alone. If the reader answers most LoCoMo questions
    with no conversation at all, it has seen the corpus and no memory layer is
    discriminable — better learned now than after the rig is built.
    """
    from inference.provider import InferenceProvider

    conversations, items = load_corpus(DATASET, HOLDOUT_IDS)
    answerable = primary_population(items)
    sample = select_subsample(answerable, args.contamination)
    by_sample = {c.sample_id: c for c in conversations}

    provider = InferenceProvider()
    arm = NoMemoryArm()
    rows = []
    for item in sample:
        block = arm.block(item, by_sample[item.sample_id], BUDGET)
        prompt = render_reader_prompt(item.question, block.text)
        result = provider.complete(prompt, suppress_rule_detection=True)
        rows.append(
            {
                "comparison_key": item.comparison_key,
                "question": item.question,
                "gold": item.gold_answer,
                "answer": result.assistant_message,
            }
        )

    from analysis.hh001_endpoints import contains_gold

    contained = sum(1 for row in rows if contains_gold(row["answer"], row["gold"]))
    payload = {
        "schema": "hh001-contamination-probe-v1",
        "n": len(rows),
        "containment_hits": contained,
        "containment_rate": contained / len(rows) if rows else 0.0,
        "note": (
            "Containment is the weaker endpoint and undercounts. A high rate "
            "here means the reader answers without the conversation and the "
            "study cannot discriminate memory layers."
        ),
        "rows": rows,
    }
    digest = _write(ARTIFACTS / "pilot/contamination.json", payload)
    print(f"contamination probe: {contained}/{len(rows)} contained, sha256 {digest[:16]}")
    return 0


def cmd_observe_mem0(args: argparse.Namespace) -> int:
    """Watch what Mem0 actually does on one conversation.

    The ``1 + n`` generative calls per message pair figure is read from Mem0's
    paper. It has never been observed here.
    """
    conversations, _ = load_corpus(DATASET, HOLDOUT_IDS)
    conversation = conversations[0]
    ledger = Ledger(arm="A3_MEM0")
    arm = Mem0Arm(make_mem0_client)
    shape = arm.ingest(conversation)
    payload = {
        "schema": "hh001-mem0-observation-v1",
        "sample_id": conversation.sample_id,
        "pairs": len(conversation.record.candidates),
        "ingestion": shape,
        "cost": ledger.as_dict(),
    }
    digest = _write(ARTIFACTS / "pilot/mem0_observation.json", payload)
    print(f"mem0 observation written, sha256 {digest[:16]}")
    return 0


# --------------------------------------------------------------------------
# capture / commit / run
# --------------------------------------------------------------------------


def cmd_capture(args: argparse.Namespace) -> int:
    """Populate the shared embedding cache. Zero generative calls."""
    conversations, items = load_corpus(DATASET, HOLDOUT_IDS)
    texts: set[str] = set()
    for conversation in conversations:
        for source in conversation.record.candidates:
            texts.add(source.candidate.text)
        for chunk in chunk_text(conversation.full_text, args.chunk_size, args.chunk_overlap):
            texts.add(chunk)
    for item in items:
        texts.add(item.question)

    embed = make_embedder(mode="populate")
    ordered = sorted(texts)
    for text in ordered:
        embed(text)
    payload = {
        "schema": "hh001-vector-capture-v1",
        "unique_texts": len(ordered),
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "model_generation_calls": 0,
    }
    digest = _write(ARTIFACTS / "runtime/vector_capture.json", payload)
    print(f"captured {len(ordered)} vectors, sha256 {digest[:16]}")
    return 0


def cmd_commit(args: argparse.Namespace) -> int:
    _, items = load_corpus(DATASET, HOLDOUT_IDS)
    answerable = primary_population(items)
    adversarial = adversarial_population(items)
    if args.subsample > len(answerable):
        raise SystemExit(
            f"Subsample {args.subsample} exceeds the answerable population "
            f"{len(answerable)}"
        )
    commitments = default_commitments(
        subsample_size=args.subsample,
        replicates=args.replicates,
        plan_sha256=plan_digest(REPO_ROOT),
        template_manifest=template_manifest().as_dict(),
    )
    digest = commitments.write(COMMITMENTS)
    manifest = subsample_manifest(answerable, args.subsample)
    _write(ARTIFACTS / "subsample_manifest.json", manifest)
    _write(
        ARTIFACTS / "reachability.json",
        {
            "schema": "hh001-reachability-v1",
            "answerable_population": len(answerable),
            "adversarial_population": len(adversarial),
            **reachability(args.subsample),
        },
    )
    print(f"commitments sha256 {digest}")
    print(f"  arms       {', '.join(commitments.arms)}")
    print(f"  budget     {commitments.budget_chars} chars")
    print(f"  items      {commitments.subsample_size} of {len(answerable)} answerable")
    print(f"  replicates {commitments.replicates}", end="")
    if commitments.below_confirmatory_replicates:
        print("  (below the confirmatory minimum of 5, by design)")
    else:
        print()
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    if not COMMITMENTS.is_file():
        raise SystemExit(
            "No commitments file. Run `commit` first: §6 exists so the numbers "
            "are fixed before any of them are seen."
        )
    commitments = Commitments.load(COMMITMENTS)
    from inference.provider import InferenceProvider

    conversations, items = load_corpus(DATASET, HOLDOUT_IDS)
    answerable = primary_population(items)
    sample = select_subsample(answerable, commitments.subsample_size, commitments.seed)
    by_sample = {c.sample_id: c for c in conversations}

    provider = InferenceProvider()

    def reader(prompt: str) -> str:
        return provider.complete(prompt, suppress_rule_detection=True).assistant_message

    def judge(prompt: str) -> str:
        return provider.complete(prompt, suppress_rule_detection=True).assistant_message

    # Each arm gets its own ledger, and its own embedder wrapped against that
    # ledger, so an embedding call is attributed to the arm that made it. A
    # shared unwrapped embedder would report zero for every arm, which is the
    # exact number this study is here to earn rather than assume.
    ledgers = {
        name: Ledger(arm=name)
        for name in (
            "A0_NO_MEMORY",
            "A1_FULL_CONTEXT",
            "A2_CDW_PAIR",
            "A3_MEM0",
            "A4_RAG_FIXED",
        )
    }
    base_embed = make_embedder(mode="reuse")
    arms = [
        NoMemoryArm(),
        FullContextArm(reader_char_allowance=reader_char_allowance()),
        CdwPairArm(CountingEmbedder(base_embed, ledgers["A2_CDW_PAIR"], "query")),
    ]
    if not args.without_mem0:
        arms.append(Mem0Arm(make_mem0_client))
    arms.append(
        RagFixedArm(CountingEmbedder(base_embed, ledgers["A4_RAG_FIXED"], "query"))
    )
    ledgers = {arm.name: ledgers[arm.name] for arm in arms}

    result = run_pipeline(
        arms,
        sample,
        by_sample,
        commitments,
        reader=reader,
        judge=judge,
        outcome_dir=ARTIFACTS / "outcomes",
        ledgers=ledgers,
    )
    digest = _write(ARTIFACTS / "result.json", result)
    print(f"result sha256 {digest}")
    print(json.dumps(result["contrast"], indent=1))
    if not result["directional_claim_permitted"]:
        print("\nNO DIRECTIONAL CLAIM: " + result["sign_check"]["reason"])
    return 0


def cmd_report(args: argparse.Namespace) -> int:
    path = ARTIFACTS / "result.json"
    if not path.is_file():
        raise SystemExit("No result to report. Run `run` first.")
    print(path.read_text(encoding="utf-8"))
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    pilot = sub.add_parser("pilot", help="contamination probe")
    pilot.add_argument("--contamination", type=int, default=50)
    pilot.set_defaults(func=cmd_pilot)

    observe = sub.add_parser("observe-mem0", help="watch Mem0 ingest one conversation")
    observe.set_defaults(func=cmd_observe_mem0)

    capture = sub.add_parser("capture", help="populate the shared embedding cache")
    capture.add_argument("--chunk-size", type=int, default=1_000)
    capture.add_argument("--chunk-overlap", type=int, default=200)
    capture.set_defaults(func=cmd_capture)

    commit = sub.add_parser("commit", help="write and hash the six pre-commitments")
    commit.add_argument("--subsample", type=int, required=True)
    commit.add_argument("--replicates", type=int, required=True)
    commit.set_defaults(func=cmd_commit)

    run_cmd = sub.add_parser("run", help="generate, seal, judge, gate, analyze")
    run_cmd.add_argument(
        "--without-mem0",
        action="store_true",
        help="run the other four arms; the contrast will refuse to compute",
    )
    run_cmd.set_defaults(func=cmd_run)

    report = sub.add_parser("report", help="print the committed result")
    report.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
