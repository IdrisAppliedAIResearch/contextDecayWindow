# TC-001 Report — the flat arm wins on delivery, decisively

**Pre-registration:** `TC_001_PRE_REGISTRATION.md`, commit
`4c561e919f9a397dfbad150f529e753d4feda05e`, SHA-256
`5a7b437e14ba8e3dc04d75a9483975bf4d052c66ee0c2005360824a1e747b035`
**Execution commit:** `c2d3fef96a88d4466bb13004b4149705bcca4751`
**Standing:** `REGISTERED-OFFLINE` — bars locked first, zero generative calls,
replayable against a retained embedding cache, on a corpus already observed.
Capped as characterization; **not** confirmation.
**Disposition:** **D3 — `FLAT_WINS`**
**Date:** August 22, 2026
**Artifacts:** `runs/tc001/g0/`, `runs/tc001/run/`, `runs/tc001/diagnostics/`,
`artifacts/tc001/preflight/`

---

## 1. The verdict

Over 868 LoCoMo development questions at a 16,000-character budget, with the
candidate set, the vectors, the renderer, the packer, the drop policy and the
budget held identical, the flat cosine ranking delivered a question's complete
evidence **749 times against the tiered stack's 314**.

| | `A_FLAT` | `A_TIERED` |
|---|---:|---:|
| Complete evidence delivered | **749 / 868 (86.3%)** | 314 / 868 (36.2%) |
| Gains for the tiered arm | — | 8 |
| Losses | — | 443 |
| Net | — | **−435** |
| Discordant pairs | 451 | |
| One-sided exact binomial, flat direction | **6.98 × 10⁻¹²⁰** | |

Registered bar: D3 requires `net ≤ −4` and `p₋ ≤ 0.01`. Both are met by a very
wide margin. The registered null band is 4 questions; the observed margin is 435.

**This is the arc's root question answered in the direction the arc was built to
be able to answer.** §0 of the registration set it up as a real question rather
than a formality, and the answer is that on this corpus, at this budget, the
tiered architecture does not earn its place on delivery.

## 2. It is not one corpus slice, one budget or one endpoint

Every cut registered in §4 runs the same way. Nothing here was chosen after the
fact; all of it was named in the registration before the run.

**All four conversations, all five categories.**

| Conversation | Flat | Tiered | Gains | Losses | n |
|---|---:|---:|---:|---:|---:|
| `conv-41` | 167 | 84 | 1 | 84 | 193 |
| `conv-42` | 218 | 77 | 3 | 144 | 258 |
| `conv-47` | 168 | 91 | 3 | 80 | 189 |
| `conv-48` | 196 | 62 | 1 | 135 | 228 |

| LoCoMo category | Flat | Tiered | Gains | Losses | n |
|---|---:|---:|---:|---:|---:|
| 1 | 70 | 27 | 2 | 45 | 107 |
| 2 | 130 | 66 | 2 | 66 | 143 |
| 3 | 24 | 16 | 2 | 10 | 42 |
| 4 | 352 | 134 | 2 | 220 | 386 |
| 5 | 173 | 71 | 0 | 102 | 190 |

**Any-evidence, the registered secondary endpoint:** 803 against 381, 8 gains,
430 losses, p = 4.52 × 10⁻¹¹⁶.

**The 32,000-character secondary budget:** 810 against 633, 7 gains, 184 losses,
p = 5.45 × 10⁻⁴⁶. The gap narrows as the budget loosens — from 435 to 177 — which
is what Preflight predicted from the two arms' Jaccard overlap rising from 0.215
to 0.588. It does not close, and it does not change direction.

**The registered robustness check** (§8, flat arm charged the missing 18
characters so both arms pay the same block wrapper) reproduces the primary
**exactly**: same 749/314, same 8/443, same disposition. The flat arm's delivered
characters do fall — p50 15,969 to 15,954 — so the check ran; the endpoint simply
does not move at that scale, as §6.1's band predicted.

## 3. Where it came from

Both arms deliver almost the same *amount*. At 16,000 characters the flat arm
delivers p50 54 episodes in 15,969 characters and the tiered arm p50 54 in
15,961. The difference is entirely in *which* 54.

**The tiered arm's budget goes to a query-independent window.** The recency tier
takes 32 of 32 on every one of the 871 questions and **61% of the delivered
characters**. What is left holds p50 22 K episodes and, on 722 of 871 questions,
**nothing at all from the coverage selector**.

**The evidence was not hard to find.** Among the 443 losses, the *worst*-ranked
evidence episode sits at cosine rank p50 **3**, p75 12, and never below 59 — well
inside the ~54 episodes the flat arm delivers. On the median loss the tiered arm
delivered **zero** of the question's evidence while holding 22 K episodes.

**The eight gains say the same thing from the other side.** Their evidence sat at
flat-order ranks 90 to 227 — far outside the flat arm's reach — and was picked up
by the recency tier on 4 of the 8. That is the same shape NF-003 recorded and the
registration pre-specified the cut for: the rescues live deep in the ranking, and
there are eight of them against 443 losses.

**What the coverage selector contributed.** Of the 381 questions where the tiered
arm delivered any evidence, the carrying tier was K alone on 274 and recency
alone on 92. **Coverage was involved in 8 and was the sole carrier on 3.** It is
also the component `PAPER_002.md` §10 measures at 81% of selection latency, and
Preflight measured the whole tiered path at about 6.5× the flat path per query.

## 4. A mechanism-identity finding the run surfaced

**`DESCRIPTIVE`.** Written after the verdict existed, carries no bar and no arm:
`runs/tc001/diagnostics/tc001_k_tier_order.json`.

`build_context` builds its K tier as a list comprehension over the store:

```python
k_hits = [e for e in episodes if relevance_by_id[e["id"]] >= config.k_threshold]
```

The filter is by similarity. **The ordering is not** — it is the store's own
order. Under a binding budget the packer therefore admits the *earliest*
qualifying episodes, not the most relevant ones.

Measured on all 871 questions, 827 of which have enough delivered K episodes to
separate the two predictions:

| | Overlap with what the tier delivered |
|---|---:|
| First *n* qualifying episodes in conversation order | mean **0.976**, p50 1.000 |
| Top *n* qualifying episodes by cosine | mean 0.328, p50 0.269 |

**824 of 827 questions match conversation order better. Zero match relevance
order better.** And the sharpest consequence: the highest-cosine qualifying
episode that the K tier *drops* has median relevance rank **1**. On more than
half of these questions the single most relevant above-threshold candidate in the
entire store is not delivered.

**Preflight Part 1 did not catch this, and should have.** Its name-to-behavior
check confirmed *which* candidates each tier holds — the recency window really is
the last N, the pool really is the full store, the K threshold really does fire —
and never asked *in what order each tier offers them*. That is the same class of
gap as the N-tier mislabel this programme spent eleven studies not noticing, and
it is recorded here rather than left out, per `PREFLIGHT.md`'s scope note. It does
not change the verdict: TC-001 measured the shipped mechanism faithfully, and this
is what the shipped mechanism is.

## 5. What this does not establish

Restated from §9 of the registration, unchanged by the result.

- **Nothing about answers.** Availability is not a verdict. LV-001 measured 16 of
  16 offline availability against 1.5 of 8 live. A 435-question delivery margin
  is a delivery margin. The live evaluation this endpoint requires is TC-006's,
  and TC-006's own first task is establishing whether its instrument can resolve
  a margin at all.
- **Nothing that authorizes deleting the tiers.** A delivery result on one corpus
  at one budget is not a design decision. Two things in particular argue for
  caution: LoCoMo asks questions about a whole finished conversation, so a
  recency window is close to worthless here **by construction** — its 61% budget
  share buys almost nothing on this corpus and might buy a great deal on a live
  continuing conversation, which is the setting the tier was built for. And §4's
  finding means the K tier was never tested at its best.
- **Nothing about which tier is responsible.** §3 and §4 are descriptive.
  Allocation is TC-003's question and it is now sharper, not answered.
- **Nothing that transfers.** Four conversations of one dialogue style. TC-002
  owns transfer.
- **No confirmation.** The corpus is spent; the standing is capped.

## 6. Preflight, as it actually went

| # | Outcome |
|---|---|
| `PF1` | Pass. 2,247 cache hits, 0 misses; dataset, cache and every source file hashed in the run header |
| `PF2` | Pass as scoped, **incomplete as needed**. Tier membership verified; tier *ordering* not asked. §4 |
| `PF3` | Pass. G0 committed at `c2d3fef9` before the run phase opened either arm; the precondition is recorded in the run header and re-checked in code |
| `PF4` | Pass. 451 discordant pairs predicted before the run; 451 observed |
| `PF5` | Pass. Content hashes throughout; delivered episodes read off the payload by the renderer's own turn attribute |
| `PF6` | Pass. All 882 committed development rows reproduced by digest, all eight headline blocks equal |
| `PF7` | Not applicable and demonstrated so: neither path has feedback. The constant-output check that could fail did not |
| `PF8` | Not applicable: full-population replay, no sampling |
| `PF9` | Both named residuals stand. Evidence present is not evidence used; a hit says nothing about what surrounds it |
| `PF10` | Stated in the registration and restated in §5 |

The `PF4` prediction is worth one more line. The reachability probe was run
before the bars were locked and reported 451 discordant pairs with the direction
withheld. The run found 451 discordant pairs. The probe measured exactly what it
claimed to and nothing more.

## 7. Rule 4 — the dependency re-read

TC-001 has reported, so `TC_ARC_ROADMAP.md` Rule 4 fires: every other study's
dependency line is re-read from the file, and the re-read is logged in
`TC_ARC_DEPENDENCY_LOG.md` with an explicit per-study verdict, **before the next
study is registered**. That log is updated in the same commit as this report.

The short version, which the log states properly: **nothing is blocked.** No TC
study depends on TC-001's verdict, by design — Rule 2 forbids a dependency that
names a stage. TC-003 in particular is not blocked and is now more interesting:
if allocation rather than the tiers themselves is the cause, §3 and §4 are where
that case would start.
