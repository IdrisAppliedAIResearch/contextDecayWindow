# PAPER-001 — Adversarial Review, Cycle 2

Against the revised draft at commit `e875924f`. Same three reviewers, re-reading
after the Cycle 1 revisions.

---

## Reviewer A — methodologist

The pool/selector correction is well made, and promoting it to §5.7 and the
abstract is the right call — it is the paper's sharpest measured claim now.
Remaining objections are smaller, but two of them are internal contradictions
introduced by the revision itself, which is the usual cost of a large edit.

**A7. The draft still says "Pass 3" in its header.** Line 7.

**A8. §1.2's first contribution now contradicts §5.7.**

It reads: "three constraints separated and each **independently** bounded … The
constraints bind on different quantities and **respond to different fixes**."

§5.7 now says the opposite and says it emphatically: the order is forced, the
objective does not help until the pool is widened, and applying the objective
fix alone makes the shipped configuration worse. Those are not independent
constraints responding to independent fixes. They compose, and the composition
is the finding. Rewrite the contribution.

**A9. The abstract retains the query-type claim §5.5 now disowns.**

Abstract: "so the failure is specific to enumeration rather than general to
similarity retrieval." §5.5, after Cycle 1: "One instance cannot establish a
query *type*." The abstract is asserting what the body declines to assert.
Restate as one probe against eight.

**A10. Stale cross-reference.** §1.3 cites "§5.6" for the eight-of-nine probe
measurement. That content is §5.5; §5.6 is the residual floor.

**A11. §5.2's new table has an empty column that invites a misreading.**

The "deployed baseline" column shows 6/17 on the first row and em-dashes below.
A reader may take the dashes to mean the baseline was measured and scored
nothing on the wider pools. It was not measured on them at all — A0 has no pool
variable. Say so in the table note rather than leaving blanks.

---

## Reviewer B — systems researcher

Section 6's opening statement about no live run is exactly what was missing.
Three things remain.

**B6. "No inference calls anywhere in the memory path" is not true as written,
and the code says so.**

`EpisodeStore.context()` calls `embed_solo(self._embedder, query)` before
building anything. The memory path calls an embedding model on every query, and
embeds every episode on append. What the program means — and what its Study 005
principle established — is that there are no *generative* model calls: nothing
in the path asks a model to write text about the store. That is a real and
valuable property. It is not the absence of model calls.

This matters for the deployment argument in §6.3. "Offline" and "deterministic"
are claimed as consequences of having no model calls; in fact the component
requires an embedding model to be resident, and §7.4 is a whole subsection about
how sensitive it is to that model's calling convention. Determinism holds
*given* a pinned embedder, which is why the library asserts a sentinel hash on
open. Say it that way.

**B7. The paper silently switches corpora between §5 and §6.4.**

§5 is a 121-turn conversation with 119 eligible episodes. §6.4's boundedness and
latency results replay a 1,000-turn run. Both are called "the store". A reader
tracking the argument will assume §6.4's 1,000-turn boundedness applies to the
§5 configuration on the §5 corpus, and it does not — it is a different run at a
different scale. Name each one where it appears.

**B8. The shipped call shape differs from the one that produced the headline
result, and the paper does not mention it.**

E005 embedded nine probe queries in one batch. `store.context()` embeds a single
query alone. §7.4 establishes that this exact difference flips 6 of 146
committed payloads. So a reader who installs the library and runs the shipped
path is not obviously reproducing the 12/17.

I checked, and the answer is favourable to you: the primary configuration is not
among the six that flip. But the paper should say that out loud, because a
careful reader will notice the discrepancy and the reassurance is one sentence.

---

## Reviewer C — skeptic

Cycle 1 addressed my objections properly. §8.5's replacement experiment is the
right one and I withdraw C3. Two new things, one of which I think is the
paper's deepest unexamined assumption.

**C6. Availability may be satisfied by a wrong answer, and §5.1's new paragraph
implies it.**

The revision now says four of five known-optimum episodes are prior probe
exchanges, and adds that "this probe's earlier answers were largely wrong." Put
those together. Availability is measured by an item's presence in the delivered
block. If a prior answer restates an entity correctly inside an otherwise wrong
response, the item counts as available.

So a nontrivial part of the 15-of-17 optimum, and of any configuration scoring
well by recovering those episodes, may consist of delivering the model's own
earlier mistakes with the right nouns in them. That does not break the
decomposition — the pool and objective results are about which episodes get
selected, not about their truth — but it does mean "makes 15 of 17 available"
and "would help the model answer correctly" are further apart than the paper
suggests. §5.1's availability disclaimer covers this formally. It does not
cover it in spirit, and one sentence would.

**C7. Does the title survive §5.7?**

"Selection, Not Capacity." After Cycle 1 the headline finding is that the
candidate pool binds first and the objective is a regression without it. A pool
cut is a capacity limit on the candidate set, even though it is not a limit on
the character budget. The title is defensible — the contrast is with the budget,
which was never the constraint — but the paper should make the distinction once,
because a skeptical reader will hold the title against §5.3.

---

## Dispositions — Cycle 2

| # | Objection | Disposition |
|---|---|---|
| A7 | Header says Pass 3 | **ACCEPTED.** Trivial |
| A8 | §1.2 contradicts §5.7 on independence | **ACCEPTED.** Rewrite contribution 1 around the forced order |
| A9 | Abstract asserts the query-type claim | **ACCEPTED.** Restate as one probe against eight |
| A10 | Stale §5.6 reference | **ACCEPTED** |
| A11 | Empty column reads as measured zero | **ACCEPTED.** Add a table note |
| B6 | "No inference calls" is imprecise | **ACCEPTED, and it is a factual correction.** Change to "no generative model calls"; state that an embedding model is required and that determinism holds given a pinned embedder |
| B7 | Corpora switch silently | **ACCEPTED.** Name the 121-turn and 1,000-turn runs where each is used |
| B8 | Shipped call shape differs from the headline's | **ACCEPTED.** State the difference and that the primary configuration is not among the six affected |
| C6 | Availability can be satisfied by a wrong answer | **ACCEPTED.** One sentence in §5.1 and a limitation cross-reference |
| C7 | Title versus the pool finding | **ACCEPTED.** One clarifying sentence in §5.7 |

Ten objections, ten accepted. **None requires structural change** — all are
local corrections, wording, or one-sentence additions, against Cycle 1's four
section rewrites and one table replacement.

Two are factual rather than presentational: B6, where the paper asserted a
property the code contradicts, and B8, where a reproduction hazard went
unmentioned. Both are the same species as the errors §7 catalogues, found the
same way — by reading the artifact instead of the summary.

**Cycle 2 raises no objection requiring structural change, so the review loop
terminates here** under the two-cycle minimum, with Cycle 1's revisions and
Cycle 2's corrections applied.
