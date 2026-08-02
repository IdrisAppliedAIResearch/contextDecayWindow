"""CC-002 T4: the Study 010 replay blocks reproduce through the library renderer.

Renders the three DR-001 post-fix blocks (Study 010 Q13/Q14 and the
corrected-bakeoff Q4 payload) using episodic's renderer and asserts each
against the committed `post_fix/summary.json` SHA-256, episode identity,
and order. The serialization contract moved without changing a byte.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from episodic._render import render_episode_block, render_episode_element

from src.analysis.rendering_expansion_replay import (
    BAKEOFF_TURN,
    STUDY_010_TURNS,
    _load_bakeoff_selected,
    _load_study_010_selected,
)

POST_FIX_SUMMARY = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "rendering_expansion"
    / "artifacts"
    / "post_fix"
    / "summary.json"
)
OUTPUT = (
    REPO_ROOT
    / "experiments"
    / "components"
    / "library_extraction"
    / "artifacts"
    / "cc002"
    / "t4_render_replay.json"
)


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def main() -> None:
    for symbol in (render_episode_block, render_episode_element):
        if not symbol.__module__.startswith("episodic."):
            raise AssertionError(f"{symbol.__name__} is not the library's")

    committed = {
        block["block"]: block
        for block in json.loads(POST_FIX_SUMMARY.read_text(encoding="utf-8"))[
            "blocks"
        ]
    }
    results = []

    for turn in STUDY_010_TURNS:
        selected, logged_ids = _load_study_010_selected(turn)
        if any(episode.get("render_mode") != "episode" for episode in selected):
            raise AssertionError(
                "A non-episode element appeared; the library renderer only "
                "serializes episodes"
            )
        rendered = render_episode_block("retrieved_ltm", selected, "ltm")
        name = f"study_010_q{13 if turn == 999 else 14}"
        results.append(
            _check(
                name=name,
                rendered=rendered,
                rendered_ids=[str(episode["id"]) for episode in selected],
                logged_ids=logged_ids,
                reference=committed[name],
            )
        )

    recent, stm, context_row = _load_bakeoff_selected()
    rendered = "\n\n".join(
        (
            render_episode_block("recent_context", recent, "recent"),
            render_episode_block("retrieved_stm", stm, "stm"),
        )
    )
    results.append(
        _check(
            name="bakeoff_tier6_q4",
            rendered=rendered,
            rendered_ids=[
                str(episode["id"]) for episode in (*recent, *stm)
            ],
            logged_ids=list(context_row["selected_ids"]),
            reference=committed["bakeoff_tier6_q4"],
        )
    )

    status = "PASS" if all(row["match"] for row in results) else "FAIL"
    payload = {
        "test": "CC-002 T4",
        "status": status,
        "renderer_module": render_episode_element.__module__,
        "reference": str(POST_FIX_SUMMARY.relative_to(REPO_ROOT)),
        "bakeoff_turn": BAKEOFF_TURN,
        "blocks": results,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(payload, indent=2, sort_keys=True))
    if status != "PASS":
        raise SystemExit(1)


def _check(
    *,
    name: str,
    rendered: str,
    rendered_ids: list[str],
    logged_ids: list[str],
    reference: dict,
) -> dict:
    digest = _text_sha256(rendered)
    match = (
        digest == reference["post_fix_sha256"]
        and len(rendered) == int(reference["post_fix_serialized_chars"])
        and rendered_ids == logged_ids
    )
    return {
        "block": name,
        "episode_count": len(rendered_ids),
        "serialized_chars": len(rendered),
        "committed_chars": int(reference["post_fix_serialized_chars"]),
        "sha256": digest,
        "committed_sha256": reference["post_fix_sha256"],
        "identity_order_match": rendered_ids == logged_ids,
        "match": match,
    }


if __name__ == "__main__":
    main()
