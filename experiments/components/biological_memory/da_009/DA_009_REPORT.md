# DA-009 Reversible Role-Pattern Compression Report

**Status:** `INCREMENTAL_COMPACT_SIGNAL`
**Protocol commit:** `ac1ea834`
**Blind-selection commit:** `e231b698`
**Standing:** post-outcome incremental architecture diagnostic on spent NF-004
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 30, 2026

## Result

Encoding the modal pair-level speaker sequence once per context frees another
median 147 characters beyond DA-008 (p10 111, p90 191; minimum 79) while every
direct context remains byte-reversible and non-expanding. Direct evidence stays
935/1,098 complete.

With DA-004 benefit scores and allocation frozen, complete delivery rises from
DA-008's 961 to **966**:

| Renderer | Complete | Gains vs direct | Losses vs direct | Links admitted |
|---|---:|---:|---:|---:|
| DA-008 speaker dictionary | 961 | 26 | 0 | 2,561 |
| DA-009 role pattern | **966** | **31** | **0** | 3,181 |

Conversation totals do not regress. DA-009 adds two complete items in `conv-26`,
two in `conv-49`, one in `conv-50`, and ties the other three conversations.
The registered descriptive status therefore passes.

## Incremental Attribution

The extra 147 median direct characters, plus cheaper matching link payloads,
allow 620 additional link admissions. Median linked characters rise from 480
to 635 while total context remains nearly full at 15,959 characters, with 41
characters unused.

DA-009 has seven item-level completions absent from DA-008 and loses two DA-008
completions through greedy allocation rerouting. The net +5 contrast has exact
two-sided p=.180 and is not statistically differentiated on its own. Direct
evidence is never lost; the two trades occur only among appended links.

Gain depth remains p10/p50/p90 1/1/2. The same high-ranked links carry the new
evidence; additional capacity chiefly changes which early full pair fits.

## Ceiling

The one-hop oracle remains 986, or 51 gains over direct. DA-009 recovers 31/51,
leaving 20 reachable gains. The observed sequence is:

- protected speaker dictionary: +26 gains at median 520 usable characters;
- role-pattern compression: +5 more gains from about 147 additional direct
  characters plus matching-link savings.

This is consistent with a capacity-limited, approximately incremental regime,
not indiscriminate token flooding: direct content is fixed and exactly decoded,
while measured metadata savings buy additional full linked pairs. The next
useful branch is a more compact reversible linked payload or further repeated
structure removal, with ranking still frozen.

## Integrity and Boundary

The blind role artifact replayed byte-identically at SHA-256
`0fbe8e54d3385575749d779429488d3e1efe2e5b5815a87aa7403a4650cbf0bb`.
The result SHA-256 is
`5c8cb2102bcfe5c959ff9d7c6c811af8bef26c227517d4d7a7bbbfb28df524aa`.
All registered populations, DA-004 AUC .823401708567509, direct 935, and DA-008
961 reproduce exactly.

Structural reversibility remains an availability claim. It does not establish
that a reader interprets the role header, and this spent corpus does not
independently validate DA-004 ranking or authorize adoption.

