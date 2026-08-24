# TC-001B Report — removing recency is not enough, and the ordering is why

**Pre-registration:** `TC_001B_PRE_REGISTRATION.md`, commit
`455ce2df65ec0ee56be0a57728542e9eaf9adc59`, SHA-256
`146205a7c58f569fccbbcaa8cdc26a697758ec5404316f09a4324c1728e6cb16`
**Escalated from:** `amendments/AMENDMENT_001_dual_arm_escalation.md`
**Execution commit:** `323aa2e70cc753aa73ba8f566fe60c66fdc302ab`
**Standing:** `REGISTERED-OFFLINE` — bars locked first, zero generative calls,
replayable against a retained embedding cache, on a corpus already observed,
with arms chosen after TC-001's result was known. Capped as characterization;
**not** confirmation.
**Disposition (C1, the registered headline):** **D3 — `FLAT_WINS`**
**Date:** August 22, 2026
**Artifacts:** `runs/tc001b/g0/`, `runs/tc001b/run/`, `artifacts/tc001b/preflight/`

---

## 1. The verdict

The author's question was whether the tiered architecture earns its place once
the recency window — built for a live conversation, and near-worthless on a
finished transcript — is taken out of it.

**It does not, but the reason is not the tier that was removed.**

| Contrast | | Delivered complete evidence | gains / losses | net | *p* | Disposition |
|---|---|---:|---:|---:|---:|---|
| **C1** | `A_DUAL` vs `A_FLAT` | **472** vs **749** | 14 / 291 | **−277** | 8.23 × 10⁻⁶⁹ | **D3 `FLAT_WINS`** |
| **C2** | `A_DUAL` vs `A_TIERED` | 472 vs 314 | 218 / 60 | **+158** | 1.54 × 10⁻²² | **D1 `DUAL_WINS`** |
| **C3** | `A_DUAL_RANKED` vs `A_FLAT` | **748** vs **749** | 1 / 2 | −1 | — | `DESCRIPTIVE`, no bar |
| **C4** | `A_DUAL_RANKED` vs `A_DUAL` | 748 vs 472 | 289 / 13 | **+276** | 2.76 × 10⁻⁶⁹ | **D1 `RANKED_WINS`** |

868 questions, 16,000 characters, band 4, α = 0.0025 (Bonferroni over four).

**TC-001's 435-question deficit decomposes, and almost exactly:**

```
recency tier              158   (C2)
K delivered in store order 276   (C4)
                          ----
                          434    against an observed 435
```

Removing the recency tier is worth 158 questions and leaves the tiered stack 277
behind the flat arm. Offering the K tier best-first instead of in store order is
worth **276** — nearly twice as much — and once both are done, `A_DUAL_RANKED`
lands within one question of `A_FLAT`.

## 2. What C3 does and does not say

`A_DUAL_RANKED` delivered complete evidence on 748 questions; `A_FLAT` on 749.
They agree on **865 of 868**. Of the three they disagree on, one goes to the
ranked arm and two to the flat arm.

**No disposition is attached to this, and none may be read into it.** PF4
measured C3's discordant count *before the bars were locked, with the direction
withheld*, found three, and registered the consequence: three discordant pairs
put the best attainable one-sided *p* at 0.125, above both α and the signal α,
and `|net| ≤ 3 < B = 4` leaves `D0a` as the only branch it could ever reach. A
bar there would have been unreachable by construction — DMR-001's defect, with
the lesson already in the repository. So C3 was registered `DESCRIPTIVE`, and
`verdict()` refuses to apply the table to it rather than trusting the document
to be obeyed.

The prediction held exactly: **PF4 said three discordant pairs, the run found
three.**

What can be said without a bar: on this corpus, at this budget, a K threshold
plus a cluster-diversity coverage selector, with the K tier ordered by
relevance, delivers what a plain cosine ranking delivers. It costs **92–97 ms
per question against 14** to do it.

## 3. It is not one cut

Every breakdown registered in §4 runs the same way, and none was chosen after
the fact.

**All four conversations, all five categories.** C1 is `FLAT_WINS` on every one;
C2 and C4 are `DUAL_WINS` and `RANKED_WINS` on every one; C3 is within ±1
everywhere.

| Conversation | C1 net | C2 net | C3 net | C4 net |
|---|---:|---:|---:|---:|
| `conv-41` (n=193) | −44 | +39 | +1 | +45 |
| `conv-42` (n=258) | −93 | +48 | −1 | +92 |
| `conv-47` (n=189) | −53 | +24 | −1 | +52 |
| `conv-48` (n=228) | −87 | +47 | 0 | +87 |

| Category | C1 net | C2 net | C3 net | C4 net |
|---|---:|---:|---:|---:|
| 1 (n=107) | −26 | +17 | +1 | +27 |
| 2 (n=143) | −22 | +42 | −1 | +21 |
| 3 (n=42) | −6 | +2 | 0 | +6 |
| 4 (n=386) | −156 | +62 | −1 | +155 |
| 5 (n=190) | −67 | +35 | 0 | +67 |

**The any-evidence secondary (n=871):** C1 528 vs 803 (net −275), C2 528 vs 381
(+147), C3 801 vs 803 (−2), C4 801 vs 528 (+273).

**The 32,000-character secondary:** C1 694 vs 810 (net −116), C2 694 vs 633
(+61), C3 811 vs 810 (**+1**), C4 811 vs 694 (+117). Every gap narrows as the
budget loosens and none closes or reverses — except C3, which was already closed
and crosses zero by one question.

**The registered robustness check** (§8.2, `A_DUAL` charged the 18 characters
`A_TIERED` pays for a non-empty `recent_context` block) reproduces C2 **exactly**:
same 472/314, same 218/60, same disposition. `A_DUAL`'s delivered characters do
fall — p50 15,965 → 15,946 — so the check ran; the endpoint does not move at
that scale, as §6.1's band predicted.

C1, C3 and C4 needed no such check: `A_DUAL` and `A_DUAL_RANKED` render an empty
`recent_context` block exactly as `A_FLAT` does, so **the primary contrast is
wrapper-symmetric at 52 characters against 52.** TC-001 could not say that about
its own primary.

## 4. Where it came from

**The evidence was never hard to find, and that is the whole finding.** The
discordant cut was pre-specified in §4 before the split was known:

| | n | Worst-ranked evidence, flat cosine rank |
|---|---:|---|
| C1 losses (`A_FLAT` delivers, `A_DUAL` does not) | 291 | p50 **3**, p25 1, p75 12, max 57 |
| C1 gains | 14 | p50 75, p25 65, max 227 |
| C4 gains (ranking the K tier rescues it) | 289 | p50 **3**, p25 1, p75 12, max 57 |
| C4 losses | 13 | p50 74, p25 65, max 227 |

C4's gains are C1's losses, question for question and rank for rank. The
store-ordered K tier was discarding evidence sitting at **median cosine rank 3**
— inside the ~54 episodes every arm delivers — and the moment the tier is asked
to offer its best candidates first, that evidence arrives.

TC-001 recorded the same shape for the shipped arm: 443 losses at worst-evidence
rank p50 3, max 59. The defect was never about which tier held the budget. It
was about which member of the tier got spent.

**The coverage selector, no longer starved, still barely delivers.** With
recency gone, its mean delivered episodes rise from 1.39 to 8.37 and the
questions where it delivers nothing fall from 722 of 871 to 571. What that buys:

| | `A_TIERED` | `A_DUAL` / `A_DUAL_RANKED` |
|---|---:|---:|
| Coverage was the sole carrier of a question's evidence | 3 | **12** |
| Coverage was involved at all | 8 | 22 |

Twelve questions out of 871, from the component `PAPER_002.md` §10 measures at
81% of selection latency and rising.

**Removing a tier bought no latency back.** `A_DUAL` runs at p50 91.6–97.0 ms
per question and `A_DUAL_RANKED` at 90.9–96.0, against the shipped
`A_TIERED`'s 89.5–102.3 and `A_FLAT`'s 13.4–15.9. The clustering dominates the
path whether or not a recency window sits in front of it.

## 5. What this does not establish

Restated from §9 of the registration, unchanged by the result.

- **The arms were chosen after TC-001's result was known.** Bars were locked
  before any number here existed, which makes this registered rather than
  exploratory — but a registered study built on an observed result is
  characterization. Nothing here is `CONFIRMATORY` and no sealed corpus remains
  to this programme to make it so.
- **Nothing about answers.** Availability is not a verdict. LV-001 measured 16
  of 16 offline availability against 1.5 of 8 live. A 277-question delivery
  margin is a delivery margin. TC-006 owns the reader, and its own first task is
  establishing whether its instrument can resolve a margin at all.
- **Nothing that authorizes changing a default.** `recency_window_n` stays at
  32. C2 says the tier cost 158 questions *on a corpus with no live
  continuation*, which cannot measure what the tier was built to do. This is the
  same caveat TC-001 gave, and removing the tier does not weaken it — it is
  precisely why C2's number is not a deployment decision.
- **Nothing about the coverage selector's cost.** §4's delivery numbers are
  delivery numbers. TC-005 owns the cost side.
- **Nothing that transfers.** Four conversations of one dialogue style, 156
  distinct episodes. TC-002 owns transfer.
- **C3 has no bar.** Its 748-against-749 is a description, not a verdict of
  equivalence. An equivalence claim needs an equivalence test with a registered
  margin, and this study registered none.

## 6. Preflight, as it actually went

| # | Outcome |
|---|---|
| `PF1` | Pass. 2,247 cache hits, 0 misses; dataset, cache and every source file hashed in the run header |
| `PF2` | **Pass, including the check TC-001 omitted.** `compose_context(k_order="store")` equals `build_context` on 3,484 of 3,484 comparisons. `A_DUAL`'s delivered K prefix is in store order on 865 of 865 evaluable questions and in relevance order on 1; `A_DUAL_RANKED`'s is in relevance order on 864 of 865 |
| `PF3` | Pass. G0 committed at `323aa2e7` before the run phase opened any arm; re-checked in code |
| `PF4` | **Pass, and it changed the design.** C1 305, C2 278, C4 302 discordant pairs — all reachable and failable. C3 had 3, so C3 was registered with no bar before the run. Predicted 3, observed 3 |
| `PF5` | Pass. Inherited from TC-001 unchanged; delivered episodes read off the payload by the renderer's own turn attribute |
| `PF6` | Pass. G0 reproduces TC-001's committed primary and secondary tables on all four rows, against both the recomputed values and the committed artifact |
| `PF7` | Not applicable and demonstrated so: no path has feedback |
| `PF8` | Not applicable: full-population replay over all 868 evaluable questions |
| `PF9` | Three residuals stand. Evidence present is not evidence used; a hit says nothing about what surrounds it; and the identity gate certifies equality under the shipped K order, not that the ranked variant is the *right* counterfactual |
| `PF10` | Stated in the registration and restated in §5 |

**One thing worth stating plainly.** TC-001's report recorded a gap in its own
Preflight — it checked *which* candidates each tier holds and never *in what
order each tier offers them* — and that gap is why the store-order finding
arrived as a post-hoc diagnostic instead of a registered arm. This study asked
the ordering question in Part 1, before its bars were locked. The consequence is
C4: a 276-question effect measured against a bar, rather than a description
written after a verdict.

## 7. Rule 4 — the dependency re-read

TC-001B has reported, so `TC_ARC_ROADMAP.md` Rule 4 fires: every other study's
dependency line is re-read from the file and logged in
`TC_ARC_DEPENDENCY_LOG.md` with an explicit per-study verdict, **before the next
study is registered**. That log is updated in the same commit as this report.

**Nothing is blocked.** No TC study depends on this one's verdict — Rule 2
forbids a dependency that names a stage — and a verdict cannot block anything: a
`BLOCKED` entry is valid only when it names a missing artifact.

Two studies should be read differently now, which is not the same as being
blocked. **TC-003** asked whether allocation explains TC-001's gap; C2 and C4
say allocation explains 158 of it and *ordering within a tier* explains 276, so
TC-003's reserved-floors proposal now has a measured competitor it did not have
yesterday. **TC-005**'s latency target belongs to a component that carries a
question's evidence alone on 12 of 871 even when nothing is starving it.
