from __future__ import annotations

import time
from dataclasses import dataclass
from html import escape

from .models import RankedCandidate


def _attribute(value: object) -> str:
    return escape(str(value), quote=True)


def _text(value: object) -> str:
    return escape(str(value), quote=False)


def render_candidate_element(ranked: RankedCandidate) -> str:
    candidate = ranked.candidate
    common = [
        f'source_episode_id="{_attribute(candidate.source_episode_id)}"',
        f'turn="{candidate.turn_number}"',
        f'topic_id="{_attribute(candidate.topic_id)}"',
        f'topic_label="{_attribute(candidate.topic_label)}"',
        f'score="{ranked.score:.6f}"',
    ]
    if candidate.unit_type == "span":
        attributes = [
            *common,
            f'role="{_attribute(candidate.role)}"',
            f'span_start="{candidate.span_start}"',
            f'span_end="{candidate.span_end}"',
        ]
        return (
            f"  <span {' '.join(attributes)}>"
            f"{_text(candidate.span_text)}</span>"
        )
    return "\n".join(
        [
            (
                f"  <episode {' '.join(common)} "
                f'domain="{_attribute(candidate.domain)}">'
            ),
            f"    <user_message>{_text(candidate.user_message)}</user_message>",
            (
                "    <assistant_message>"
                f"{_text(candidate.assistant_message)}"
                "</assistant_message>"
            ),
            "  </episode>",
        ]
    )


def render_retrieval_block(
    method_id: str,
    selected: list[RankedCandidate],
) -> str:
    method = _attribute(method_id)
    if not selected:
        return f'<retrieved_memory method="{method}"/>'
    lines = [f'<retrieved_memory method="{method}">']
    lines.extend(render_candidate_element(candidate) for candidate in selected)
    lines.append("</retrieved_memory>")
    return "\n".join(lines)


@dataclass
class PackResult:
    selected: list[RankedCandidate]
    rendered_block: str
    phases: dict[str, str]
    skipped_oversized: int
    duplicate_drops: int
    elapsed_ms: float


def pack_ranked_candidates(
    method_id: str,
    ranked_with_phases: list[tuple[RankedCandidate, str]],
    budget: int,
) -> PackResult:
    if budget < 0:
        raise ValueError("budget must be non-negative")
    start = time.perf_counter()
    empty_block = render_retrieval_block(method_id, [])
    if len(empty_block) > budget:
        raise ValueError("budget cannot fit the retrieval block wrapper")
    selected: list[RankedCandidate] = []
    phases: dict[str, str] = {}
    identities: set[str] = set()
    skipped_oversized = 0
    duplicate_drops = 0
    rendered_length = len(empty_block)

    for ranked, phase in ranked_with_phases:
        identity = ranked.candidate.rendered_identity
        if identity in identities:
            duplicate_drops += 1
            continue
        element_length = len(render_candidate_element(ranked))
        if selected:
            proposed_length = rendered_length + 1 + element_length
        else:
            proposed_length = len(render_retrieval_block(method_id, [ranked]))
        if proposed_length > budget:
            skipped_oversized += 1
            continue
        selected.append(ranked)
        identities.add(identity)
        phases[identity] = phase
        rendered_length = proposed_length

    rendered = render_retrieval_block(method_id, selected)
    if len(rendered) != rendered_length:
        raise AssertionError("Incremental serialization accounting drifted")
    if len(rendered) > budget:
        raise AssertionError("Serialized retrieval block exceeded its budget")
    return PackResult(
        selected=selected,
        rendered_block=rendered,
        phases=phases,
        skipped_oversized=skipped_oversized,
        duplicate_drops=duplicate_drops,
        elapsed_ms=(time.perf_counter() - start) * 1000.0,
    )
