# Errata

## Scoring Integrity Audit (2026-07-26)

**Headline change:** Study 001 changes from VALIDATED to PARTIAL.

The scoring-integrity audit found 19 changed scores across Studies 001-009.
Original response and score artifacts remain unchanged. Corrected item-level values,
rationales, provenance, totals, reliability measures, and cascade verdicts are in
`experiments/audits/scoring_integrity/`.

Most consequential corrections:

- Study 002 C: 13.0 -> 8.5. Q11: 1.0 -> 0.0 (`NO_ANSWER`).
- Study 002 A: 8.0 -> 5.5.
- Study 003 accepted: 12.0 -> 11.5; literal Bar 2 remains FAIL.
- Study 009 S: 10.5 -> 9.0; L remains 12.0, so the null-test gap is 3.0.
- Study 001 iterative: 9.0 -> 8.0; compaction: 3.5 -> 2.5; Bar 2 changes to FAIL.

The first 81-item Layer 2 attempt is invalidated by
`AMENDMENT_003_study003_cross_references.md`. The final results use the replacement
79-item sequence only.

The residual-error figure is extrapolated rather than observed: 3 disagreements
in a 26-item control sample (11.54%) projected over 143 unreviewed items gives
16.5 expected errors, reported informally as about 20. Study 010 was outside
the audit; its exploratory scores are not directly comparable to the corrected
Studies 001-009 series.

## Study 010 LTM Budget Accounting (2026-07-29)

**Headline change:** the published Q13/Q14 LTM character values were charged
content estimates, not serialized block lengths.

Study 010 reported 31,991 and 31,847 LTM characters at Q13 and Q14 and described
them as near-saturation of `B_ltm = 32,000`. DR-001 replayed both committed
blocks character-for-character. Their actual serialized lengths were 53,726 and
53,839 characters, exceeding the nominal budget by 21,726 and 21,839, or 67.9%
and 68.2%. The budget was violated, not saturated.

The old budget authority counted source user/assistant text but omitted
per-episode tags, metadata, and separators. The historical values and run
artifacts remain unchanged. Their classification is corrected here, and the
compact-store scaling conclusion derived from the undercharged values is
withdrawn. Scores and fact-delivery findings do not change because the model
received the recorded blocks, but they describe a budget-noncompliant arm.

DR-001 replaces the renderer with compact, content-identical episode elements
and charges exact complete-block cost. The same historical identity sets render
to 37,619 and 37,545 characters, still above 32,000; production re-selection at
the locked budget admits 69 and 71 episodes. See
`experiments/components/rendering_expansion/`.

The separate reported context peak survives audit. All 2,000 Study 010 rows
recompute from the committed serialized prompts under the registered
`characters // 4` estimator; L peaks at 27,154 and S at 17,541. These are
character-based estimates, not exact model-tokenizer counts. See
`experiments/components/rendering_expansion/artifacts/context_peak_audit/`.

## Retrieval Bakeoff Q4 Cosine and Seal Provenance (2026-07-29)

**Headline change:** the published turn-55/Q4-query cosine changes from
0.16612689197063446 to 0.12042197585105896.

AS-001 reconstructed the turn-55 episode from the committed turn log. Its
embedding is byte-identical to the original local database vector, and the
exact committed turn-115 query yields 0.12042197585105896. The old value has no
committed generating code. Both values remain below the registered K threshold
of 0.48, so K-ineligibility, scores, and the Q4 exclusion verdict do not change.

The audit also found that the corrected Tier 6 mechanism seal lists `study.db`,
but `*.db` is ignored and that file was never committed or placed in Git LFS.
The seal was computed over mixed LF/CRLF working-tree representations. All 264
tracked mechanism files match their seal entries under exact canonical LF or
deterministic CRLF materialization, with no content mismatch; the missing
database means the historical seal cannot establish a complete committed
265-file mechanism tree.

AS-001 does not use the ignored database. It reconstructs candidate identity,
order, topic, and source text from committed logs, reproduces the historical
15-episode/59,708-character payload and SHA-256 exactly, and records the seal
limitation. See `experiments/components/q4_packing/`.

## AS-001 Decision Rule Invalidation (2026-07-29)

**Headline change:** the emitted `PRIMACY MECHANISM LIVE` verdict is withdrawn.

AS-001 opened `S' = 9` at 32k and 16 at 64k, versus 15 episodes in the
historical 59,708-character payload. Its rule assumed compact rendering could
recover slots; it had no interpretation for exact charging reducing them.
Branch A required `S' >= 29` at 32k, while Branch D labeled every failure to
reach rank 27 as a primacy mechanism. The rule could not distinguish a separate
primacy mechanism from the joint effects of rank, greedy N-first packing, and
budget.

This issue was raised after output, so Decision 001 invalidates the
interpretation rather than retroactively amending the locked rule. The original
analysis artifacts remain unchanged as diagnostics. A post-result exact
reachability calculation finds rank 27 first enters at 108,432 characters.
AS-001 does not authorize a pinned tier or an architecture study.

## Retrieval Ledger E002 Budget Interpretation (2026-07-31)

**Headline change:** E002 remains KILL, but its matched-budget improvement is
now part of the primary interpretation.

The closeout originally paired E002's 10/17 result with the registered 13/17
historical hurdle without stating the budget difference in the interpretation.
The corrected Tier 6 Q11 payload that made 13/17 items available was 60,285
characters under its locked 60,595-character cap. The separate 59,708 figure
is Tier 6 Q4 at turn 115. E002 was held to an exact 32,000-character cap.

At the same enforced budget, the unchanged selector made 6/17 items available
at 31,946 characters and segmentation made 10/17 available at 21,761
characters, a 66.7% increase. This does not change the prospectively locked
14/17 pass threshold or the KILL. It changes the interpretation from "did not
solve breadth" without qualification to "did not reach a cross-budget
historical hurdle, while materially improving the matched-budget baseline."

The 6/17 figure is not the program's first exact-budget breadth measurement.
Retrieval bakeoff Tier 1 previously reported 8/17 at 31,861 exactly serialized
characters under its own renderer and M4 method. See
`experiments/components/retrieval_mechanism_ledger/E002_POSTHOC_INTERPRETATION.md`.

## Retrieval Ledger and PAPER-001 IDF Claim (2026-08-03)

**Headline change:** the categorical claim that inverse document frequency
ranked the six hard plants worse than density is withdrawn.

The Study 009 breadth regression audit computed three IDF variants and
designated none as primary. Mean content-word IDF ranked all five eligible
hard-plant spans worse than density. Maximum content-word IDF ranked three
worse and two better; summed IDF per logged word ranked four worse and one
better. The sixth, photophores, was unranked under all three because the audit
retained the formation eligibility filter.

The audit itself reports the three formulas and their rows but does not state
"IDF worse." That categorical sentence first appears four days later in the
retrieval mechanism ledger, without naming a variant, and was later repeated in
PAPER-001 and its claim index. It can only be reconstructed by selecting
`rarity_mean` after seeing all three results. The narrower mean-IDF result
remains descriptive; IDF as a family was not refuted.

No historical artifact is edited and no missing rarity value is recomputed.
See
`experiments/components/retrieval_mechanism_ledger/RD_001_RARITY_PROVENANCE_AUDIT.md`.


## Retrieval Ledger E002 Targeted No-Regression Count (2026-08-01)

**Headline change:** E002's targeted preservation is corrected from **14/16 to
16/16**. Its KILL verdict is unaffected.

E002 reported preserving 14 of 16 committed-available targeted items. Its own
committed artifact `artifacts/e002/targeted_no_regression.csv` records
`preserved = True` on every committed-available row, so no item was ever lost;
only the summary count was wrong.

The cause is a unit mismatch found while implementing E005. `TARGETED_ITEMS`
places Q7 and Q10 both at turn 118, sharing the items `vampyroteuthis
infernalis` and `kenji watanabe`. The availability map was keyed on
`(turn, item)`, which collapses those four rows to two, capping the numerator at
14 distinct keys. The denominator summed `committed_available` over the row
list, counting the duplicates separately, and so equalled 16. The gate
`preserved == required` was therefore unsatisfiable by construction, for any
selector.

E002 was killed on its primary gate, reaching at most 10/17 Q11 items against a
locked 14/17 requirement, so the no-regression result was never binding. The
correction means E002 passed a gate it was previously recorded as failing.

E005 keys availability on `(question, turn, item)` and gates the unit with a
regression test. The defect changed E005's outcome from
`REJECT_NO_REGRESSION` to `PROMOTION_ELIGIBLE`; it was repaired before the
outcome was accepted and no threshold was altered. Committed E002 artifacts are
not edited. See
`experiments/components/retrieval_mechanism_ledger/amendments/AMENDMENT_004_targeted_item_identity.md`.

## Retrieval Ledger MMR Submodularity Claim (2026-08-01)

**Headline change:** the diversity-selection scan's unverified claim that MMR's
objective lacks submodularity is **refuted**. MMR is *non-monotone submodular*.

The scan recorded, explicitly flagged as unconfirmed, that MMR is "widely
described as lacking the submodularity that buys the greedy guarantees."
Verified against the primary text, Lin and Bilmes (2011), *A Class of Submodular
Functions for Document Summarization*, ACL-HLT 510-520, Section 3: Theorem 2
states `F_MMR` is non-monotone submodular, and the surrounding text notes MMR's
diminishing-returns property was "apparently unnoticed until now." The greedy
constant-factor guarantee fails for MMR because the objective is **not
monotone**, not because it is not submodular.

The scan's conclusion, that MMR carries no constant-factor guarantee, stands.
Its stated reason does not. No repository text may describe MMR as
non-submodular. See
`experiments/components/retrieval_mechanism_ledger/E005_POSTHOC_INTERPRETATION.md`.

## episodic Selection-Latency Range and Its Extrapolation (2026-08-02)

**Headline change:** the library README claimed a selection-latency range of
"20-3,000 candidates". DR-002 measured 20-119. The number 3,000 was a
character count from an unrelated table.

`episodic/README.md` cited "35-43 microseconds per candidate over 20-3,000
candidates; empirical scaling exponent 0.96" against
`dr_002/scaling_timings.json`. That artifact holds six rows, from 20 to 119
candidates, and DR-002's own report describes it as "a 6x range in pool
size". The 3,000 appears in the DR-002 report as a cumulative character
figure in the greedy-trace table and was misread as a pool size. The README
line is corrected to 20-119.

The per-candidate figure and the 0.96 exponent are correct inside the range
DR-002 measured. They do not extend past it. CC-005 measured the same
configuration on the same material to 1,000 candidates. Every row below is
`artifacts/cc005/latency_curve.csv`, the median `build_context` wall time over
seven runs per point, embedding excluded:

| Candidates | Median `build_context` | Microseconds per candidate |
|---:|---:|---:|
| 50 | 4.20 ms | 84.0 |
| 100 | 10.01 ms | 100.1 |
| 200 | 25.10 ms | 125.5 |
| 300 | 42.12 ms | 140.4 |
| 400 | 53.93 ms | 134.8 |
| 500 | 66.36 ms | 132.7 |
| 700 | 118.90 ms | 169.9 |
| 850 | 145.68 ms | 171.4 |
| 1,000 | 189.99 ms | 190.0 |

The empirical exponent over 50-1,000 is **1.25**, not 0.96. Clustering's share
of the total rises with it, from 37% at 50 candidates to **81%** at 1,000;
DR-002's "roughly 73% at n = 119" sits on that trend rather than being a
constant.

**Correction to this entry (2026-08-02).** The table above replaces a
four-row version that was wrong in three ways, found while tracing figure
sources for PAPER-001. It was headed "Median build_context" but took its 50-
and 500-candidate rows from `artifacts/cc005/latency_components.csv`
`stage_total_ms` - the sum of the timed stages, which is smaller than the call
- giving 3.8 ms and 65.6 ms where the medians are 4.20 ms and 66.36 ms. Its
1,000-candidate row was a `build_context` median, so the four rows did not
come from one measurement. And its second row, "119 (DR-002's maximum), ~10 ms,
~84", was not a CC-005 measurement at all: CC-005 has no 119-candidate point,
and that row pairs the 100-candidate median with the 50-candidate
per-candidate cost.

The entry's headline is unaffected. 190 ms at 1,000 candidates, the 1.25
exponent, and the 81% clustering share were all read from the correct
artifacts and all stand.

One claim in the original entry does not survive the correction, and it is
worth stating rather than deleting. The entry read "per-candidate cost is flat
to about 119 candidates and rises steadily after", positioned as a reading of
the table. It is not one: across CC-005's own curve, per-candidate cost rises
from 84.0 to 100.1 microseconds between 50 and 100 candidates, which is a 19%
climb inside the range described as flat. The flatness is DR-002's finding
about DR-002's measurement - 35-43 microseconds over 20-119 candidates - and
the two quantities are not comparable: DR-002 timed cluster setup plus the
greedy loop, while CC-005 times the whole `build_context` call, which is why
CC-005 reads about 100 microseconds per candidate at n = 100 where DR-002 reads
about 40 at n = 119. Neither measurement is wrong. Placing them in one column
was.

The consequence is for the projections, not for DR-002. The CC-003/004/005
pre-registration reads "~40 microseconds per candidate, exponent 0.96;
DR-002 projects ~40 ms at 1,000 candidates and ~400 ms at 10,000". Those
come from extending a curve 84x beyond its last measured point. The measured
value at 1,000 candidates is 190 ms, about five times the projection, and
the corresponding projection to 10,000 candidates is roughly 3.2 seconds
rather than 400 ms.

No committed run artifact changes. DR-002's measurements stand as recorded;
what is withdrawn is the range attributed to them in the library README and
the linear extrapolation built on top of them.

## DR-002 Cosine Rank Under the Committed Embedding Call (2026-08-01)

**Headline change:** one published rank moves. DR-002's step-11 selection, turn
118, is corrected from cosine rank **21 to 20** of 119.

DX-001's replay gate established that the carried embedder returns a different
vector for the same query text depending on the shape of the embedding call.
E005 embedded all nine probe queries in one batch; DR-002's rank tables embedded
the query on its own. The two vectors agree to cosine 0.999837 with a largest
component difference of 0.217, and the difference flips 6 of the 146 committed
E005 payloads.

The E005 primary configuration `A3_l0.1_r0.0_k16` is not among the six. Its
selection sequence, character count, domain counts, targeted preservation and
oracle overlap are unchanged, and DX-001 reproduced all 146 committed payload
hashes under the committed call. Re-measured under that call:

- All nine rows of the DR-002 generality table reproduce exactly, including
  Q11's last-needed item at rank 87 and every targeted probe at rank 2 or
  better.
- The worst fact-bearing rank remains 86, so DR-002's registered rule and its
  "cosine ordering is the wrong prior" verdict are unaffected.
- Oracle episode ranks read 14, 20, 22, 86, 112 rather than 14, 21, 22, 86, 112.

Committed DR-002 artifacts are not edited. The re-measurement is
`experiments/components/retrieval_mechanism_ledger/artifacts/e005/dr_002/generality_batched.json`,
produced by `scripts/verify_dr002_generality_batched.py`. The general lesson is
recorded in
`experiments/components/retrieval_mechanism_ledger/DX_001_PART2_DISPOSITION.md`
section 8: reproducing a retrieval result requires reproducing the embedding
call shape, not only the query text.

## EC-001 Rank-to-Retrieval Interpretation (2026-08-03)

**No registered number changes.** The EC-001 report correctly published pooled
median evidence-session rank 2 and any-session recall 109/470 (23.2%), but it
did not explain why a favourable session ordering produced weak delivery. The
omission made the two results read as a contradiction.

A post-run audit of the already-opened sealed Tier 1 mechanism log separates
the stages. Evidence is in the top four on 401/470 questions, but only 96 of
those retrieve any evidence session. At least one exchange clears the carried
`K = 0.48` threshold on 232/500 questions, while a non-recency K exchange
survives exact packing on only 20. Every block is truncated and at least 31,000
characters; median composition is 16 recency, 0 non-recency K, and 1 coverage
exchange. Of 109 evidence-session hits, 91 come from delivered recency and 18
from all non-recency paths. Thirty session hits omit every exact annotated
answer turn.

The corrected interpretation is that the internal top-of-rank inversion is not
a dominant property of these naturalistic questions, while EC-001's adapted
retrieval path is dominated downstream by N-first exact-budget exhaustion.
The threshold is an additional category-specific gate, especially for
single-session preference, and session/exchange granularity explains the later
109-to-79 loss. The diagnostic is explicitly post hoc and does not authorize a
counterfactual parameter change.

Artifact:
`experiments/external/longmemeval/runs/tier1_001/retrieval_path_diagnostic.json`
at commit `7b38badb`.

## EC-002 Packing Counterfactual (2026-08-05)

**No EC-001 registered number changes.** EC-002 tests the post-hoc
recency-first diagnosis with a registered same-store offline counterfactual.
Changing only exact packing priority from recency-first to K-first raises
any-session recall from 109/470 to 261/470 (152 paired gains, zero losses) and
exact-turn-any availability from 79/470 to 196/470 (119 gains, two losses).
The corrected interpretation is stronger: N-first budget exhaustion is a
causal delivery gate under the EC-001 adaptation.

The original EC-001 embedding cache was not retained. A0 is therefore an
amended reproduction under recomputed embeddings, not a byte-exact replay.
EC-001 remains permanently unreplayable at bit granularity; CC-006 protects
retained caches only for runs made after its contract is adopted.

Artifact:
`experiments/external/longmemeval/runs/ec002_k_first/a1_k_first/paired_comparison.json`
at commit `4168a05c`.

## The N Tier Is Not a Recency Window (2026-08-08)

**The architecture description changes; no measured number changes.** Post-unseal
mechanism analysis of Study 011 found that the tier the program calls a recency
window selects by delivery history, not by recency of formation. `logical_n_key`
sorts the whole store by (has ever been delivered, turn last delivered, source
turn, id) ascending — a least-recently-delivered coverage rotation, with source
turn entering only as a third-level tiebreak and entering oldest-first.

Replaying the deployed key against store state reconstructed from
`retrieval_events` reproduces the live ranking on 120 of 120 testable turns in
every Study 011 arm that has the tier. The delivered set overlaps a true window
of the same size by 0.29; 36% of deliveries are older than the cap of 32 turns;
the rotation reaches all 120 reachable episodes.

Three distinct rules carry the name, and only the third is a window:

| Path | Cap | Orders by | Where it ran |
|---|---:|---|---|
| `StmRetrievalEngine._n_retrieve` | 10 | most recently delivered first | Study 009 and earlier live runs |
| `logical_n_key` | 32 | least recently delivered first | Corrected Tier 6, Studies 010 and 011 |
| `episodic._context._recency_window` | 32 | the last N in conversation order | The extracted library; EC-002, CC-003, CC-005 |

**Corrected readings.**

- `PAPER_001.md` §6.2 and the closing summary describe the surviving component.
  That description is accurate about the library. §5.2.4 is added to record that
  the live arc ran a different rule under the same name.
- Study 011's registered prediction 4, "Arm A ≈ Study 009's Arm S", is
  **withdrawn as unscorable** rather than scored as near. The two arms differ in
  ordering rule and in cap.
- EC-002 and IC-001 are **not the same contrast on two corpora**. EC-002 packs K
  against the library's genuine window; IC-001 packs it against the rotation.
  Each is internally valid and EC-002's 152 gains with zero losses stands as a
  statement about the library.

**Unchanged.** Every contrast in which both arms carry the tier, which includes
Study 011's B1 verdict (A 8.0, B 7.5, C 7.0, D 8.0; the packing correction is
not adopted), every delivery and packing number, and every gate result. Study
009's 3.0-point S-vs-L contrast is **not re-read here**; this entry records that
the mechanism is not the one its report names.

Nothing here establishes what a correctly-implemented recency window would
score, in either direction.

Artifacts:
`experiments/study_011/analysis/n_tier_characterization.json` and
`experiments/study_011/amendments/AMENDMENT_002_n_tier_is_not_a_recency_window.md`.
