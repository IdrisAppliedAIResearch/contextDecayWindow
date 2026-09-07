"""Fixed, extractive reference detection; no event-resolution claim."""
from dataclasses import dataclass, asdict
from .source import digest, canonical

PRONOUNS = frozenset("he she him her his hers they them their theirs it its this that these those".split())


@dataclass(frozen=True)
class Reference:
    id: str
    unit_id: str
    text: str
    offset: int
    mentions: tuple[str, ...]

    def serialize(self):
        return asdict(self)


def extract(unit, doc):
    """doc is a version-pinned spaCy parse of the exact original unit text."""
    if doc.text != unit.text:
        raise ValueError("Parser input differs from original source")
    chunks = list(doc.noun_chunks)
    found = []
    for sentence in doc.sents:
        mentions = [t.text for t in sentence if t.lower_ in PRONOUNS]
        mentions += [c.text for c in chunks if sentence.start <= c.start < sentence.end
                     and any(t.lower_ == "the" and t.dep_ == "det" for t in c)]
        if mentions:
            text = sentence.text
            key = digest(canonical([unit.id, sentence.start_char, text]))
            found.append(Reference(key, unit.id, text, sentence.start_char, tuple(sorted(set(mentions)))))
    return tuple(found)
