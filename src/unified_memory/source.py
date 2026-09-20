"""Source-only schema, immutable identities, and common chronological renderer."""
from __future__ import annotations
from dataclasses import dataclass, asdict
import hashlib
import json
import re
from xml.sax.saxutils import escape, quoteattr


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class Unit:
    id: str
    conversation: str
    session: str
    position: int
    date: str
    member_ids: tuple[str, ...]
    text: str
    historical_text: str
    speakers: tuple[str, ...]

    def serialize(self) -> dict:
        return asdict(self)


def adapt(conversation: dict, identity: str) -> tuple[Unit, ...]:
    """Only conversation source data enters here, never QA metadata."""
    allowed = {"speaker_a", "speaker_b"}
    allowed.update(k for k in conversation if re.fullmatch(r"session_\d+(_date_time)?", k))
    if set(conversation) - allowed:
        raise ValueError("Unknown source schema fields")
    sessions = sorted((k for k in conversation if re.fullmatch(r"session_\d+", k)),
                      key=lambda s: int(s.split("_")[-1]))
    units, source_ids = [], set()
    for session in sessions:
        turns = conversation[session]
        for start in range(0, len(turns), 2):
            members = turns[start:start + 2]
            ids = tuple(str(t["dia_id"]) for t in members)
            if len(set(ids)) != len(ids) or source_ids.intersection(ids):
                raise ValueError("Duplicate source member identity")
            source_ids.update(ids)
            historical = "\n".join(f"{t['speaker']}: {t['text']}" for t in members)
            lines = []
            for t in members:
                lines.append(f"{t['speaker']}: {t['text']}")
                caption = t.get("blip_caption")
                if caption:
                    if not isinstance(caption, str):
                        raise ValueError("Caption is not source text")
                    lines.append(f"[Supplied image-caption annotation, {t['dia_id']}]: {caption}")
            text = "\n".join(lines)
            unit_id = digest(canonical([identity, session, ids, text]))
            units.append(Unit(unit_id, identity, session, len(units),
                              str(conversation.get(session + "_date_time", "")),
                              ids, text, historical, tuple(str(t["speaker"]) for t in members)))
    return tuple(units)


def render(units: tuple[Unit, ...] | list[Unit], selected: set[str]) -> str:
    known = {u.id for u in units}
    if selected - known:
        raise ValueError("Selection contains unknown source IDs")
    return "\n".join(
        f'<record session={quoteattr(u.session)} date={quoteattr(u.date)} '
        f'dialogue_ids={quoteattr(" ".join(u.member_ids))}>\n{escape(u.text)}\n</record>'
        for u in sorted(units, key=lambda u: (u.position, u.id)) if u.id in selected)
