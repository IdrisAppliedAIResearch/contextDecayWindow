"""The DR-001 compact episode renderer - the serialization contract.

Moved verbatim from the source repository (`src/memory/context_builder.py`,
`src/memory/stm_context_builder.py`, `src/memory/context_matched_stm.py`,
implementation commit 202b1883). Byte-identical output is the extraction's
acceptance bar: budget accounting charges the exact serialized characters
these functions produce, so any drift here silently changes every number
downstream.
"""

from __future__ import annotations

from html import escape
from typing import Iterable


def render_episode_element(episode: dict) -> str:
    """Serialize one source episode with only attribution-critical structure."""
    turn = _attribute(episode.get("turn_number", ""))
    return "\n".join(
        (
            f'<episode turn="{turn}">',
            f"<user>{_text(episode.get('user_message', ''))}</user>",
            (
                "<assistant>"
                f"{_text(episode.get('assistant_message', ''))}"
                "</assistant>"
            ),
            "</episode>",
        )
    )


def render_episode_block(name: str, episodes: list, tier: str) -> str:
    if not episodes:
        return f"<{name}/>"
    lines = [f"<{name}>"]
    for episode in episodes:
        lines.append(render_episode_element(episode))
    lines.append(f"</{name}>")
    return "\n".join(lines)


def render_stm_payload(
    recent_episodes: Iterable[dict],
    stm_episodes: Iterable[dict],
) -> str:
    return "\n\n".join(
        (
            render_episode_block(
                "recent_context",
                list(recent_episodes),
                "recent",
            ),
            render_episode_block(
                "retrieved_stm",
                list(stm_episodes),
                "stm",
            ),
        )
    )


def _attribute(value) -> str:
    return escape(str(value), quote=True)


def _text(value) -> str:
    return escape(str(value), quote=False)
