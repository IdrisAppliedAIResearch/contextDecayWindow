"""Fail when a rubric requires facts not planted before its probe turn."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path


def normalized(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).casefold()
    text = text.replace("–", "-").replace("—", "-").replace("−", "-")
    return re.sub(r"\s+", " ", text)


def load_turns(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    turns = payload["turns"] if isinstance(payload, dict) else payload
    return [
        {
            "turn": int(turn.get("turn", index)),
            "text": turn.get("user")
            or turn.get("user_message")
            or turn.get("content")
            or turn.get("text")
            or "",
        }
        for index, turn in enumerate(turns, 1)
    ]


def load_rubric(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not re.match(r"\| (?:I|Q)\d+ ", line):
            continue
        label, turn, kind, expected = [
            cell.strip() for cell in line.strip("|").split("|")
        ]
        rows.append(
            {
                "label": label,
                "probe_turn": int(turn),
                "kind": kind,
                "items": [item.strip() for item in expected.split(";")],
            }
        )
    if not rows:
        raise RuntimeError(f"No rubric rows found in {path}")
    return rows


def audit(script_path: Path, rubric_path: Path) -> dict:
    turns = load_turns(script_path)
    rubric = load_rubric(rubric_path)
    results = []
    for probe in rubric:
        item_results = []
        for item in probe["items"]:
            components = [component.strip() for component in item.split(" + ")]
            component_results = []
            for component in components:
                needle = normalized(component)
                source_turns = [
                    turn["turn"]
                    for turn in turns
                    if needle in normalized(turn["text"])
                    and turn["turn"] != probe["probe_turn"]
                ]
                earliest = min(source_turns) if source_turns else None
                component_results.append(
                    {
                        "component": component,
                        "earliest_source_turn": earliest,
                        "planted_before_probe": (
                            earliest is not None and earliest < probe["probe_turn"]
                        ),
                    }
                )
            item_results.append(
                {
                    "item": item,
                    "components": component_results,
                    "planted_before_probe": all(
                        component["planted_before_probe"]
                        for component in component_results
                    ),
                }
            )
        results.append(
            {
                "label": probe["label"],
                "probe_turn": probe["probe_turn"],
                "kind": probe["kind"],
                "items": item_results,
                "pass": all(item["planted_before_probe"] for item in item_results),
            }
        )
    failures = [
        {
            "label": probe["label"],
            "probe_turn": probe["probe_turn"],
            "unavailable_items": [
                item["item"]
                for item in probe["items"]
                if not item["planted_before_probe"]
            ],
        }
        for probe in results
        if not probe["pass"]
    ]
    return {
        "check": "probe_fact_order",
        "criterion": (
            "Every required fact component must appear in a scripted user turn "
            "strictly before its probe turn."
        ),
        "script": str(script_path),
        "rubric": str(rubric_path),
        "probe_count": len(results),
        "result": "PASS" if not failures else "FAIL",
        "failure_count": len(failures),
        "failures": failures,
        "probes": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--script", type=Path, required=True)
    parser.add_argument("--rubric", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = audit(args.script, args.rubric)
    rendered = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0 if result["result"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
