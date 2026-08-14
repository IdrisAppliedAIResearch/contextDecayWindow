# NF-006 Part 1 Exploration - Internal Statement Candidate Identity

**Status:** `EXPLORATION ONLY - OUTCOMES SEALED`
**Corpus:** corrected `c121_l` raw store, episodes eligible before turn 120
**Calls:** zero model calls, zero embedding calls

## Behavioral identity

Each user message remains one candidate. Assistant text splits at top-level
numbered starts when at least two are present, and otherwise at blank
paragraphs. A standalone `(Risk: ...)` marker is metadata and is dropped; an
inline marker remains part of its statement. Source turn, role, ordinal, parent
episode, and domain are inherited mechanically.

This is a paragraph/numbered-section splitter, not the existing sentence-span
segmenter. It preserves the four numbered monetary sections in turn 90 as four
units rather than fragmenting their explanations sentence by sentence.

## Distribution

The 119 eligible episodes become 791 unique statement candidates: 119 user
units and 672 assistant units. Candidate length is 31-1,811 characters, with
median 564 and p90 821. Episodes produce 3-14 units, median 7 and p90 8. No
empty, duplicate, or unsplit degenerate unit remains. One residual unit is
1,811 characters, just above the 1,800-character audit marker; it is retained
and exposed rather than split by an unregistered fallback.

Turn 90 becomes five units: its 262-character user request plus four assistant
sections of 601, 709, 571, and 644 characters. This matches the unit used in
the authorized causal spot check without reading its cosine outcome here.

## Name-to-behavior checks

- `statement` means one whole user message or one assistant numbered/paragraph
  block; it does not mean sentence, source turn, or episode.
- `whole store` means all 119 episodes eligible at turn 120, not E005's deployed
  34-episode shortlist or cosine top 100.
- `split` changes candidate identity and cost but does not summarize, rewrite,
  or generate text.
- `outcome sealed` means this exploration reads no probe query, Q11 key,
  targeted key, rank, cosine, selection, or availability artifact.

The machine-readable distribution and input database hash are in
`artifacts/part1_exploration.json`.
