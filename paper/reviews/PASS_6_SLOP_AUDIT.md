# PAPER-001 — Pass 6, Slop Audit

Against the post-Cycle-2 draft. The specification's §6 rules, checked one at a
time, with what was found and what was done.

---

## Banned vocabulary — mechanical scan

| Term | Hits | Disposition |
|---|---:|---|
| "delve" | 0 | — |
| "leverage" as a verb | 0 | — |
| "robust" | 0 | — |
| "seamless" | 0 | — |
| "cutting-edge" | 0 | — |
| "paradigm shift" | 0 | — |
| "it is important to note" | 0 | — |
| "in the realm of" | 0 | — |
| "a testament to" | 0 | — |
| "this raises interesting questions" | 0 | — |
| hedging stacks ("may potentially", "might possibly", "could potentially") | 0 | — |
| filler openers ("In recent years", "increasingly important") | 0 | — |
| "novel" / "novelty" | 3 | **All three retained.** §1.3 uses it to *refuse* the claim ("No novelty for maximal marginal relevance…"), which the rule requires. The other two are Study 003's promotion filter, which is literally named novelty. No instance describes this paper's contribution |

The paper never calls its own contribution novel. §1.3 explicitly disclaims it,
and §5.7 attributes the decomposition's absence elsewhere to a mechanical cause
— it needs an answer key and exact-cost accounting — rather than to insight.

---

## Rhythmic tricolons

Three found. Two cut, one kept.

**Cut.** §6.3 read "reproducible, free of generated intermediate text, and
provenance-preserving." The middle item is the same claim as the third — text
that is never generated is why provenance survives — so it was carrying cadence,
not content. The following paragraph explained only two of the three, which is
the tell. Now: "reproducible and provenance-preserving," both explained.

**Cut.** §9 repeated the same shape: "reproducible given a pinned embedder, free
of generated intermediate text, and auditable." Now two items.

**Kept.** §4's closing line — "Five studies of write-time selection, one bakeoff
of query-time selection, and two attempts at query representation" — is an
inventory with three counts in it, not a cadence. Every element carries a number
and maps to a subsection.

---

## Every adjective attached to a number, or cut

Checked section by section. The surviving unquantified adjectives are of three
kinds, all permitted:

- **Structural**: "append-only", "set-level", "data-dependent", "verbatim",
  "offline". These name a kind, not a degree.
- **Explicitly marked as interpretation**: §6.3's "deployable", inside a
  subsection labelled interpretation rather than measurement.
- **Negations of a measured quantity**: "not a controlled series", "unbounded
  retention".

Two were repaired in earlier passes rather than this one: "outperformed" in §9
(Cycle 1, B2) became a statement about gates, and §6.2's "smaller than the
deployed systems" (Cycle 1, B1) became a statement about the listed mechanisms.

---

## Negative results stated flatly

§4's table gives outcomes without cushioning. §4.2 ends "All 17 facts were
present in the raw store. Retrieval did not find them." §5.2 states that the
shipped configuration scores below the baseline on the deployed pool without
softening it, and §5.7 promotes that to the section's conclusion. §6 opens by
stating no live run exists.

The one place the draft had spin was §5.2's "Every one of the 146 configurations
beat the deployed 6 of 17," which was true only on one pool and read as
general. Cycle 1 A1 removed it.

---

## Where uncertain, say what would settle it

All nine limitations name a settling measurement. §8.5's was rewritten in Cycle 1
from "collect an unscripted corpus" — expensive and vague — to a rank-versus-
lexical-rarity correlation runnable on committed data. §8.8 names rerunning the
sweep under a second embedder. §7.3's probe-order count was demoted in Pass 2
rather than asserted, and the paper describes the error class instead.

---

## Sentences deletable without loss

Four cut. One example, from §6.4, which had a two-sentence opener interrupted by
a corpus caveat inserted in Cycle 2; the caveat now precedes the opener instead
of splitting it.

One heading changed for a different reason: §6.1 was "Eleven efforts removed
more than they added," and its table happens to have eleven rows — but "eleven
efforts" elsewhere in the paper means ten studies plus the bakeoff, which are
not in one-to-one correspondence with the eleven removed mechanisms. The heading
is now "What was removed," and a line under it says the count is a coincidence.

---

## Internal consistency sweep

Four inconsistencies found, all introduced by the review revisions themselves.

| Found | Fix |
|---|---|
| Header still read "Pass 3" | Updated |
| §1.2 called the three constraints "independently bounded" after §5.7 established they bind in a forced order | Contribution 1 rewritten |
| §1.3 cited "§5.6" for the eight-of-nine probe reading, which is §5.5 | Corrected |
| §7.7 still said "about 20 scoring errors" after §7.1 gained the 3-to-43 interval | Now quotes the interval and the point estimate |

The last one is the same species as the errors §7 catalogues: a number corrected
in one place and left standing in another. It was found by grepping for the
superseded value rather than by rereading, which is the only method that works.

---

## Read-aloud test

The rule: if a paragraph could preface any paper in any field, delete it and
write what happened.

The openers most at risk were §1's first paragraph and §5's first line. §1 opens
on the specific trade — transcript cost against summary loss — and reaches "Most
of those efforts failed" by its fourth sentence. §5.1 opens with two scoping
notes and then a number. §6 opens with "none of it was run live."

No paragraph survived that could preface a different paper.
