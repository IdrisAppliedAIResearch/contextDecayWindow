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
import time
from pathlib import Path
from typing import Any, Callable

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_env() -> None:
    """Load `.env` the way conftest does, so this runner stands alone.

    Values already in the environment win, so an explicit export overrides
    the file rather than being silently replaced by it.
    """
    path = REPO_ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


_load_env()
# Mem0 phones home by default; a research run does not.
os.environ.setdefault("MEM0_TELEMETRY", "False")

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
from analysis.hh001_run import generate_arm, run as run_pipeline  # noqa: E402
from analysis.hh001_stats import reachability  # noqa: E402

ARTIFACTS = REPO_ROOT / "experiments/comparisons/hh_001/artifacts/dev"
DATASET = Path(os.environ.get("HH001_LOCOMO_PATH", r"C:\Users\muzaf\Downloads\locomo10.json"))
CACHE = ARTIFACTS / "hh001_embeddings.db"
COMMITMENTS = ARTIFACTS / "commitments.json"
CACHE_MANIFEST = ARTIFACTS / "runtime/vector_capture.json"

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


def _carried_delegate():
    from retrieval_bakeoff.embedding import CarriedEmbedder

    model_path = Path(os.environ["CDW_EMBEDDING_MODEL_PATH"])
    delegate = CarriedEmbedder(model_path)
    delegate.assert_carried_model()
    return delegate


def make_embedder(mode: str = "reuse") -> Callable[[str], Any]:
    """The one embedder every arm that embeds shares (plan §4).

    Reuse binds the cache to the file and content digests `capture` recorded,
    so a cache that changed under us fails loudly instead of quietly serving
    different vectors. CC-006's seal is the reason this is not optional.
    """
    from episodic import EmbeddingCache

    delegate = _carried_delegate()
    if mode == "populate":
        return EmbeddingCache(CACHE, mode="populate", embedder=delegate)
    if not CACHE_MANIFEST.is_file():
        raise SystemExit(
            f"No vector manifest at {CACHE_MANIFEST}. Run `capture` first."
        )
    record = json.loads(CACHE_MANIFEST.read_text(encoding="utf-8"))["cache"]
    return EmbeddingCache(
        CACHE,
        mode="reuse",
        expected_file_sha256=record["file_sha256"],
        expected_content_sha256=record["content_sha256"],
        expected_model_sha256=delegate.model_sha256,
    )


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
            # The local llama-server is started without `--embeddings` and
            # answers /v1/embeddings with 501, and its start script is not
            # ours to change. `scripts/hh001_embedding_shim.py` serves the
            # carried embedder on this port instead, bit-identically to the
            # sealed cache every other arm reads, so plan section 4's
            # one-embedder-for-every-arm rule still holds.
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": "carried-qwen3-embedding",
                    "embedding_dims": 1024,
                    "openai_base_url": os.environ.get(
                        "HH001_EMBED_SHIM_URL", "http://127.0.0.1:8100/v1"
                    ),
                    "api_key": "not-used-by-the-shim",
                },
            },
            # Study-owned store. Mem0 defaults to a shared /tmp/qdrant whose
            # collection dimension is fixed on first use, so a run that once
            # touched a 1536-dim embedder poisons every later run with a
            # shape mismatch. Isolating it here also makes the arm's state
            # something we can delete and rebuild deterministically.
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "collection_name": "hh001",
                    "embedding_model_dims": 1024,
                    "path": str(ARTIFACTS / "mem0_store"),
                },
            },
            "history_db_path": str(ARTIFACTS / "mem0_history.db"),
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
    """Watch what Mem0 actually does on real conversation pairs.

    The `1 + n` generative calls per message pair figure is read from Mem0's
    paper and has never been observed here. Mem0 talks to the server through
    its own OpenAI client, so the study's ledger cannot see those calls; they
    are counted by wrapping the client's `create` methods, which counts every
    call Mem0 makes regardless of why it made it.
    """
    import openai
    from openai.resources.chat.completions import Completions
    from openai.resources.embeddings import Embeddings

    counts = {"chat": 0, "embed": 0}
    chat_original = Completions.create
    embed_original = Embeddings.create

    def counted_chat(self, *a, **k):
        counts["chat"] += 1
        return chat_original(self, *a, **k)

    def counted_embed(self, *a, **k):
        counts["embed"] += 1
        return embed_original(self, *a, **k)

    Completions.create = counted_chat
    Embeddings.create = counted_embed
    try:
        conversations, _ = load_corpus(DATASET, HOLDOUT_IDS)
        conversation = conversations[0]
        pairs = list(conversation.record.candidates)[: args.pairs]
        arm = Mem0Arm(make_mem0_client)
        lengths = []
        started = time.perf_counter()
        for source in pairs:
            arm.client.add(
                source.candidate.text,
                user_id=f"observe-{conversation.sample_id}",
            )
        ingest_s = time.perf_counter() - started
        ingest_chat = counts["chat"]
        ingest_embed = counts["embed"]

        probe = arm.client.search(
            "What did they talk about?",
            top_k=100,
            threshold=0.0,
            filters={"user_id": f"observe-{conversation.sample_id}"},
        )
        from analysis.hh001_arms import _mem0_memory_texts

        memories = _mem0_memory_texts(probe)
        lengths = sorted(len(m) for m in memories)
    finally:
        Completions.create = chat_original
        Embeddings.create = embed_original

    payload = {
        "schema": "hh001-mem0-observation-v1",
        "mem0_version": __import__("importlib.metadata", fromlist=["x"]).version("mem0ai"),
        "sample_id": conversation.sample_id,
        "pairs_ingested": len(pairs),
        "ingest_seconds": round(ingest_s, 1),
        "generative_calls_at_ingest": ingest_chat,
        "embedding_calls_at_ingest": ingest_embed,
        "generative_calls_per_pair": round(ingest_chat / max(1, len(pairs)), 2),
        "paper_claim": "1 + n generative calls per message pair (arXiv:2504.19413)",
        "memories_returned": len(memories),
        "memory_chars_p0_p50_p100": (
            [lengths[0], lengths[len(lengths) // 2], lengths[-1]] if lengths else []
        ),
        "total_memory_chars": sum(lengths),
        "budget_chars": BUDGET,
        "note": (
            "Payload size against the 16,000-char matched budget decides whether "
            "budget matching helps or hurts Mem0 (plan section 4)."
        ),
    }
    digest = _write(ARTIFACTS / "pilot/mem0_observation.json", payload)
    print(f"mem0 {payload['mem0_version']} on {len(pairs)} pairs of "
          f"{conversation.sample_id}")
    print(f"  generative calls at ingest : {ingest_chat} "
          f"({payload['generative_calls_per_pair']}/pair)")
    print(f"  embedding calls at ingest  : {ingest_embed}")
    print(f"  ingest wall clock          : {ingest_s:.1f}s")
    print(f"  memories returned          : {len(memories)}")
    print(f"  total memory chars         : {sum(lengths)} vs {BUDGET} budget")
    print(f"sha256 {digest[:16]}")
    return 0


# --------------------------------------------------------------------------
# capture / commit / run
# --------------------------------------------------------------------------


def cmd_ingest_mem0(args: argparse.Namespace) -> int:
    """Write every holdout conversation into Mem0's store.

    Separate from `run` because it is the expensive half of the Mem0 arm and
    it only has to happen once: roughly 4.6 seconds and one generative call
    per message pair, against about 1,610 pairs. Its cost is recorded here
    rather than folded into the query-time ledger, because ingest cost is the
    axis on which the two architectures actually differ.
    """
    import openai
    from openai.resources.chat.completions import Completions
    from openai.resources.embeddings import Embeddings

    counts = {"chat": 0, "embed": 0}
    chat_original, embed_original = Completions.create, Embeddings.create

    def counted_chat(self, *a, **k):
        counts["chat"] += 1
        return chat_original(self, *a, **k)

    def counted_embed(self, *a, **k):
        counts["embed"] += 1
        return embed_original(self, *a, **k)

    Completions.create, Embeddings.create = counted_chat, counted_embed
    conversations, _ = load_corpus(DATASET, HOLDOUT_IDS)
    arm = Mem0Arm(make_mem0_client)
    rows = {}
    started = time.perf_counter()
    try:
        for conversation in conversations:
            before_chat, before_embed = counts["chat"], counts["embed"]
            began = time.perf_counter()
            pairs = list(conversation.record.candidates)
            for index, source in enumerate(pairs, start=1):
                arm.client.add(
                    source.candidate.text,
                    user_id=f"{arm.user_id}-{conversation.sample_id}",
                )
                if index % 25 == 0:
                    rate = (time.perf_counter() - began) / index
                    print(f"    {conversation.sample_id} {index}/{len(pairs)}"
                          f"  {rate:.2f}s/pair", flush=True)
            elapsed = time.perf_counter() - began
            rows[conversation.sample_id] = {
                "pairs": len(pairs),
                "seconds": round(elapsed, 1),
                "generative_calls": counts["chat"] - before_chat,
                "embedding_calls": counts["embed"] - before_embed,
            }
            print(f"  {conversation.sample_id}: {len(pairs)} pairs, "
                  f"{elapsed:.0f}s, {counts['chat'] - before_chat} generative calls",
                  flush=True)
    finally:
        Completions.create, Embeddings.create = chat_original, embed_original

    total_pairs = sum(r["pairs"] for r in rows.values())
    payload = {
        "schema": "hh001-mem0-ingest-v1",
        "conversations": rows,
        "total_pairs": total_pairs,
        "total_generative_calls": counts["chat"],
        "total_embedding_calls": counts["embed"],
        "generative_calls_per_pair": round(counts["chat"] / max(1, total_pairs), 3),
        "total_seconds": round(time.perf_counter() - started, 1),
        "comparison": (
            "This component ingests the same pairs with zero generative calls; "
            "that zero is architectural and is not a finding. The measured "
            "number here is."
        ),
    }
    digest = _write(ARTIFACTS / "cost/mem0_ingest.json", payload)
    print()
    print(f"ingested {total_pairs} pairs, {counts['chat']} generative calls "
          f"({payload['generative_calls_per_pair']}/pair), "
          f"{payload['total_seconds'] / 60:.0f} min")
    print(f"sha256 {digest[:16]}")
    return 0


def cmd_store_probe(args: argparse.Namespace) -> int:
    """Ask whether Mem0's store still contains the answers at all.

    `fidelity` measures whether the gold answer reached the delivered block.
    For the verbatim arms a miss is a selection failure by construction. For
    Mem0 a miss has two possible causes and they mean different things:

      * the fact is in the store and retrieval did not surface it — selection;
      * the fact is not in the store at all — extraction dropped it when the
        model decided what was worth remembering.

    This dumps every memory Mem0 holds per conversation and checks the gold
    answers against the whole store, so the two are separated by measurement
    rather than argued about. Zero generative calls: it reads what is already
    written.
    """
    from analysis.hh001_endpoints import contains_gold

    conversations, items = load_corpus(DATASET, HOLDOUT_IDS)
    answerable = primary_population(items)
    arm = Mem0Arm(make_mem0_client)
    client = arm.client

    by_conversation = {c.sample_id: c for c in conversations}
    rows = {}
    for conversation in conversations:
        user = f"{arm.user_id}-{conversation.sample_id}"
        # `get_all` pages at top_k=20 by default. Reading that default and
        # calling the result "the store" measures the page size and reports it
        # as retention — it produced a 51/315 that was pure artifact. Ask for
        # more than the store can hold, then assert the cap did not bind.
        stored = client.get_all(filters={"user_id": user}, top_k=args.top_k)
        from analysis.hh001_arms import _mem0_memory_texts

        memories = _mem0_memory_texts(stored)
        if len(memories) >= args.top_k:
            raise SystemExit(
                f"{conversation.sample_id} returned {len(memories)} memories at "
                f"top_k={args.top_k}: the cap bound, so this is a page and not "
                "the store. Raise --top-k and re-run."
            )
        haystack = "\n".join(memories)
        pool = [i for i in answerable if i.sample_id == conversation.sample_id]
        eligible = [
            i for i in pool
            if contains_gold(conversation.full_text, i.gold_answer)
        ]
        in_store = sum(1 for i in eligible if contains_gold(haystack, i.gold_answer))
        rows[conversation.sample_id] = {
            "memories": len(memories),
            "memory_chars": len(haystack),
            "source_chars": conversation.chars,
            "compression": round(len(haystack) / conversation.chars, 4)
            if conversation.chars else None,
            "answerable_items": len(pool),
            "gold_stated_in_source": len(eligible),
            "gold_present_in_store": in_store,
            "gold_absent_from_store": len(eligible) - in_store,
            "retention_rate": round(in_store / len(eligible), 4) if eligible else None,
        }
        print(f"  {conversation.sample_id}: {len(memories)} memories, "
              f"{in_store}/{len(eligible)} answers retained", flush=True)

    total_eligible = sum(r["gold_stated_in_source"] for r in rows.values())
    total_present = sum(r["gold_present_in_store"] for r in rows.values())
    payload = {
        "schema": "hh001-mem0-store-probe-v1",
        "by_conversation": rows,
        "gold_stated_in_source": total_eligible,
        "gold_present_in_store": total_present,
        "gold_absent_from_store": total_eligible - total_present,
        "retention_rate": round(total_present / total_eligible, 4)
        if total_eligible else None,
        "reads": (
            "This is a containment test over Mem0's own memory text. A gold "
            "answer can be preserved in meaning while failing it - a "
            "paraphrase counts as absent here. So this bounds extraction loss "
            "from above, and the bound is what it is: a number this test can "
            "overstate, never understate."
        ),
        "comparison": (
            "The verbatim arms retain every answer their source states, by "
            "construction, because they store the turn unchanged. That is "
            "architecture, not a measured win, and must not be reported as one."
        ),
    }
    digest = _write(ARTIFACTS / "cost/mem0_store_probe.json", payload)
    print()
    print(f"answers stated in source : {total_eligible}")
    print(f"still present in store   : {total_present}")
    print(f"absent from store        : {total_eligible - total_present}")
    print(f"sha256 {digest[:16]}")
    return 0


def cmd_storage(args: argparse.Namespace) -> int:
    """Bytes on disk per stored turn, per arm.

    Mem0's store is measured directly, because it exists as files. A2's and
    A4's are computed from what they actually keep — the verbatim text plus one
    float32 vector per unit — rather than measured from the shared capture
    cache, which holds every arm's texts at once and would attribute A4's
    chunks to A2. Both are stated so neither is mistaken for the other.
    """
    conversations, _ = load_corpus(DATASET, HOLDOUT_IDS)
    turns = sum(c.turn_count for c in conversations)
    pairs = sum(len(c.record.candidates) for c in conversations)
    vector_bytes = 1024 * 4  # float32 x 1024 dims

    pair_text = sum(
        len(src.candidate.text.encode("utf-8"))
        for c in conversations for src in c.record.candidates
    )
    chunks = [
        chunk for c in conversations
        for chunk in chunk_text(c.full_text, args.chunk_size, args.chunk_overlap)
    ]
    chunk_text_bytes = sum(len(c.encode("utf-8")) for c in chunks)

    def tree_bytes(path: Path) -> int:
        if not path.exists():
            return 0
        if path.is_file():
            return path.stat().st_size
        return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())

    mem0_bytes = (
        tree_bytes(ARTIFACTS / "mem0_store")
        + tree_bytes(ARTIFACTS / "mem0_history.db")
    )

    rows = {
        "A2_CDW_PAIR": {
            "units": pairs,
            "unit": "adjacent-turn pair",
            "text_bytes": pair_text,
            "vector_bytes": pairs * vector_bytes,
            "total_bytes": pair_text + pairs * vector_bytes,
            "measured": "computed from what the arm keeps",
        },
        "A4_RAG_FIXED": {
            "units": len(chunks),
            "unit": f"{args.chunk_size}-char chunk, {args.chunk_overlap} overlap",
            "text_bytes": chunk_text_bytes,
            "vector_bytes": len(chunks) * vector_bytes,
            "total_bytes": chunk_text_bytes + len(chunks) * vector_bytes,
            "measured": "computed from what the arm keeps",
        },
        "A3_MEM0": {
            "units": None,
            "unit": "model-extracted memory",
            "text_bytes": None,
            "vector_bytes": None,
            "total_bytes": mem0_bytes,
            "measured": "measured on disk: qdrant store plus history.db",
        },
    }
    for value in rows.values():
        value["bytes_per_turn"] = (
            round(value["total_bytes"] / turns, 1) if turns else None
        )
    payload = {
        "schema": "hh001-storage-v1",
        "conversations": len(conversations),
        "source_turns": turns,
        "source_text_bytes": sum(len(c.full_text.encode("utf-8")) for c in conversations),
        "vector_bytes_per_unit": vector_bytes,
        "arms": rows,
        "caveat": (
            "A0 stores nothing and A1 stores the transcript itself, so neither "
            "is listed. Mem0's figure includes its history log, which is an "
            "audit trail rather than the retrievable store; it is reported "
            "whole rather than split, because splitting it would be a guess."
        ),
    }
    digest = _write(ARTIFACTS / "cost/storage.json", payload)
    print(f"{turns} source turns across {len(conversations)} conversations")
    for arm, value in sorted(rows.items()):
        total = value["total_bytes"]
        print(f"  {arm:16s} {total:>12,} bytes  "
              f"{value['bytes_per_turn']:>8} /turn  ({value['measured']})")
    print(f"sha256 {digest[:16]}")
    return 0


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

    from episodic import EmbeddingCache

    delegate = _carried_delegate()
    ordered = sorted(texts)
    with EmbeddingCache(CACHE, mode="populate", embedder=delegate) as cache:
        for text in ordered:
            cache(text)
        record = cache.record()
    payload = {
        "schema": "hh001-vector-capture-v1",
        "unique_texts": len(ordered),
        "chunk_size": args.chunk_size,
        "chunk_overlap": args.chunk_overlap,
        "model_generation_calls": 0,
        "cache": record,
    }
    digest = _write(CACHE_MANIFEST, payload)
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
    conversations, items = load_corpus(DATASET, HOLDOUT_IDS)
    answerable = primary_population(items)
    sample = select_subsample(answerable, commitments.subsample_size, commitments.seed)
    by_sample = {c.sample_id: c for c in conversations}

    # HH-001's own client: the carried provider discards prompt tokens, and
    # prompt tokens are the axis these arms differ most on.
    from analysis.hh001_reader import LlamaReader

    server = os.environ.get("CDW_INFERENCE_SERVER_URL", "http://127.0.0.1:8000")
    reader = LlamaReader(server)
    judge_client = LlamaReader(server, n_predict=128)

    def judge(prompt: str) -> str:
        return judge_client(prompt, 0).text

    _write(ARTIFACTS / "runtime/reader.json", {
        "schema": "hh001-reader-runtime-v1",
        **reader.runtime_record(),
    })

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


def cmd_timing(args: argparse.Namespace) -> int:
    """Timing pilot: one conversation, every available arm, wall clock.

    Produces the two numbers the commitments need (`n` and `R`) and says
    whether A4 survives. Mem0 is included only when installed; its absence is
    recorded rather than silently skipped.
    """
    from inference.provider import InferenceProvider

    conversations, items = load_corpus(DATASET, HOLDOUT_IDS)
    by_sample = {c.sample_id: c for c in conversations}
    pool = [i for i in primary_population(items) if i.sample_id == args.conversation]
    if not pool:
        raise SystemExit(f"No answerable items for {args.conversation}")
    sample = select_subsample(pool, min(args.items, len(pool)))

    provider = InferenceProvider()

    def reader(prompt: str) -> str:
        return provider.complete(prompt, suppress_rule_detection=True).assistant_message

    base_embed = make_embedder(mode="reuse")
    specs = [
        ("A0_NO_MEMORY", lambda led: NoMemoryArm()),
        ("A1_FULL_CONTEXT",
         lambda led: FullContextArm(reader_char_allowance=reader_char_allowance())),
        ("A2_CDW_PAIR",
         lambda led: CdwPairArm(CountingEmbedder(base_embed, led, "query"))),
        ("A4_RAG_FIXED",
         lambda led: RagFixedArm(CountingEmbedder(base_embed, led, "query"))),
    ]
    if mem0_available():
        specs.insert(3, ("A3_MEM0", lambda led: Mem0Arm(make_mem0_client)))

    rows = {}
    for name, build in specs:
        ledger = Ledger(arm=name)
        arm = build(ledger)
        started = time.perf_counter()
        answers = generate_arm(
            arm, sample, by_sample, reader=reader,
            budget=BUDGET, replicates=args.replicates, ledger=ledger,
        )
        elapsed = time.perf_counter() - started
        per_call = elapsed / max(1, len(answers))
        rows[name] = {
            "seconds": round(elapsed, 1),
            "calls": len(answers),
            "seconds_per_call": round(per_call, 2),
            "mean_block_chars": round(
                sum(a.block_chars for a in answers) / max(1, len(answers))
            ),
            "truncated_calls": sum(1 for a in answers if a.block_truncated),
            "cost": ledger.as_dict(),
        }
        print(f"  {name:18s} {elapsed:7.1f}s over {len(answers):3d} calls"
              f"  = {per_call:5.2f}s/call")

    arms_in_run = len(rows) + (0 if mem0_available() else 1)
    per_call = sum(r["seconds_per_call"] for r in rows.values()) / len(rows)
    payload = {
        "schema": "hh001-timing-pilot-v1",
        "conversation": args.conversation,
        "items": len(sample),
        "replicates": args.replicates,
        "mem0_installed": mem0_available(),
        "arms": rows,
        "mean_seconds_per_call": round(per_call, 2),
        "projection_note": (
            "A full run costs n * R * arms reader calls plus one judge call "
            "each. Judging is a second pass of the same size."
        ),
        "projected_hours": {
            str(n): round(n * args.replicates * arms_in_run * per_call * 2 / 3600, 2)
            for n in (100, 200, 300, 500, 850)
        },
    }
    digest = _write(ARTIFACTS / "pilot/timing.json", payload)
    print()
    print(f"mean {per_call:.2f}s/call over {len(rows)} arms"
          f"  (mem0 {'installed' if mem0_available() else 'ABSENT'})")
    print("projected hours for a full run, generation plus judging:")
    for n, hours in payload["projected_hours"].items():
        print(f"  n={n:>4}  R={args.replicates}  ->  {hours:6.2f} h")
    print(f"sha256 {digest[:16]}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="mode", required=True)

    pilot = sub.add_parser("pilot", help="contamination probe")
    pilot.add_argument("--contamination", type=int, default=50)
    pilot.set_defaults(func=cmd_pilot)

    observe = sub.add_parser("observe-mem0", help="watch Mem0 ingest real pairs")
    observe.add_argument("--pairs", type=int, default=10)
    observe.set_defaults(func=cmd_observe_mem0)

    ingest = sub.add_parser("ingest-mem0", help="write all conversations into Mem0")
    ingest.set_defaults(func=cmd_ingest_mem0)

    probe = sub.add_parser("store-probe", help="what Mem0 still holds after extraction")
    probe.add_argument("--top-k", type=int, default=100_000)
    probe.set_defaults(func=cmd_store_probe)

    storage = sub.add_parser("storage", help="bytes on disk per stored turn")
    storage.add_argument("--chunk-size", type=int, default=1_000)
    storage.add_argument("--chunk-overlap", type=int, default=200)
    storage.set_defaults(func=cmd_storage)

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

    timing = sub.add_parser("timing", help="timing pilot on one conversation")
    timing.add_argument("--conversation", default="conv-26")
    timing.add_argument("--items", type=int, default=5)
    timing.add_argument("--replicates", type=int, default=3)
    timing.set_defaults(func=cmd_timing)

    report = sub.add_parser("report", help="print the committed result")
    report.set_defaults(func=cmd_report)

    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
