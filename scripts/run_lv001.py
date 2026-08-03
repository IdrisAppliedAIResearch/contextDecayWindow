"""LV-001 live validation run: one arm of the 121-turn corpus.

Registered design: `experiments/components/live_validation/LV_001_pre_registration.md`
Anchor: `89614a0c3799e0e96edb7809ba11eac07d39ac90`

Two arms, differing only in which episodes reach the window:

  * **L-A0** — the deployed baseline. Recency N-cap union K-threshold
    candidates, per-item cosine order, via the prior committed engine
    `src/memory/context_matched_stm.py`.
  * **L-A3** — the shipping configuration `A3_l0.1_r0.0_k16`, via `episodic`'s
    set-level coverage selector.

Everything else is shared and must stay shared. Both arms use the same script,
the same seed, the same server, the same system prompt, the same
`<pinned_rules/> / <recent_context> / <retrieved_stm> / <current_turn>` scaffold,
and — because the A0 engine already imports them — **the same packer and the
same renderer from `episodic`**. So the arms differ in candidate selection and
in nothing else that touches the prompt.

Rule pinning is absent from both. The shipping architecture has none (PAPER-001
§6.2 records it as removed), so leaving it enabled for the control only would
put a block in one arm's prompt and not the other's and confound the comparison
with something neither selector chooses.

    python scripts/run_lv001.py --arm a3 --turns 35     # ablation, gate G6
    python scripts/run_lv001.py --arm a3                # full 121-turn run
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "episodic" / "src"))

import numpy as np  # noqa: E402

SCRIPT = REPO / "experiments/study_005/script.json"
ROOT = REPO / "experiments/components/live_validation"
BUDGET = 32_000
N_CAP = 32
K_THRESHOLD = 0.48
EMBEDDING_MODEL = (
    "C:/Users/muzaf/.cache/huggingface/hub/Qwen3-Embedding-0.6B-GGUF/"
    "Qwen3-Embedding-0.6B-Q8_0.gguf"
)


def load_script() -> tuple[str, list[dict]]:
    payload = json.loads(SCRIPT.read_text(encoding="utf-8"))
    return payload["system_prompt"], payload["turns"]


class A0Arm:
    """Deployed baseline: prior committed engine, per-item cosine selection."""

    name = "L-A0"
    selection = "recency N-cap union K-threshold, per-item cosine order"

    def __init__(self, workdir: Path, system_prompt: str, embed, carried) -> None:
        from src.db.schema import init_db
        from src.db.episode import store_episode
        from src.memory.context_matched_stm import (
            ContextMatchedStmRetrievalEngine,
        )

        self._store_episode = store_episode
        self._embed = embed
        self.conn = init_db(str(workdir / "study.db"))
        self.engine = ContextMatchedStmRetrievalEngine(
            self.conn,
            n_cap=N_CAP,
            k_threshold=0.47,   # engine requires strictly below the carried 0.48
            payload_budget=BUDGET,
            embedding_provider=embed,
            system_prompt=system_prompt,
        )

    def build_prompt(self, user_message: str, turn_number: int) -> tuple[str, dict]:
        result = self.engine.retrieve(user_message, turn_number)
        meta = {
            "delivered_episodes": len(result.recent_episodes)
            + len(result.retrieved_stm_episodes),
            "k_count": result.k_count,
            "n_count": result.n_count,
            "chars_delivered": result.retrieval_payload_chars,
            "payload_sha256": result.retrieval_payload_sha256,
            "n_candidates": result.n_candidate_count,
            "k_candidates": result.k_candidate_count,
            "truncated": bool(result.skipped_n_ids or result.skipped_k_ids),
        }
        return result.constructed_prompt, meta

    def append(self, user_message: str, assistant_message: str, turn: int) -> None:
        embedding = self._embed(
            f"User: {user_message}\nAssistant: {assistant_message}"
        )
        self._store_episode(self.conn, user_message, assistant_message,
                            embedding, turn)

    def close(self) -> None:
        self.conn.close()


class A3Arm:
    """Shipping configuration: episodic's set-level coverage selector."""

    name = "L-A3"
    selection = "A3_l0.1_r0.0_k16 set-level coverage over the full store"

    def __init__(self, workdir: Path, system_prompt: str, embed, carried) -> None:
        from episodic import EpisodeStore, EpisodicConfig
        from src.memory.stm_context_builder import render_current_turn

        self._render_current_turn = render_current_turn
        self._system_prompt = system_prompt
        self.config = EpisodicConfig()
        self.store = EpisodeStore(workdir / "study.db", self.config,
                                  embedder=_EpisodicEmbedder(carried))

    def build_prompt(self, user_message: str, turn_number: int) -> tuple[str, dict]:
        block, report = self.store.context(user_message, BUDGET)
        prompt = "\n\n".join([
            self._system_prompt,
            "<pinned_rules/>",
            block,
            self._render_current_turn(user_message),
        ])
        meta = {
            "delivered_episodes": len(getattr(report, "delivered_ids", []) or []),
            "chars_delivered": getattr(report, "chars_delivered", None),
            "chars_wanted": getattr(report, "chars_wanted", None),
            "truncated": getattr(report, "truncated", None),
            "dropped": len(getattr(report, "dropped_ids", []) or []),
        }
        return prompt, meta

    def append(self, user_message: str, assistant_message: str, turn: int) -> None:
        self.store.append("user", user_message)
        self.store.append("assistant", assistant_message)

    def close(self) -> None:
        self.store.close()


class _EpisodicEmbedder:
    """Adapt the carried embedder to episodic's expected interface.

    `model_sha256` must be the real artifact hash: the store asserts it against
    the pinned value on open (hazard H1), and an adapter that reported anything
    else would defeat the gate rather than satisfy it.
    """

    def __init__(self, carried) -> None:
        self._carried = carried
        self.model_sha256 = carried.model_sha256

    def embed(self, text: str):
        return self._carried(text)

    def __call__(self, text: str):
        return self._carried(text)


def carried_embedder():
    from src.retrieval_bakeoff.embedding import CarriedEmbedder

    os.environ["CDW_EMBEDDING_MODEL_PATH"] = EMBEDDING_MODEL
    embedder = CarriedEmbedder(Path(EMBEDDING_MODEL))
    embedder.assert_carried_model()
    return embedder


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", choices=["a0", "a3"], required=True)
    parser.add_argument("--turns", type=int, default=0,
                        help="0 runs the whole script; 35 is the G6 ablation")
    args = parser.parse_args()

    os.environ.setdefault("CDW_INFERENCE_SERVER_URL", "http://127.0.0.1:8080")

    from src.inference.provider import InferenceProvider

    system_prompt, turns = load_script()
    if args.turns:
        turns = turns[: args.turns]

    label = "ablation_35" if args.turns else "full_121"
    outdir = ROOT / "runs" / label / f"l_{args.arm}"
    outdir.mkdir(parents=True, exist_ok=True)

    embedder = carried_embedder()
    embed = embedder
    arm_class = A0Arm if args.arm == "a0" else A3Arm
    arm = arm_class(outdir, system_prompt, embed, embedder)
    provider = InferenceProvider()

    turns_log = outdir / "turns.jsonl"
    responses = outdir / "responses.md"
    turns_log.write_text("", encoding="utf-8")
    responses.write_text(f"# LV-001 {arm.name} responses\n\n", encoding="utf-8")

    started = time.time()
    print(f"{arm.name}: {len(turns)} turns -> {outdir.relative_to(REPO)}")

    for index, turn in enumerate(turns, 1):
        number = int(turn.get("turn", index))
        user_message = turn.get("user") or turn.get("user_message") or ""
        prompt, meta = arm.build_prompt(user_message, number)

        began = time.time()
        result = provider.complete(f"{prompt}\n\nAssistant:")
        answer = result.assistant_message
        elapsed = time.time() - began

        arm.append(user_message, answer, number)

        record = {
            "turn_number": number,
            "arm": arm.name,
            "user_message": user_message,
            "assistant_message": answer,
            "prompt_chars": len(prompt),
            "estimated_tokens": len(prompt) // 4,
            "seconds": round(elapsed, 2),
            "tokens_per_second": result.tokens_per_second,
            "time_to_first_token": result.time_to_first_token,
            "output_tokens": result.output_tokens,
            **meta,
        }
        with turns_log.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
        with responses.open("a", encoding="utf-8") as handle:
            handle.write(f"## Turn {number}\n\n**User:** {user_message}\n\n"
                         f"**Assistant:** {answer}\n\n")

        if index % 10 == 0 or index == len(turns):
            rate = (time.time() - started) / index
            print(f"  turn {number:3d}/{len(turns)}  "
                  f"{meta.get('chars_delivered')} chars  "
                  f"{rate:.1f}s/turn  eta {(len(turns)-index)*rate/60:.0f}m")

    arm.close()
    (outdir / "run_header.json").write_text(json.dumps({
        "record": "LV-001 live validation",
        "arm": arm.name,
        "selection": arm.selection,
        "anchor": "89614a0c3799e0e96edb7809ba11eac07d39ac90",
        "turns": len(turns),
        "budget_chars": BUDGET,
        "server": os.environ["CDW_INFERENCE_SERVER_URL"],
        "embedding_model_sha256": embedder.model_sha256,
        "completions": provider.completion_count,
        "started_utc": datetime.fromtimestamp(started, timezone.utc).isoformat(),
        "elapsed_seconds": round(time.time() - started, 1),
    }, indent=2) + "\n", encoding="utf-8")

    print(f"{arm.name} complete in {(time.time()-started)/60:.1f} min")
    return 0


if __name__ == "__main__":
    sys.exit(main())
