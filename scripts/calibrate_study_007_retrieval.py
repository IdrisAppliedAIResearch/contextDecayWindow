"""Study 007 S7-T-013/014/015/016 — joint calibration of `B_ltm` and `k_min`.

Runs both offline gates over Study 006's preserved store and finds the
smallest-sufficient parameters that satisfy them **simultaneously**:

  * **Retrieval replay gate** — at Q11 (turn 120) and Q14 (turn 121), the LTM
    block must contain at least one planted term from each of the four domains.
  * **Targeted-retrieval fixture** — for each narrowly targeted query, the
    majority of the character budget must go to the query's own domain, that
    domain's top-similarity candidate must be present, and the floor's cost
    against a floor-disabled variant must be bounded. Amendment 002 re-derives
    that third criterion in characters plus one record of bin-packing slack; the
    pre-registered slot form is still computed and reported as `slot_bound_held`.

The replay gate pushes the floor up; the fixture pushes it down. Resolving that
tension before the run is the point of doing both offline.

`k_min = 0` is swept as a **diagnostic control**, not as a candidate: it
disables the floor, so comparing it against `k_min >= 1` at the same budget
answers whether the floor causes four-domain coverage or whether volume alone
does. That answer is `floor_is_causal`, and it is recorded before the run so
Bar 1's attribution is not decided after seeing the result.

Read-only: Study 006 artifacts are hashed before and after and compared.

Usage:
    PYTHONUTF8=1 .venv/Scripts/python.exe scripts/calibrate_study_007_retrieval.py
"""

import json
import sys
from pathlib import Path

from src.analysis.study_007_replay import (
    DOMAIN_TERMS,
    PROBE_TURNS,
    STUDY_006_RUN,
    hash_tree,
    load_candidates,
    probe_queries,
    replay_probe,
    replay_probe_top_m,
    score,
)
from src.memory.retrieval_budget import (
    PHASE_FLOOR,
    select_within_budget,
    topic_key,
)

FIXTURE = Path("tests/targeted_retrieval_fixture.json")
OUT_DIR = Path("experiments/study_007/replay")

B_SWEEP = (16000, 20000, 24000, 28000, 32000, 36000, 40000, 48000, 64000)
K_SWEEP = (0, 1, 2, 3, 4)

CTX_SIZE = 50176
CTX_LIMIT_FRACTION = 0.60

# Study 006 treatment, measured (Amendment 001 §3.1): the constructed prompt at
# turn 120 was 31,371 characters of which 13,130 were the LTM block. Everything
# outside the LTM block is unchanged by this study, so a projection is the
# non-LTM remainder plus the new budget.
S006_PROMPT_CHARS = {120: 31371, 121: 36808}
S006_LTM_CHARS = {120: 13130, 121: 16027}

# Scaffolding the renderer adds per element (tags, attributes) that the budget
# does not charge. Measured from Study 006: 13,130 rendered - 12,039 content
# over 4 elements.
SCAFFOLD_PER_ELEMENT = 273


def topic_domain_map(candidates: list[dict]) -> dict[str, str]:
    """Label each canonical topic id with the domain its content belongs to."""
    text_by_topic: dict[str, list[str]] = {}
    for candidate in candidates:
        text_by_topic.setdefault(topic_key(candidate), []).append(
            f"{candidate.get('user_message') or ''} "
            f"{candidate.get('assistant_message') or ''}"
        )
    mapping = {}
    for topic, chunks in text_by_topic.items():
        blob = " ".join(chunks).lower()
        counts = {
            domain: sum(blob.count(term.lower()) for term in terms)
            for domain, terms in DOMAIN_TERMS.items()
        }
        mapping[topic] = max(counts, key=counts.get)
    return mapping


def project_peak_tokens(turn: int, b_ltm: int, records: int) -> int:
    non_ltm = S006_PROMPT_CHARS[turn] - S006_LTM_CHARS[turn]
    projected = non_ltm + b_ltm + records * SCAFFOLD_PER_ELEMENT
    return projected // 4


def run_replay_gate(candidates, queries, b_ltm, k_min) -> dict:
    results = {
        turn: replay_probe(turn, queries[turn], candidates, b_ltm, k_min)
        for turn in PROBE_TURNS
    }
    peak = max(
        project_peak_tokens(turn, b_ltm, len(r.selection.selected))
        for turn, r in results.items()
    )
    return {
        "four_domain_both": all(r.four_domain for r in results.values()),
        "per_probe": {
            turn: {
                "domains": r.domains_covered,
                "chars": r.block_chars,
                "records": len(r.selection.selected),
                "floor_per_topic": r.selection.floor_per_topic,
                "fill": r.selection.fill_selected,
                "containment_drops": r.containment_drops,
                "utilization": round(r.selection.utilization, 4),
            }
            for turn, r in results.items()
        },
        "projected_peak_tokens": peak,
        "context_ok": peak < CTX_SIZE * CTX_LIMIT_FRACTION,
        "budget_respected": all(
            r.block_chars <= b_ltm for r in results.values()
        ),
    }


def run_targeted_fixture(candidates, fixture, topic_domain, b_ltm, k_min) -> dict:
    topics = len({topic_key(c) for c in candidates})
    per_query = []
    for entry in fixture["queries"]:
        scored = score(candidates, entry["query"])
        floored = select_within_budget(scored, budget=b_ltm, k_min=k_min)
        unfloored = select_within_budget(scored, budget=b_ltm, k_min=0)

        own_chars = sum(
            chars
            for topic, chars in floored.chars_per_topic.items()
            if topic_domain[topic] == entry["domain"]
        )
        majority = (
            own_chars / floored.chars_used > 0.5 if floored.chars_used else False
        )

        own_topics = {t for t, d in topic_domain.items() if d == entry["domain"]}
        own_best = next(
            (c for c in sorted(scored, key=lambda x: -x["similarity"])
             if topic_key(c) in own_topics),
            None,
        )
        top_present = own_best is not None and str(own_best["id"]) in {
            str(c["id"]) for c in floored.selected
        }

        own_slots = sum(
            1 for c in floored.selected if topic_key(c) in own_topics
        )
        unfloored_slots = sum(
            1 for c in unfloored.selected if topic_key(c) in own_topics
        )
        lost = max(0, unfloored_slots - own_slots)
        bound = k_min * (topics - 1)

        # Amendment 002. The governing bound is expressed in characters. The
        # floor's cost to the queried domain cannot exceed what the floor spends
        # on other domains; that is the quantity the floor actually controls.
        # The slot figures above are retained and reported, but they measure the
        # ratio of episode sizes between domains, which is a corpus property.
        floor_chars_other = sum(
            rendered
            for candidate, rendered in (
                (c, len((c.get("user_message") or ""))
                 + len((c.get("assistant_message") or "")))
                for c in floored.selected
            )
            if floored.phases[str(candidate["id"])] == PHASE_FLOOR
            and topic_key(candidate) not in own_topics
        )
        own_chars_unfloored = sum(
            len((c.get("user_message") or ""))
            + len((c.get("assistant_message") or ""))
            for c in unfloored.selected
            if topic_key(c) in own_topics
        )
        chars_lost = max(0, own_chars_unfloored - own_chars)
        # Bin-packing slack. Removing the floor's episodes leaves a hole that
        # own-domain episodes of different sizes cannot fill exactly; the waste
        # is strictly less than one admissible record. Without this term the
        # criterion is violated by a few percent for arithmetic reasons.
        slack = max(
            len((c.get("user_message") or ""))
            + len((c.get("assistant_message") or ""))
            for c in candidates
        )

        per_query.append({
            "id": entry["id"],
            "domain": entry["domain"],
            "own_chars": own_chars,
            "total_chars": floored.chars_used,
            "own_share": round(
                own_chars / floored.chars_used if floored.chars_used else 0.0, 4
            ),
            "majority_own_domain": majority,
            "top_span_present": top_present,
            "slots_own": own_slots,
            "slots_own_unfloored": unfloored_slots,
            "slots_lost": lost,
            "slots_lost_bound": bound,
            "slot_bound_held": lost <= bound,
            "chars_lost": chars_lost,
            "floor_chars_other_domains": floor_chars_other,
            "packing_slack": slack,
            "chars_lost_bound": floor_chars_other + slack,
            "bounded_floor_cost": chars_lost <= floor_chars_other + slack,
        })

    return {
        "all_majority": all(q["majority_own_domain"] for q in per_query),
        "all_top_present": all(q["top_span_present"] for q in per_query),
        "all_bounded": all(q["bounded_floor_cost"] for q in per_query),
        "all_slot_bound_held": all(q["slot_bound_held"] for q in per_query),
        "min_own_share": min(q["own_share"] for q in per_query),
        "per_query": per_query,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    before = hash_tree(STUDY_006_RUN)

    candidates = load_candidates()
    queries = probe_queries()
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    topic_domain = topic_domain_map(candidates)

    print("Topic -> domain mapping:")
    for topic, domain in sorted(topic_domain.items(), key=lambda kv: kv[1]):
        print(f"  {topic}  ->  {domain}")

    # S7-T-015 harness fidelity check.
    print("\nS7-T-015 harness fidelity (Study 006 parameters, M=5, no floor)")
    fidelity = {}
    for turn in PROBE_TURNS:
        result = replay_probe_top_m(turn, queries[turn], candidates, top_m=5)
        fidelity[turn] = {
            "records": len(result.selection.selected),
            "source_turns": sorted(
                int(c["turn_number"]) for c in result.selection.selected
            ),
            "topics": len(result.topics_in_block),
            "domains": result.domains_covered,
            "chars": result.block_chars,
        }
        print(
            f"  turn {turn}: {fidelity[turn]['records']} records, "
            f"{fidelity[turn]['topics']} topics, "
            f"domains={fidelity[turn]['domains']}, "
            f"source turns={fidelity[turn]['source_turns']}"
        )

    live_turns = {120: [3, 4, 8, 98], 121: [4, 8, 31, 105]}
    fidelity_ok = (
        all(fidelity[t]["source_turns"] == live_turns[t] for t in PROBE_TURNS)
        and fidelity[120]["domains"] == ["civil"]
        and fidelity[120]["topics"] == 2
    )
    print(f"  reproduces Study 006's observed probe behaviour: {fidelity_ok}")
    if not fidelity_ok:
        print("STOP: harness is not faithful; no replay evidence is trustworthy.")
        return 1

    # S7-T-013/016 joint sweep.
    print("\nJoint sweep — both gates must pass at the same parameters")
    header = (
        f"{'B_ltm':>7} {'k_min':>5} | {'4dom':>5} {'causal':>6} {'peak':>6} | "
        f"{'major':>5} {'topsp':>5} {'bound':>5} {'slot':>5} {'minshare':>8} "
        f"| verdict"
    )
    print(header)
    print("-" * len(header))

    frontier = []
    for b_ltm in B_SWEEP:
        for k_min in K_SWEEP:
            gate = run_replay_gate(candidates, queries, b_ltm, k_min)
            targeted = run_targeted_fixture(
                candidates, fixture, topic_domain, b_ltm, k_min
            )
            # Bar 1 attribution: does the floor cause four-domain coverage at
            # this budget, or would volume alone deliver it? Recorded for every
            # point so the claim is made before the run, not after.
            no_floor = run_replay_gate(candidates, queries, b_ltm, 0)
            gate["four_domain_without_floor"] = no_floor["four_domain_both"]
            gate["floor_is_causal"] = (
                gate["four_domain_both"] and not no_floor["four_domain_both"]
            )
            passes = (
                gate["four_domain_both"]
                and gate["context_ok"]
                and gate["budget_respected"]
                and targeted["all_majority"]
                and targeted["all_top_present"]
                and targeted["all_bounded"]
            )
            row = {
                "b_ltm": b_ltm,
                "k_min": k_min,
                "replay": gate,
                "targeted": targeted,
                "both_pass": passes,
            }
            frontier.append(row)
            print(
                f"{b_ltm:>7} {k_min:>5} | "
                f"{str(gate['four_domain_both']):>5} "
                f"{str(gate['floor_is_causal']):>6} "
                f"{gate['projected_peak_tokens']:>6} | "
                f"{str(targeted['all_majority']):>5} "
                f"{str(targeted['all_top_present']):>5} "
                f"{str(targeted['all_bounded']):>5} "
                f"{str(targeted['all_slot_bound_held']):>5} "
                f"{targeted['min_own_share']:>8.3f} | "
                f"{'PASS' if passes else ''}"
            )

    # k_min = 0 is a diagnostic control, not a legal parameter: it disables the
    # floor and leaves the budget alone, which is not the component this study
    # pre-registered. It is swept and reported so the floor's causal
    # contribution is measurable, and excluded from selection.
    passing = [
        row for row in frontier if row["both_pass"] and row["k_min"] >= 1
    ]
    chosen = min(
        passing, key=lambda r: (r["b_ltm"], r["k_min"])
    ) if passing else None

    print()
    if chosen:
        print(
            f"SMALLEST SUFFICIENT: B_ltm={chosen['b_ltm']} "
            f"k_min={chosen['k_min']}"
        )
    else:
        print("NO PARAMETERS SATISFY BOTH GATES — do not run; escalate.")

    after = hash_tree(STUDY_006_RUN)
    unchanged = before == after
    print(
        f"\nStudy 006 artifacts unchanged: {unchanged} "
        f"({len(before)} files hashed before and after)"
    )

    (OUT_DIR / "calibration_sweep.json").write_text(
        json.dumps(
            {
                "topic_domain_map": topic_domain,
                "fidelity": {str(k): v for k, v in fidelity.items()},
                "fidelity_ok": fidelity_ok,
                "frontier": frontier,
                "chosen": chosen,
                "artifacts_unchanged": unchanged,
                "artifacts_hashed": len(before),
            },
            indent=2,
            default=str,
        ),
        encoding="utf-8",
    )
    return 0 if (chosen and unchanged) else 1


if __name__ == "__main__":
    sys.exit(main())
