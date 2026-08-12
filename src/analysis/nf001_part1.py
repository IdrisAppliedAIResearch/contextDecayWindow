"""NF-001 Part 1: is there a query-blind stopping signal in the retrieval stream?

DMR-004 asked whether query text fixes the evidence obligation. It does not,
for two thirds of real queries, and closing the gap meant enumerating question
formats. This diagnostic asks the other half of `HYPOTHETICAL_001` §6.2 -
whether a step that produces no new evidence is a usable stop - by reading the
retrieval stream instead of the query.

The mechanism side of this module sees candidate identities, their order, and
their text. It never sees a fact key. Fact keys enter only through
`fact_curve`, which is measurement, and the separation is structural: the
novelty functions take episode text and return floats, with no argument that
could carry a label.

The failure this is most likely to have is stated in the spec and measured
first: a novelty floor stops early wherever a stream repeats itself, and one of
this program's corpora is 84% duplicates. `duplicate_report` runs before
anything else for that reason.
"""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Sequence

RECORD_SCHEMA = "nf001-part1-v1"

#: The store IC-001's frozen candidate identities resolve against. Verified by
#: joining all 34 considered ids for probe 120, not by trusting the path.
STORE = (
    "experiments/surveys/retrieval_bakeoff/tier6/runs/"
    "tier6_live_121_corrected_001/context_matched_stm/study.db"
)
ARMS = {
    "B0_deployed": "experiments/internal/packing_priority/runs/ic001/b0_recency_first/b0_arm.json",
    "B1_k_first": "experiments/internal/packing_priority/runs/ic001/b1_k_first/b1_arm.json",
}

_WORD = re.compile(r"[a-z0-9]+")


class StreamError(RuntimeError):
    pass


@dataclass(frozen=True)
class Stream:
    """One question's ordered candidate stream, with its measurement key."""

    arm: str
    probe_turn: int
    question: str
    episode_ids: tuple[str, ...]
    texts: tuple[str, ...]
    items: tuple[str, ...]

    def __len__(self) -> int:
        return len(self.episode_ids)


def load_store(repository_root: Path) -> dict[str, str]:
    path = repository_root / STORE
    if not path.is_file():
        raise StreamError(f"store missing: {path}")
    connection = sqlite3.connect(f"file:{path.as_posix()}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "select id, user_message, assistant_message from episodes"
        ).fetchall()
    finally:
        connection.close()
    return {row[0]: f"{row[1] or ''}\n{row[2] or ''}" for row in rows}


def load_streams(repository_root: Path) -> tuple[Stream, ...]:
    store = load_store(repository_root)
    streams: list[Stream] = []
    for arm, relative in ARMS.items():
        payload = json.loads((repository_root / relative).read_text(encoding="utf-8"))
        targeted_by_turn = {
            int(block["turn"]): (name, tuple(entry["item"] for entry in block["items"]))
            for name, block in payload["targeted"].items()
        }
        q11_turn = int(payload["q11"]["probe_turn"])
        q11_items = tuple(entry["item"] for entry in payload["q11"]["items"])

        for turn_key, probe in payload["probes"].items():
            turn = int(turn_key)
            ordered = tuple(probe["considered_ids"])
            missing = [i for i in ordered if i not in store]
            if missing:
                raise StreamError(f"{arm} turn {turn}: {len(missing)} ids not in the store")
            if turn == q11_turn:
                question, items = "Q11", q11_items
            elif turn in targeted_by_turn:
                question, items = targeted_by_turn[turn]
            else:
                continue
            streams.append(
                Stream(
                    arm=arm,
                    probe_turn=turn,
                    question=question,
                    episode_ids=ordered,
                    texts=tuple(store[i] for i in ordered),
                    items=items,
                )
            )
    if not streams:
        raise StreamError("no streams assembled")
    return tuple(streams)


# ------------------------------------------------------------------ measurement

def fact_curve(stream: Stream) -> tuple[int, ...]:
    """Cumulative distinct items present in the first k candidates.

    Substring matching, lowercased. This reproduces IC-001's committed
    `fact_count` exactly on its selected payload, which is the reproduction
    anchor PF6 asks for; it is not a new scoring rule invented here.
    """
    curve: list[int] = []
    blob = ""
    found: set[str] = set()
    for text in stream.texts:
        blob += "\n" + text.lower()
        for item in stream.items:
            if item.lower() in blob:
                found.add(item)
        curve.append(len(found))
    return tuple(curve)


def oracle_depth(curve: Sequence[int]) -> int:
    """The shallowest depth reaching the stream's maximum fact count."""
    if not curve:
        return 0
    best = max(curve)
    return curve.index(best) + 1


# --------------------------------------------------------------- novelty units

def tokens(text: str) -> set[str]:
    return set(_WORD.findall(text.lower()))


def char_ngrams(text: str, n: int = 5) -> set[str]:
    squeezed = re.sub(r"\s+", " ", text.lower())
    return {squeezed[i : i + n] for i in range(max(0, len(squeezed) - n + 1))}


def novelty_token_gain(seen: set[str], text: str) -> float:
    """Share of this candidate's tokens not already seen."""
    current = tokens(text)
    if not current:
        return 0.0
    return len(current - seen) / len(current)


def novelty_char_containment(seen: set[str], text: str) -> float:
    current = char_ngrams(text)
    if not current:
        return 0.0
    return len(current - seen) / len(current)


def novelty_token_jaccard(seen: set[str], text: str) -> float:
    """1 - Jaccard against everything seen so far."""
    current = tokens(text)
    if not current or not seen:
        return 1.0 if current else 0.0
    union = len(current | seen)
    return 1.0 - (len(current & seen) / union) if union else 0.0


UNITS: dict[str, tuple[Callable[[str], set[str]], Callable[[set[str], str], float]]] = {
    "token_gain": (tokens, novelty_token_gain),
    "char5_gain": (lambda t: char_ngrams(t), novelty_char_containment),
    "token_jaccard": (tokens, novelty_token_jaccard),
}


def novelty_curve(stream: Stream, unit: str) -> tuple[float, ...]:
    accumulate, score = UNITS[unit]
    seen: set[str] = set()
    out: list[float] = []
    for text in stream.texts:
        out.append(score(seen, text))
        seen |= accumulate(text)
    return tuple(out)


# --------------------------------------------------------------- the stop rule

def novelty_floor_stop(novelty: Sequence[float], floor: float, window: int) -> int:
    """First depth after `window` consecutive candidates below `floor`.

    Returns the number of candidates taken. Never stops before `window`, and
    never returns 0 - a stopping rule that delivers nothing is not a stopping
    rule.
    """
    run = 0
    for index, value in enumerate(novelty, start=1):
        run = run + 1 if value < floor else 0
        if run >= window:
            return max(1, index)
    return len(novelty)


# ------------------------------------------------------------------- reporting

def duplicate_report(streams: Sequence[Stream]) -> dict[str, Any]:
    """The spec's §5 risk, measured before anything else.

    A novelty floor looks brilliant on a stream that repeats itself, for reasons
    that have nothing to do with sufficiency. This measures repetition inside
    each stream rather than in the corpus.
    """
    rows = []
    for stream in streams:
        texts = list(stream.texts)
        exact = len(texts) - len(set(texts))
        near = 0
        seen_tokens: list[set[str]] = []
        for text in texts:
            current = tokens(text)
            if any(
                current and previous and len(current & previous) / len(current | previous) >= 0.9
                for previous in seen_tokens
            ):
                near += 1
            seen_tokens.append(current)
        rows.append(
            {
                "arm": stream.arm,
                "question": stream.question,
                "depth": len(stream),
                "exact_duplicates": exact,
                "exact_duplicate_rate": exact / len(stream) if len(stream) else None,
                "near_duplicates_j90": near,
                "near_duplicate_rate": near / len(stream) if len(stream) else None,
            }
        )
    rates = [row["exact_duplicate_rate"] for row in rows if row["exact_duplicate_rate"] is not None]
    return {
        "rows": rows,
        "max_exact_duplicate_rate": max(rates) if rates else None,
        "streams_with_any_exact_duplicate": sum(1 for r in rows if r["exact_duplicates"]),
    }


def unit_tracking_report(streams: Sequence[Stream]) -> dict[str, Any]:
    """Does a novelty unit track marginal fact gain, or is it measuring length?

    The spec requires this be measured rather than assumed: this program has
    confused ranking units with delivery units before.
    """
    out: dict[str, Any] = {}
    for unit in UNITS:
        agree = disagree = 0
        gains_when_novel = []
        gains_when_stale = []
        for stream in streams:
            curve = fact_curve(stream)
            novelty = novelty_curve(stream, unit)
            marginal = [curve[0]] + [curve[i] - curve[i - 1] for i in range(1, len(curve))]
            if not marginal:
                continue
            median_novelty = sorted(novelty)[len(novelty) // 2]
            for gain, value in zip(marginal, novelty):
                if value >= median_novelty:
                    gains_when_novel.append(gain)
                else:
                    gains_when_stale.append(gain)
                if (gain > 0) == (value >= median_novelty):
                    agree += 1
                else:
                    disagree += 1
        total = agree + disagree
        out[unit] = {
            "sign_agreement": agree / total if total else None,
            "mean_fact_gain_when_novel": (
                sum(gains_when_novel) / len(gains_when_novel) if gains_when_novel else None
            ),
            "mean_fact_gain_when_stale": (
                sum(gains_when_stale) / len(gains_when_stale) if gains_when_stale else None
            ),
        }
    return out


def _percentile(ordered: Sequence[float], fraction: float) -> float:
    if not ordered:
        return float("nan")
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def stop_grid_report(
    streams: Sequence[Stream],
    floors: Sequence[float] = (0.05, 0.10, 0.20, 0.30, 0.40, 0.50),
    windows: Sequence[int] = (1, 2, 3),
) -> dict[str, Any]:
    """Regret against the oracle stopping depth, plus stopping-depth swing.

    Regret is negative-or-zero: facts at the rule's depth minus facts at the
    depth that maximizes them. Swing is p95:p05 of the chosen depth across
    questions - a rule that picks one depth everywhere is fixed depth in a
    costume, which is the check that worked in DMR-001B and DMR-001C.
    """
    per_stream = []
    for stream in streams:
        curve = fact_curve(stream)
        per_stream.append((stream, curve, oracle_depth(curve), max(curve) if curve else 0))

    rows = []
    for unit in UNITS:
        novelty_by_stream = {
            (s.arm, s.question): novelty_curve(s, unit) for s, _, _, _ in per_stream
        }
        for floor in floors:
            for window in windows:
                regrets, depths = [], []
                for stream, curve, o_depth, o_best in per_stream:
                    novelty = novelty_by_stream[(stream.arm, stream.question)]
                    depth = novelty_floor_stop(novelty, floor, window)
                    regrets.append(curve[depth - 1] - o_best)
                    depths.append(depth)
                ordered_depths = sorted(depths)
                low = _percentile(ordered_depths, 0.05)
                high = _percentile(ordered_depths, 0.95)
                rows.append(
                    {
                        "unit": unit,
                        "floor": floor,
                        "window": window,
                        "median_regret": sorted(regrets)[len(regrets) // 2],
                        "mean_regret": sum(regrets) / len(regrets),
                        "worst_regret": min(regrets),
                        "median_depth": sorted(depths)[len(depths) // 2],
                        "depth_swing_p95_p05": (high / low) if low else None,
                    }
                )
    return {"floors": list(floors), "windows": list(windows), "rows": rows}


def control_report(streams: Sequence[Stream], depths: Sequence[int] = (1, 3, 5, 8, 10, 15, 20, 30)) -> dict[str, Any]:
    """Fixed depth, oracle, and both degenerate arms - all computed."""
    per_stream = [(s, fact_curve(s)) for s in streams]
    rows = []
    for k in depths:
        regrets, taken = [], []
        for stream, curve in per_stream:
            if not curve:
                continue
            depth = min(k, len(curve))
            regrets.append(curve[depth - 1] - max(curve))
            taken.append(depth)
        rows.append(
            {
                "arm": f"FIXED_{k}",
                "median_regret": sorted(regrets)[len(regrets) // 2],
                "mean_regret": sum(regrets) / len(regrets),
                "worst_regret": min(regrets),
                "median_depth": sorted(taken)[len(taken) // 2],
                "depth_swing_p95_p05": 1.0,
            }
        )
    oracle_depths = sorted(oracle_depth(curve) for _, curve in per_stream)
    rows.append(
        {
            "arm": "ORACLE",
            "median_regret": 0,
            "mean_regret": 0.0,
            "worst_regret": 0,
            "median_depth": oracle_depths[len(oracle_depths) // 2],
            "depth_swing_p95_p05": (
                _percentile(oracle_depths, 0.95) / _percentile(oracle_depths, 0.05)
                if _percentile(oracle_depths, 0.05)
                else None
            ),
        }
    )
    for name, depth_fn in (("STOP_AT_1", lambda c: 1), ("NEVER_STOP", len)):
        regrets, taken = [], []
        for _stream, curve in per_stream:
            if not curve:
                continue
            depth = depth_fn(curve)
            regrets.append(curve[depth - 1] - max(curve))
            taken.append(depth)
        rows.append(
            {
                "arm": name,
                "median_regret": sorted(regrets)[len(regrets) // 2],
                "mean_regret": sum(regrets) / len(regrets),
                "worst_regret": min(regrets),
                "median_depth": sorted(taken)[len(taken) // 2],
                "depth_swing_p95_p05": None,
            }
        )
    return {"rows": rows}


def build_part1_record(repository_root: Path) -> dict[str, Any]:
    streams = load_streams(repository_root)
    per_stream = []
    for stream in streams:
        curve = fact_curve(stream)
        per_stream.append(
            {
                "arm": stream.arm,
                "question": stream.question,
                "probe_turn": stream.probe_turn,
                "depth": len(stream),
                "items": len(stream.items),
                "max_facts": max(curve) if curve else 0,
                "oracle_depth": oracle_depth(curve),
                "fact_curve": list(curve),
            }
        )
    return {
        "schema": RECORD_SCHEMA,
        "store": STORE,
        "arms": ARMS,
        "streams": len(streams),
        "per_stream": per_stream,
        "duplicates": duplicate_report(streams),
        "unit_tracking": unit_tracking_report(streams),
        "controls": control_report(streams),
        "stop_grid": stop_grid_report(streams),
    }


def write_part1_record(repository_root: Path) -> Path:
    record = build_part1_record(repository_root)
    path = repository_root / "experiments/components/biological_memory/nf_001/artifacts/part1_record.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return path
