"""Study 007 retrieval replay — offline evaluation over Study 006's store.

Study 006 preserved its distilled store (200 records, known contents and
topics), its probe-turn retrieval logs, and its constructed prompts. The Study
007 retrieval policy is therefore evaluable against the exact store and the
exact queries that failed, before any run is spent.

**Read-only.** The Study 006 database is opened with `mode=ro`; every artifact
under the run directory is SHA-256 hashed before and after and compared.

The harness is faithful to the runner in the ways that decide selection:

  * candidates are built by `get_distilled_retrieval_rows`, the same query the
    runner uses, so `id` resolves to the source episode and `user_message` /
    `assistant_message` carry the text the renderer emits;
  * queries are embedded by the same provider;
  * the STM block at each probe turn is reconstructed from `retrieval.jsonl`, so
    containment dedup sees what it saw live.
"""

import hashlib
import json
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from src.embeddings.provider import embed, cosine_similarity
from src.memory.arbitration import arbitrate_budgeted
from src.memory.distilled_ltm_store import get_distilled_retrieval_rows
from src.memory.retrieval_budget import (
    BudgetSelection,
    select_top_m,
    topic_key,
)


STUDY_006_RUN = Path(
    "experiments/study_006/runs/study_006_full_001/condition_c"
)

PROBE_TURNS = (120, 121)

# Planted terms by domain, from `experiments/study_007/q_facts_key.md`.
# Coverage is checked against the rendered block, which carries whole source
# episodes; the key records that this is the more permissive of its two
# matching contexts.
DOMAIN_TERMS: dict[str, list[str]] = {
    "civil": ["Halcyon Crossing", "847", "S460ML", "Anara Bekova", "92.4"],
    "art": [
        "Annunciation", "Melozzo", "della Rovere", "1483",
        "ultramarine", "Julius II",
    ],
    "monetary": [
        "Taylor Rule", "Federal Reserve", "dual mandate", "Priya Mehta",
        "reverse repurchase", "2.3%",
    ],
    "marine": [
        "Vampyroteuthis", "Kenji Watanabe", "photophore", "marine snow",
        "mantle margin",
    ],
}


@dataclass
class ProbeResult:
    turn: int
    query: str
    selection: BudgetSelection
    domains_covered: list[str] = field(default_factory=list)
    terms_found: dict[str, list[str]] = field(default_factory=dict)
    block_chars: int = 0
    containment_drops: int = 0
    topics_in_block: list[str] = field(default_factory=list)

    @property
    def four_domain(self) -> bool:
        return len(self.domains_covered) == 4


def hash_tree(root: Path) -> dict[str, str]:
    """SHA-256 every file under `root`, for the read-only guarantee."""
    digests = {}
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digests[str(path.relative_to(root))] = hashlib.sha256(
                path.read_bytes()
            ).hexdigest()
    return digests


def load_candidates(run_dir: Path = STUDY_006_RUN) -> list[dict]:
    """Read the preserved distilled store through the runner's own query."""
    db_path = run_dir / "study.db"
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    try:
        return get_distilled_retrieval_rows(conn)
    finally:
        conn.close()


def stm_block_ids(turn: int, run_dir: Path = STUDY_006_RUN) -> set[str]:
    """Episodes in the STM block at `turn`, as the live run assembled it."""
    path = run_dir / "logs" / "retrieval.jsonl"
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row.get("turn_number") != turn:
            continue
        return {
            str(episode["id"])
            for key in ("n_episodes", "k_episodes")
            for episode in row.get(key, [])
        }
    return set()


def probe_queries(
    script_path: str = "experiments/study_005/script.json",
) -> dict[int, str]:
    script = json.loads(Path(script_path).read_text(encoding="utf-8"))
    return {
        turn["turn"]: turn["user"]
        for turn in script["turns"]
        if turn["turn"] in PROBE_TURNS
    }


def score(candidates: list[dict], query: str) -> list[dict]:
    """Attach cosine similarity to every candidate — no truncation."""
    query_embedding = embed(query)
    scored = []
    for candidate in candidates:
        import numpy as np

        embedding = np.frombuffer(candidate["embedding"], dtype="float32")
        scored.append({
            **candidate,
            "similarity": cosine_similarity(query_embedding, embedding),
        })
    return scored


def render_block_text(selected: list[dict]) -> str:
    return "\n".join(
        f"{c.get('user_message') or ''}\n{c.get('assistant_message') or ''}"
        for c in selected
    )


def evaluate_coverage(selected: list[dict]) -> tuple[list[str], dict]:
    """Which domains are represented in the rendered block, and by what."""
    text = render_block_text(selected)
    found = {
        domain: [term for term in terms if term.lower() in text.lower()]
        for domain, terms in DOMAIN_TERMS.items()
    }
    covered = [domain for domain, hits in found.items() if hits]
    return covered, found


def replay_probe(
    turn: int,
    query: str,
    candidates: list[dict],
    b_ltm: int,
    k_min: int,
    apply_containment: bool = True,
    run_dir: Path = STUDY_006_RUN,
) -> ProbeResult:
    scored = score(candidates, query)
    excluded = stm_block_ids(turn, run_dir) if apply_containment else set()
    arbitration = arbitrate_budgeted(
        stm_candidates=[],
        ltm_candidates=scored,
        stm_block_episode_ids=excluded,
        ltm_budget=b_ltm,
        ltm_k_min=k_min,
    )
    selection = arbitration.budget
    covered, found = evaluate_coverage(selection.selected)
    return ProbeResult(
        turn=turn,
        query=query,
        selection=selection,
        domains_covered=covered,
        terms_found=found,
        block_chars=selection.chars_used,
        containment_drops=arbitration.containment_drops,
        topics_in_block=sorted(
            {topic_key(c) for c in selection.selected}
        ),
    )


def replay_probe_top_m(
    turn: int,
    query: str,
    candidates: list[dict],
    top_m: int = 5,
) -> ProbeResult:
    """Study 006's policy, for the harness fidelity check."""
    scored = score(candidates, query)
    selection = select_top_m(scored, top_m=top_m)
    covered, found = evaluate_coverage(selection.selected)
    return ProbeResult(
        turn=turn,
        query=query,
        selection=selection,
        domains_covered=covered,
        terms_found=found,
        block_chars=selection.chars_used,
        topics_in_block=sorted({topic_key(c) for c in selection.selected}),
    )
