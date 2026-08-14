"""Post-seal availability measurement for NF-006."""

from __future__ import annotations

import json
import unicodedata
from collections import defaultdict
from pathlib import Path
from typing import Sequence

from analysis.nf006_inputs import Q11_TURN, load_parents
from analysis.nf006_mechanism import (
    build_statement_candidates,
    render_statement_payload,
)
from analysis.retrieval_bakeoff_tier6_121 import ATOMIC_ITEMS, TARGETED_ITEMS
from episodic._render import render_stm_payload


TARGETED_DOMAINS = {
    "Q1": "civil",
    "Q2": "civil",
    "Q4": "art",
    "Q5": "art",
    "Q6": "art",
    "Q7": "marine",
    "Q8": "marine",
    "Q10": "marine",
}


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).lower()


def availability(payload: str, items: Sequence[tuple]) -> list[dict]:
    normalized = normalize(payload)
    return [
        {
            "domain": str(row[0]),
            "item": str(row[1]),
            "available": str(row[2]) in normalized,
        }
        for row in items
    ]


def disposition(
    *,
    targeted_pass: bool,
    c0: int,
    c1: int,
    t1: int,
    monetary_gain_over_c1: bool,
) -> str:
    if not targeted_pass:
        return "TARGETED_REGRESSION - CHARACTERIZED"
    if t1 >= 14 and t1 > c1 and monetary_gain_over_c1:
        return "INTERNAL_DILUTION_RESCUES_Q11 - CHARACTERIZED"
    if t1 > c1 and monetary_gain_over_c1:
        return "INTERNAL_DILUTION_CARRIES_SIGNAL - CHARACTERIZED"
    if c1 > c0 and t1 <= c1:
        return "PACKING_ONLY_GAIN - CHARACTERIZED"
    return "NO_INTERNAL_DILUTION_SIGNAL - CHARACTERIZED"


def measure(selection_path: Path) -> dict:
    sealed = json.loads(selection_path.read_text(encoding="utf-8"))
    records = {
        (str(row["arm"]), int(row["probe_turn"])): row
        for row in sealed["records"]
    }
    parents = load_parents()
    parent_by_id = {str(row["id"]): row for row in parents}
    statements = build_statement_candidates(
        tuple(row for row in parents if int(row["turn_number"]) < Q11_TURN)
    )
    statement_by_id = {str(row["id"]): row for row in statements}

    payloads: dict[tuple[str, int], str] = {}
    for key, record in records.items():
        arm, _turn = key
        selected_ids = [str(value) for value in record["selected_ids"]]
        if arm == "C0_EPISODE":
            payload = render_stm_payload(
                [], [parent_by_id[value] for value in selected_ids]
            )
        else:
            payload = render_statement_payload(
                [statement_by_id[value] for value in selected_ids]
            )
        import hashlib

        if hashlib.sha256(payload.encode("utf-8")).hexdigest() != record["payload_sha256"]:
            raise AssertionError("Sealed payload digest did not reconstruct")
        if len(payload) != int(record["serialized_chars"]):
            raise AssertionError("Sealed payload character count did not reconstruct")
        payloads[key] = payload

    q11: dict[str, dict] = {}
    for arm in ("C0_EPISODE", "C1_INHERITED_STATEMENT", "T1_OWN_STATEMENT"):
        rows = availability(payloads[(arm, Q11_TURN)], ATOMIC_ITEMS)
        available_rows = [row for row in rows if row["available"]]
        per_domain: dict[str, int] = defaultdict(int)
        for row in available_rows:
            per_domain[row["domain"]] += 1
        record = records[(arm, Q11_TURN)]
        q11[arm] = {
            "available": len(available_rows),
            "total": len(rows),
            "per_domain": dict(sorted(per_domain.items())),
            "items": rows,
            "selected_count": record["selected_count"],
            "distinct_parent_count": record["distinct_parent_count"],
            "serialized_chars": record["serialized_chars"],
            "payload_sha256": record["payload_sha256"],
        }

    for arm in q11:
        own = {row["item"] for row in q11[arm]["items"] if row["available"]}
        c0_items = {
            row["item"] for row in q11["C0_EPISODE"]["items"] if row["available"]
        }
        c1_items = {
            row["item"]
            for row in q11["C1_INHERITED_STATEMENT"]["items"]
            if row["available"]
        }
        q11[arm]["gains_vs_c0"] = sorted(own - c0_items)
        q11[arm]["losses_vs_c0"] = sorted(c0_items - own)
        q11[arm]["gains_vs_c1"] = sorted(own - c1_items)
        q11[arm]["losses_vs_c1"] = sorted(c1_items - own)

    targeted_rows: list[dict] = []
    by_probe: dict[str, dict[str, int]] = {}
    by_domain: dict[str, dict[str, int]] = defaultdict(lambda: {"C0": 0, "T1": 0})
    for question, (turn, needles) in TARGETED_ITEMS.items():
        c0_payload = normalize(payloads[("C0_EPISODE", int(turn))])
        t1_payload = normalize(payloads[("T1_OWN_STATEMENT", int(turn))])
        probe_counts = {"C0": 0, "T1": 0}
        domain = TARGETED_DOMAINS[question]
        for item in needles:
            c0_value = str(item) in c0_payload
            t1_value = str(item) in t1_payload
            probe_counts["C0"] += int(c0_value)
            probe_counts["T1"] += int(t1_value)
            by_domain[domain]["C0"] += int(c0_value)
            by_domain[domain]["T1"] += int(t1_value)
            targeted_rows.append(
                {
                    "question": question,
                    "probe_turn": int(turn),
                    "domain": domain,
                    "item": str(item),
                    "C0_available": c0_value,
                    "T1_available": t1_value,
                    "outcome": "gain" if t1_value and not c0_value else "loss" if c0_value and not t1_value else "tie",
                    "C0_selected_ids": records[("C0_EPISODE", int(turn))]["selected_ids"],
                    "T1_selected_ids": records[("T1_OWN_STATEMENT", int(turn))]["selected_ids"],
                    "C0_payload_sha256": records[("C0_EPISODE", int(turn))]["payload_sha256"],
                    "T1_payload_sha256": records[("T1_OWN_STATEMENT", int(turn))]["payload_sha256"],
                }
            )
        by_probe[question] = probe_counts

    losses = sum(row["outcome"] == "loss" for row in targeted_rows)
    gains = sum(row["outcome"] == "gain" for row in targeted_rows)
    c0_total = sum(row["C0_available"] for row in targeted_rows)
    t1_total = sum(row["T1_available"] for row in targeted_rows)
    probe_pass = all(value["T1"] >= value["C0"] for value in by_probe.values())
    domain_pass = all(value["T1"] >= value["C0"] for value in by_domain.values())
    g8_pass = losses == 0 and t1_total >= c0_total and probe_pass and domain_pass

    t1_q11 = q11["T1_OWN_STATEMENT"]
    c1_q11 = q11["C1_INHERITED_STATEMENT"]
    monetary_gain = any(
        row["domain"] == "monetary" and row["available"]
        and not next(
            prior["available"]
            for prior in c1_q11["items"]
            if prior["item"] == row["item"]
        )
        for row in t1_q11["items"]
    )
    selected_turn90 = [
        row
        for row in records[("T1_OWN_STATEMENT", Q11_TURN)]["steps"]
        if int(row["source_turn"]) == 90
    ]
    monetary_rows = [row for row in t1_q11["items"] if row["domain"] == "monetary"]
    final = disposition(
        targeted_pass=g8_pass,
        c0=q11["C0_EPISODE"]["available"],
        c1=c1_q11["available"],
        t1=t1_q11["available"],
        monetary_gain_over_c1=monetary_gain,
    )
    return {
        "schema": "nf006-measurement-v1",
        "status": final,
        "G8": {
            "pass": g8_pass,
            "losses": losses,
            "gains": gains,
            "C0_total": c0_total,
            "T1_total": t1_total,
            "probe_no_regression": probe_pass,
            "domain_no_regression": domain_pass,
            "by_probe": by_probe,
            "by_domain": dict(by_domain),
            "rows": targeted_rows,
        },
        "G9": {
            "q11": q11,
            "turn90_selected_statements": selected_turn90,
            "turn90_monetary_items": monetary_rows,
            "monetary_gain_over_c1": monetary_gain,
        },
        "embedding_calls": 0,
        "generation_calls": 0,
    }
