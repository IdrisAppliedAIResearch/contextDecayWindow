"""NF-002: does marginal novelty earn its place under a budget that binds?

NF-001 asked whether a novelty floor picks a good stopping *depth*, and could
not answer: its streams were 32-35 candidates and all of them fit, so
`NEVER_STOP` was optimal and no rule could beat it. The defect was the
instrument, not the mechanism.

This module builds the instrument NF-001 lacked, and in doing so restates the
question. On LongMemEval every stream is oversubscribed - EC-002's own
episode-level candidate set by a median 2.92x, and the full session-level stream
used here by 14.5x - so the budget truncates. Under truncation the operative decision
is not *when to stop* but *what to skip*: a low-value candidate taken early
displaces a higher-value one later. So the rule under test is a filter, and the
question is whether skipping stale candidates lets more evidence fit in the same
32,000 characters.

That is adjacent to E005, which showed set-level diversity selection reaching
12/17 on the internal corpus. NF-002 asks whether the far simpler marginal-
novelty filter carries any of that to 470 real questions.

**Reproduction anchor.** Reconstructing the session order from the committed
EC-002 ranking and joining it to the dataset's `answer_session_ids` reproduces
EC-002's `evidence_session_ranks` **exactly on all 470 answerable items**. The
30 items it does not reproduce are the `_abs` abstention stratum, which EC-002
also excluded. No new number is produced before that check passes.

**Granularity.** EC-002 packs episodes; the committed ranking it publishes is
over sessions, so this packs sessions. That is a deliberate difference and it
is why the baseline here is NF-002's own rank-order arm rather than EC-002's
reported recall. This program has been caught by a silent granularity change
before, so it is stated rather than assumed.

Zero model calls. The ranking is committed and the dataset is on disk.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Sequence

SCHEMA = "nf002-streams-v1"

DATASET = Path(r"C:\Users\muzaf\datasets\longmemeval\longmemeval_s_cleaned.json")
DATASET_SHA256 = "d6f21ea9d60a0d56f34a05b609c79c88a451d2ae03597821ea3d5a9678c3a442"
EC002_RUN = Path("experiments/external/longmemeval/runs/ec002_k_first/a1_k_first")

#: The program's carried delivery control since Study 007.
BUDGET_CHARS = 32_000

_WORD = re.compile(r"[a-z0-9]+")


class StreamError(RuntimeError):
    pass


def episode_text(user: str, assistant: str) -> str:
    """The carried episode rendering, same as DMR-001C's."""
    return f"User: {user}\nAssistant: {assistant}"


def strip_position(session_id: str) -> str:
    return session_id.split("::position=")[0]


def tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


@dataclass(frozen=True)
class Candidate:
    session_id: str
    rank: int
    chars: int
    is_evidence: bool
    token_set: frozenset[str]


@dataclass(frozen=True)
class QuestionStream:
    question_id: str
    question_type: str
    candidates: tuple[Candidate, ...]
    evidence_total: int
    #: The same stream cut at episode granularity: every episode is its own
    #: candidate and inherits its session's rank. Carried alongside rather than
    #: instead of, because a granularity change is exactly what this program has
    #: been caught by before - a count-based budget silently means something
    #: different when the unit changes size.
    episodes: tuple[Candidate, ...] = ()

    @property
    def total_chars(self) -> int:
        return sum(c.chars for c in self.candidates)


def _load_committed_ranking() -> dict[str, list[str]]:
    path = EC002_RUN / "a1_mechanism.jsonl"
    if not path.is_file():
        raise StreamError(f"committed EC-002 mechanism file missing: {path}")
    ranking: dict[str, list[str]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            row = json.loads(line)
            ordered = sorted(row["session_cosine_ranking"], key=lambda e: e["rank"])
            ranking[row["question_id"]] = [strip_position(e["session_id"]) for e in ordered]
    return ranking


def _load_committed_evidence_ranks() -> dict[str, list[int]]:
    path = EC002_RUN / "a1_scores.jsonl"
    with path.open(encoding="utf-8") as handle:
        return {
            (row := json.loads(line))["question_id"]: sorted(row["evidence_session_ranks"])
            for line in handle
        }


def load_streams(dataset_path: Path | None = None) -> tuple[tuple[QuestionStream, ...], dict[str, Any]]:
    """Assemble every answerable stream, and verify the anchor while doing it."""
    ranking = _load_committed_ranking()
    committed_ranks = _load_committed_evidence_ranks()
    raw = (dataset_path or DATASET).read_bytes()
    items = json.loads(raw.decode("utf-8"))

    streams: list[QuestionStream] = []
    reproduced = mismatched = skipped_abstention = 0
    for item in items:
        question_id = item["question_id"]
        if question_id not in ranking:
            continue
        order = ranking[question_id]
        answer_ids = set(item["answer_session_ids"])
        sessions = dict(zip(item["haystack_session_ids"], item["haystack_sessions"]))

        my_ranks = sorted(i + 1 for i, sid in enumerate(order) if sid in answer_ids)
        if my_ranks != committed_ranks.get(question_id, []):
            # The `_abs` abstention stratum: EC-002 records no evidence rank for
            # these and scored 470 answerable items, so they are excluded here
            # for the same reason rather than repaired.
            skipped_abstention += 1
            mismatched += 1
            continue
        reproduced += 1

        candidates: list[Candidate] = []
        episodes: list[Candidate] = []
        for index, session_id in enumerate(order):
            turns = sessions.get(session_id)
            if turns is None:
                raise StreamError(f"{question_id}: ranked session {session_id} not in haystack")
            texts = []
            for i in range(0, len(turns) - 1, 2):
                a, b = turns[i], turns[i + 1]
                if a.get("role") == "user" and b.get("role") == "assistant":
                    texts.append(episode_text(a.get("content", ""), b.get("content", "")))
            blob = "\n".join(texts)
            is_evidence = session_id in answer_ids
            candidates.append(
                Candidate(
                    session_id=session_id,
                    rank=index + 1,
                    chars=len(blob),
                    is_evidence=is_evidence,
                    token_set=frozenset(tokens(blob)),
                )
            )
            for text in texts:
                episodes.append(
                    Candidate(
                        session_id=session_id,
                        rank=index + 1,
                        chars=len(text),
                        is_evidence=is_evidence,
                        token_set=frozenset(tokens(text)),
                    )
                )
        streams.append(
            QuestionStream(
                question_id=question_id,
                question_type=item.get("question_type", "unknown"),
                candidates=tuple(candidates),
                evidence_total=sum(1 for c in candidates if c.is_evidence),
                episodes=tuple(episodes),
            )
        )

    anchor = {
        "dataset_sha256_expected": DATASET_SHA256,
        "items_seen": len(items),
        "evidence_ranks_reproduced": reproduced,
        "excluded_abstention_stratum": skipped_abstention,
        "mismatched": mismatched,
        "anchor_holds": reproduced == 470,
    }
    if not anchor["anchor_holds"]:
        raise StreamError(
            f"reproduction anchor failed: {reproduced} items reproduced, expected 470"
        )
    return tuple(streams), anchor


# ------------------------------------------------------------------- the arms

def pack_all(stream: QuestionStream, budget: int = BUDGET_CHARS) -> tuple[int, int, int]:
    """Rank order, take everything that fits. This is the baseline.

    Returns (evidence covered, chars used, candidates taken).
    """
    used = taken = covered = 0
    for candidate in stream.candidates:
        if used + candidate.chars > budget:
            continue
        used += candidate.chars
        taken += 1
        covered += candidate.is_evidence
    return covered, used, taken


def pack_novelty_filter(
    stream: QuestionStream, floor: float, budget: int = BUDGET_CHARS
) -> tuple[int, int, int]:
    """Skip a candidate whose token novelty against what is already taken is
    below `floor`, and keep walking. Skipping frees budget for a later one.
    """
    seen: set[str] = set()
    used = taken = covered = 0
    for candidate in stream.candidates:
        if candidate.token_set:
            novelty = len(candidate.token_set - seen) / len(candidate.token_set)
        else:
            novelty = 0.0
        if taken and novelty < floor:
            continue
        if used + candidate.chars > budget:
            continue
        used += candidate.chars
        taken += 1
        covered += candidate.is_evidence
        seen |= candidate.token_set
    return covered, used, taken


def pack_oracle(stream: QuestionStream, budget: int = BUDGET_CHARS) -> tuple[int, int, int]:
    """The most evidence that fits, cheapest-evidence-first.

    Not achievable without the key. It is the ceiling the arms are scored
    against, and it is measurement only.
    """
    evidence = sorted((c for c in stream.candidates if c.is_evidence), key=lambda c: c.chars)
    used = covered = taken = 0
    for candidate in evidence:
        if used + candidate.chars > budget:
            continue
        used += candidate.chars
        taken += 1
        covered += 1
    return covered, used, taken


def pack_shortest_first(stream: QuestionStream, budget: int = BUDGET_CHARS) -> tuple[int, int, int]:
    """A key-blind control that games the budget without using relevance.

    If this beats rank order, the result is about character economics rather
    than about novelty, and the report has to say so.
    """
    used = taken = covered = 0
    for candidate in sorted(stream.candidates, key=lambda c: c.chars):
        if used + candidate.chars > budget:
            continue
        used += candidate.chars
        taken += 1
        covered += candidate.is_evidence
    return covered, used, taken


ARMS = {
    "rank_order": pack_all,
    "shortest_first": pack_shortest_first,
    "oracle": pack_oracle,
}


def iter_streams(streams: Sequence[QuestionStream]) -> Iterator[QuestionStream]:
    yield from streams


def pack_episodes(stream: QuestionStream, budget: int = BUDGET_CHARS) -> tuple[int, int, int]:
    """Rank order, episode granularity, same skip-on-overflow policy.

    The only difference from `pack_all` is the size of the unit. A session that
    does not fit is skipped whole; its episodes are small enough to fit
    individually, and one of them may be the evidence.
    """
    used = taken = 0
    covered_sessions: set[str] = set()
    for candidate in stream.episodes:
        if used + candidate.chars > budget:
            continue
        used += candidate.chars
        taken += 1
        if candidate.is_evidence:
            covered_sessions.add(candidate.session_id)
    return len(covered_sessions), used, taken


def build_part1_record(dataset_path: Path | None = None) -> dict[str, Any]:
    streams, anchor = load_streams(dataset_path)
    n = len(streams)

    def summarize(fn, **kwargs) -> dict[str, Any]:
        any_hit = all_hit = 0
        used: list[int] = []
        for stream in streams:
            covered, chars, _taken = fn(stream, **kwargs)
            any_hit += covered >= 1
            all_hit += covered >= stream.evidence_total
            used.append(chars)
        used.sort()
        return {
            "any_evidence": any_hit,
            "any_evidence_rate": any_hit / n,
            "all_evidence": all_hit,
            "all_evidence_rate": all_hit / n,
            "median_chars_used": used[n // 2],
        }

    arms = {
        "rank_order_sessions": summarize(pack_all),
        "rank_order_episodes": summarize(pack_episodes),
        "shortest_first": summarize(pack_shortest_first),
        "oracle_ceiling": summarize(pack_oracle),
    }
    for floor in (0.05, 0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70):
        arms[f"novelty_floor_{floor:.2f}"] = summarize(pack_novelty_filter, floor=floor)

    # Paired gains and losses for the granularity change, which is what a
    # no-regression bar has to be set against. TA-001 and SR-001 both died on
    # losses, not on net.
    gains = losses = 0
    for stream in streams:
        session_hit = pack_all(stream)[0] >= 1
        episode_hit = pack_episodes(stream)[0] >= 1
        gains += episode_hit and not session_hit
        losses += session_hit and not episode_hit

    # Where the misses actually are.
    deep = cost = 0
    for stream in streams:
        if pack_all(stream)[0]:
            continue
        used = 0
        deepest = 0
        for candidate in stream.candidates:
            if used + candidate.chars <= budget_guard():
                used += candidate.chars
                deepest = max(deepest, candidate.rank)
        best_evidence_rank = min(c.rank for c in stream.candidates if c.is_evidence)
        if best_evidence_rank > deepest:
            deep += 1
        else:
            cost += 1

    lengths = sorted(len(s.candidates) for s in streams)
    totals = sorted(s.total_chars for s in streams)
    return {
        "schema": SCHEMA,
        "anchor": anchor,
        "budget_chars": BUDGET_CHARS,
        "streams": n,
        "candidates_per_stream": {
            "min": lengths[0],
            "median": lengths[n // 2],
            "max": lengths[-1],
        },
        "oversubscription_median": totals[n // 2] / BUDGET_CHARS,
        "arms": arms,
        "granularity_paired": {"gains": gains, "losses": losses, "net": gains - losses},
        "miss_diagnosis": {
            "ranked_deeper_than_anything_that_fit": deep,
            "within_reach_but_skipped_on_cost": cost,
        },
    }


def budget_guard() -> int:
    return BUDGET_CHARS


def write_part1_record(repository_root: Path, dataset_path: Path | None = None) -> Path:
    record = build_part1_record(dataset_path)
    path = repository_root / "experiments/components/biological_memory/nf_002/artifacts/part1_record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
