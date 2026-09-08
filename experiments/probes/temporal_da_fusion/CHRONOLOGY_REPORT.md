# Same retrieval, recency removed, chronological reader probe

Exploratory, September 6, 2026. Plan c9158936; code9ea35762; input gate5c6d3306; calibration618b85ab. Native thinking off; one fresh seed per arm;16 fixed questions;48 measurement calls plus two arithmetic calibration calls. No original study scores or deployed defaults changed.

**Chronological ordering without recency improves the before-question score from5/12 to8/12 in this sample: three gains, zero losses. Removing recency alone leaves correctness at5/12.** All eight evidence-complete before cases are correct under chronological presentation; all four remaining misses lack complete required evidence. This is a small one-seed probe, not an established100% conditional accuracy rate.

The three repairs are Harbor-113 (annex/workshop → studio), Orchard-657 (depot → hangar), and Orchard-219 (office → hangar). The exact source contents and retrieval identities did not change. The four latest/absence guards stay4/4 in every arm.

Recommendation: carry this no-recency chronological presentation as the candidate for a larger paired reader check before further fusion tuning. The evidence supports prioritizing that check; it does not yet justify production adoption or a general recency-removal claim.

All192 source contexts were checked offline. ORIGINAL exactly reproduces C1; NO_RECENT removes the additive32 exchanges; CHRONO_NO_RECENT sorts the same selected retrieved records oldest to newest after removal. No replacement records or extra retrieval were introduced. The empty recent-context marker remains, without any recent exchanges.

## Final-answer results

| Sample | Original | No recent | No recent, chronological |
|---|---:|---:|---:|
| primary | 5/12 | 5/12 | 8/12 |
| latest | 2/2 | 2/2 | 2/2 |
| absent | 2/2 | 2/2 | 2/2 |

Pairs separate removal from ordering; chronological-with-recency was not tested.

- primary, ORIGINAL→NO_RECENT: 0 gains, 0 losses.
- primary, NO_RECENT→CHRONO_NO_RECENT: 3 gains, 0 losses.
- latest, ORIGINAL→NO_RECENT: 0 gains, 0 losses.
- latest, NO_RECENT→CHRONO_NO_RECENT: 0 gains, 0 losses.
- absent, ORIGINAL→NO_RECENT: 0 gains, 0 losses.
- absent, NO_RECENT→CHRONO_NO_RECENT: 0 gains, 0 losses.

## Size and runtime

| Arm | Median context chars, all192 | Median prompt tokens, sample | Measurement seconds |
|---|---:|---:|---:|
| ORIGINAL | 57,331 | 11,923 | 65.04 |
| NO_RECENT | 31,686 | 6,794 | 38.19 |
| CHRONO_NO_RECENT | 31,686 | 6,794 | 38.14 |

All full prompts fit the fixed32768 context plus16384 output allowance. Every measurement completed with EOS, nonempty final and no native thinking block. Native-off baseline prompts match the saved Study E native template on16/16, and two calibration outputs match exactly.

## Every sampled question

| Question | Gold | Original | No recent | Chronological | Evidence complete |
|---|---|---|---|---|---|
| What was the delivery location for "Harbor-292" immediately before "Harbor-292 review"? | hangar | The hangar ✓ | The hangar ✓ | hangar ✓ | yes |
| What was the delivery location for "Harbor-485" immediately before "Harbor-485 review"? | office | The hangar ✗ | The workshop ✗ | workshop ✗ | no |
| What was the delivery location for "Harbor-113" immediately before "Harbor-113 review"? | studio | The annex ✗ | The workshop ✗ | studio ✓ | yes |
| What was the delivery location for "Orchard-186" immediately before "Orchard-186 review"? | hangar | The hangar ✓ | The hangar ✓ | hangar ✓ | yes |
| What was the delivery location for "Orchard-657" immediately before "Orchard-657 review"? | hangar | The depot ✗ | depot ✗ | hangar ✓ | yes |
| What was the delivery location for "Orchard-219" immediately before "Orchard-219 review"? | hangar | The office ✗ | office ✗ | hangar ✓ | yes |
| What was the delivery location for "Meadow-637" immediately before "Meadow-637 review"? | depot | The depot ✓ | depot ✓ | depot ✓ | yes |
| What was the delivery location for "Meadow-792" immediately before "Meadow-792 review"? | annex | The annex ✓ | The annex ✓ | annex ✓ | yes |
| What was the delivery location for "Meadow-228" immediately before "Meadow-228 review"? | warehouse | The studio ✗ | The studio ✗ | studio ✗ | no |
| What was the delivery location for "Riverside-324" immediately before "Riverside-324 review"? | annex | The office ✗ | The office ✗ | office ✗ | no |
| What was the delivery location for "Riverside-481" immediately before "Riverside-481 review"? | laboratory | The workshop ✗ | The annex ✗ | hangar ✗ | no |
| What was the delivery location for "Riverside-755" immediately before "Riverside-755 review"? | annex | The annex ✓ | The annex ✓ | annex ✓ | yes |
| What is the latest delivery location for "Cedar-443"? | warehouse | warehouse ✓ | warehouse ✓ | warehouse ✓ | yes |
| What is the latest delivery location for "Cedar-967"? | office | office ✓ | office ✓ | office ✓ | yes |
| What was the delivery location for "Summit-519" immediately before "Summit-519 review"? | I don't know | I don't know. ✓ | I don't know. ✓ | I don't know. ✓ | not applicable |
| What was the delivery location for "Summit-899" immediately before "Summit-899 review"? | I don't know | I don't know. ✓ | I don't know. ✓ | I don't know. ✓ | not applicable |

## Interpretation limits

The sample uses the first three content ids in each of four before conditions and the first two latest/absence ids, without filtering by correctness or completeness. It is16 exposed synthetic questions, not a heldout population estimate. One seed does not characterize reader variance. Four guards are too few to establish safety. The comparison concerns the C1 baseline, not the fusion variants.

Native thinking was kept off consistently under the standing test rule. These results cannot be compared causally with the earlier thinking-on probe, which selected failures and changed the native system prefix. Availability is identical across these presentation arms; final-answer changes are reader outcomes under a joint input intervention, not improved retrieval.

Canonical final answers are scored under the frozen Study E grammar. Reasoning-only output is not awarded credit. Raw responses, per-item scores, gates, selection and all transformed contexts are retained in chronology_artifacts. No human or independent-rater audit is claimed.

The explicit failed-input-gate fault-injection check was executed during closeout, after reader calls. The actual input and calibration gates were committed and enforced before calls; this is a timing deviation from the planned preflight fixture, not retroactive proof that the fixture ran before measurement. See negative_gate_fixture.json.

Original study registrations, answers, source data, retrieval code and production defaults remain unchanged. This exploratory probe tests the user-requested presentation without a new success disposition.
