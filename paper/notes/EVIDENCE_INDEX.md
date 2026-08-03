# PAPER-001 Pass 0 — Evidence Index and Spec Reconciliation

Working document. Not part of the paper. Records what was verified against
committed artifacts before drafting, and every place the authoring spec
disagrees with the repository.

Repository state: branch `paper-001`, from `main` at `8a8a6229`.

**Post-draft update, RD-001 (2026-08-03).** The full 119-rank ordering is now
committed at `artifacts/rd001/full_rank_inventory.csv`. The proposed rarity
correlation remains not identifiable: the prior audit scores only 6 of 76
fact-bearing episodes across three variants. PAPER-001 is revised on the
separate `e006/rarity-diagnostic` branch.

---

## 1. Spec-versus-artifact discrepancies

These are resolved in favour of the committed artifact in every case. Each is
carried into the paper as written here, not as the spec states it.

### D1 — Oracle cosine ranks: spec says 14, 21, 22, 86, 112; the corrected value is 14, **20**, 22, 86, 112

The spec (§1.1 link 7) inherits DR-002's published table. `ERRATA.md`
"DR-002 Cosine Rank Under the Committed Embedding Call (2026-08-01)" corrects
step 11, turn 118, from rank 21 to rank 20, and states the oracle ranks read
"14, 20, 22, 86, 112". Confirmed in
`artifacts/e005/dr_002/generality_batched.json`:

```
"selection_rank_corrections": [{"measured_rank": 20, "published_rank": 21,
                                "source_turn": 118, "step": 11}]
```

`worst_fact_bearing_rank_unchanged: true`, `generality_conclusion_unchanged: true`.
The verdict and the rank-86 rule are unaffected. **Paper uses 14, 20, 22, 86, 112
and cites the erratum.**

### D2 — AR-001 has two sets, and "the oracle" is the second one

The spec's §1.1 link 5 quotes both AR-001 numbers correctly but does not
distinguish the sets, and link 7 then attaches ranks to "the oracle" without
saying which.

| Set | Facts | Chars | Turns |
|---|---:|---:|---|
| Exact threshold optimum | 14/17 | 5,058 | 90, 112, 113, **115**, 118 |
| Greedy | 15/17 | 5,455 | 90, 112, 113, **116**, 118 |

Source: `artifacts/ar_001/AR_001_report.md` §"Exact Threshold Set" (the 14/17
set) and §"Result" (greedy 15/17 at 5,455).

E005's A4 arm, DR-002's "oracle overlap", and DX-001's "oracle episode" all
refer to the **greedy 15/17 set**. Confirmed by the column headers of
`artifacts/e005/oracle_overlap.csv`: `turn_90, turn_112, turn_113, turn_116,
turn_118` — turn 116, not turn 115.

That set's ranks are 112, 22, 14, 86, 20 respectively, which is exactly
DR-002's list. **Paper states which set it means every time it says "oracle".**

### D3 — The pool ablation is one frozen configuration, not the sweep

Spec §1.2 table: "34 → 119 gives 5/17 → 12/17 and 2/4 → 4/4". True, but only of
the frozen configuration `A3_l0.1_r0.0_k16` (`DR_002_report.md` §1). The
best-of-sweep figure per pool is different and must not be conflated:

| Pool | Frozen A3 config (DR-002 §1) | Best of 146 configs (E005 report) |
|---|---|---|
| 119 | 12/17, 4/4 domains | 13/17 |
| 100 | 9/17, 3/4 | 13/17 |
| 34 | 5/17, 2/4 | 13/17 |

The load-bearing pool claim is the **domain** one, which survives the
distinction: on the deployed 34-episode pool *no* configuration covers four
domains, because art has no representative in the top 34 (DR-002 §2). **Paper
leads with the domain claim and labels the fact counts by which quantity they
are.**

### D4 — DR-002 §3.5 refutes the strong reading of the inversion

The spec's link 7 headline is "the primitive is inverted where it matters
most". DR-002 §3.5 was added specifically to block the stronger claim, and
measures it false: on all eight targeted probes cosine ordering places every
needed item inside rank 2, and the top 4 carry a target item on 8 of 8. Q11,
the single enumeration probe, is the only failure (top-4 hits 0, last needed
item at rank 87).

DR-002 also lists four results the inversion does *not* explain: formation-side
failures upstream of retrieval, Study 003's arithmetically unreachable
promotion route, Study 007 (model used all 10 delivered facts; 7 required facts
absent from the store), bakeoff Tier 3's routing oracle ceiling of 6.09%, and
widened raw STM's 6/6 with no selection filter at all.

**This is not a caveat to bury. The paper states the bounded claim as the
finding: the ordering is anti-correlated at the top for enumeration queries,
and near-optimal for targeted ones.** Overreaching here is the single easiest
way to fail Reviewer C.

### D5 — `ERRATA.md`'s latency table mislabels one column

The ERRATA table under "episodic Selection-Latency Range" is headed
"Median build_context" and gives 3.8 ms / 76 µs at 50 candidates. The committed
`artifacts/cc005/latency_curve.csv` — the `build_context` medians — reads
4.2021 ms / 84.042 µs at 50. The 3.7803 ms / ~76 µs figure is the
`stage_total_ms` column of `artifacts/cc005/latency_components.csv`, the sum of
the timed stages, which excludes the rest of the call.

The headline numbers are unaffected: 189.99 ms at 1,000 candidates
(`latency_curve.csv`, and `growth_measurement.json` `latency.measured_max_ms`),
exponent 1.252, clustering share 0.807.

**Paper uses `latency_curve.csv` for F6 and does not reproduce the ERRATA row.**

**Resolved 2026-08-02.** The `ERRATA.md` entry is corrected: the table now holds
all nine `latency_curve.csv` rows, and the entry carries a dated
correction-to-itself. Tracing it fully turned up two further defects beyond the
column mislabel — the four rows came from two different artifacts, and the "119
(DR-002's maximum)" row was not a CC-005 measurement at all, pairing the
100-candidate median with the 50-candidate per-candidate cost. A claim in the
entry also fell: per-candidate cost is not flat to 119 on CC-005's curve, rising
84.0 → 100.1 µs between 50 and 100 candidates. That flatness is DR-002's, on a
measurement spanning less of the call.

### D6 — "Eleven studies" needs defining

The spec says "eleven studies" (§1.3) and its footer lists Studies 001–010 plus
the bakeoff, ledger, and component work. Studies 001–010 is ten. The paper
states the unit explicitly: **ten numbered studies plus one registered
exploratory bakeoff**, with the diagnostics and component work named separately
rather than folded into a count.

---

## 2. Verified numbers, by paper section

Every row was read from the artifact named. `→` marks a number the paper states
differently from the spec, per §1 above.

### The arc (§5 of the paper)

| Claim | Value | Artifact |
|---|---|---|
| Corrected treatment scores, 002C→009L | 8.5, 11.5, 6.5, 11.0, 9.0, 12.0, 12.0 | `audits/scoring_integrity/corrected_scores/arm_totals.json` |
| Original values, same arms | 13.0, 12.0, 7.0, 11.0, 10.5, 12.0, 12.0 | same |
| Study 001 loses VALIDATED | iterative 9.0→8.0, compaction 3.5→2.5, Bar 2 → FAIL | `ERRATA.md`; `arm_totals.json` |
| Items re-scored / changed | 222 / 19 | `audits/scoring_integrity/audit_report.md`; `ERRATA.md` |
| Residual estimate is extrapolated | 3/26 control disagreements (11.54%) over 143 unreviewed → 16.5, "about 20" | `ERRATA.md` |
| Study 009 null test, same seed | S 9.0 vs L 12.0, gap 3.0 | `arm_totals.json` |
| Topic layer | 52 topics at 120 turns; 12 domains → 2 at 1,000 | `AGENTS.md` digest 002/010 |
| Study 003 promotion | weighted route structurally unreachable; all promotion via bypass | `AGENTS.md` digest 003 |
| Density and rarity on the six hard plants | Density 89th–316th; mean IDF is worse on 5/5 eligible spans, but max IDF improves 2/5 and sum/word improves 1/5; no primary variant | `rarity_signal_feasibility.csv`; `RD_001_RARITY_PROVENANCE_AUDIT.md`; `ERRATA.md` |
| Study 007 | model used 10/10 delivered facts, invented none; 7 required facts absent | `AGENTS.md` digest 007; `README.md` |
| Study 008 | stopped at pre-run gates; no fill cap 1–50 passed jointly | `AGENTS.md` digest 008 |

### The pivot that failed (§5)

| Claim | Value | Artifact |
|---|---|---|
| Bakeoff T1 raw-store reachability | 8/17 at 31,861 exact chars, below the 11/17 formation-era ceiling | `surveys/retrieval_bakeoff/retrieval_bakeoff_report.md` §Outcome, Tier table |
| T3 routing oracle | 6.09%, below the registered 10% build threshold | same, Tier 3 |
| T4A graphs | no configuration cleared advancement; T4B never ran | same, Tier 4 |
| T5 ANN | recall degraded at synthetic scale | same, Tier 5 |
| First clean positive | widened raw STM delivered 6/6 formation-blind facts, model used 5 | same, §Primary Positive Result |
| 8/17 vs 13/17 are different objects | offline single-block content vs live end-to-end answer, different denominators | same, §Reconciling |

### Query representation (§5)

| Claim | Value | Artifact |
|---|---|---|
| E002 at matched 32k budget | baseline 6/17 @ 31,946 → segmentation 10/17 @ 21,761, 3/4 domains | `ERRATA.md` E002 budget interpretation |
| E002 targeted, corrected | 14/16 → **16/16**; KILL unaffected | `ERRATA.md` 2026-08-01; `AMENDMENT_004` |
| E002 verdict | KILL against a locked 14/17 | `RETRIEVAL_MECHANISM_LEDGER.md` F1 |
| E001 attention oracle | cosine 0.120422 → best-found 0.210318 vs K = 0.48; 0/714 rows reached K; 266/384 heads non-sparse | `RETRIEVAL_MECHANISM_LEDGER.md` F2 |
| Q4 cosine correction | 0.16612689 → 0.12042198, both below K | `ERRATA.md` bakeoff Q4 provenance |

### The decomposition (§6 — the core)

| Claim | Value | Artifact |
|---|---|---|
| Achievability, exact | 14/17 in 5,058 chars, 5 episodes, 26,942 headroom | `artifacts/ar_001/AR_001_report.md` |
| Achievability, greedy | 15/17 in 5,455 chars | same |
| 17/17 cost | 7,592 chars | `RETRIEVAL_MECHANISM_LEDGER.md` F1 |
| Domain optima | civil 826, art 3,182, monetary 2,913, marine 824 | `AR_001_report.md` |
| Store coverage | 17/17 present; 76 of 119 episodes carry ≥1 item | same |
| A0 deployed baseline | 6/17, 3/4 domains, 31,946 chars, 8 episodes | `artifacts/e005/E005_report.md` |
| E005 primary | 12/17, 4/4, 16/16 targeted, 31,569 chars, 15 episodes, `A3_l0.1_r0.0_k16` | same |
| Arms | A0 6/17, A1 12/17, A2 13/17, A3 12/17, A4 oracle 15/17 | same |
| A2 is the trap | highest raw count 13/17, monetary 0/4 at every setting, passed no gate | `E005_report.md`; `README.md`; `per_domain_counts.csv` |
| Configs swept | 146 per pool; 0 inference calls; byte-identical rerun PASS | `E005_report.md` §Integrity |
| Greedy optimality | runs at 0.955–0.9996 of its own optimum | `artifacts/e005/optimality_bounds.csv` — **verify before use** |
| Pool ablation, frozen config | 34 → 100 → 119 gives 5/17 → 9/17 → 12/17; 2/4 → 3/4 → 4/4; oracle 1/5 → 0/5 → 4/5 | `DR_002_report.md` §1 |
| Brittleness | dropping the 19 lowest-cosine episodes costs 3 facts, all of art, and all oracle overlap, despite 4/5 oracle episodes surviving | same |
| Top-4 carry zero Q11 facts | ranks 1–4 all fact-barren | `DR_002_report.md` §2; `selection_ranks.csv`; `generality_batched.json` Q11 `top4_hits: 0` |
| Worst fact-bearing rank | 86 (registered rule fires at ≥80) | `DR_002_report.md` §2 |
| Art only past rank 50 | both art contributors at ranks 50 and 86 | `selection_ranks.csv` |
| Q11 last-needed item | rank 87 of 119; first hit rank 5 | `generality_batched.json` |
| Targeted probes | every needed item inside rank 2, all 8 probes | same |
| DX-001 residual | turn 90, rank 112/119, cosine 0.0560, needs 0.225032, shortfall 0.169042 | `artifacts/dx001/DX_001_report.md` |
| DX-001 census | 0 of 146 configurations select it; best rank anywhere 4, never 1 | same |
| M1 refuted | diversity term payable in full at 0 of 15 steps; cluster never entered | same |
| Only 20 of 119 clear the needed bar | so it would have to be a different episode by cosine | same |

### What survives (§7)

| Claim | Value | Artifact |
|---|---|---|
| Graveyard | 11 rows, each with its killing result | `RETRIEVAL_MECHANISM_LEDGER.md` §6 |
| Surviving architecture | append-only verbatim store, recency window, cosine-threshold similarity, set-level coverage selector; 0 inference calls | `episodic/README.md` |
| Extraction equivalence | 132/132 A3 payload SHAs, 3/3 rendered blocks byte-identical | `CC_002_library_extraction.md` T3/T4 |
| Purity | `context()` byte-identical across two processes | CC-002 T7 |
| Suite | 1,007 tests green | `CC_005_report.md` |

### Growth and cost (§7, F6)

| Claim | Value | Artifact |
|---|---|---|
| DX-002 branch | B — an unbudgeted component is climbing | `artifacts/dx002/DX_002_report.md` |
| Runner STM p95 growth | +23,238 chars arm L, +28,701 arm S over final five buckets; record set in last bucket of both | same |
| Runner LTM saturates | 55,135 → 54,268, −867 over the same buckets | same |
| Window over window | arm L STM +33.0%; arm S STM +46.8% | same |
| Smallest detectable slope | 17.20 chars/turn on `arm_l.total` → 17,203 chars of undetectable drift | same |
| Durbin-Watson | 1.83–2.33; residuals autocorrelated, sawtooth series | same |
| Rule pinning | fired 0 of 1,000 turns, constant 15 chars — but disabled before the run, so untested not cleared | same |
| Library replay | p95 +18 chars; −0.024% window over window; 0 of 1,000 turns over budget; saturated | `artifacts/cc003/ge0_growth_gate.json` |
| Library block mean | ~31,840 chars from turn 101 onward | `CC_003_report.md` |
| Truncation is real | 895 of 1,000 turns truncated; max 70 episodes dropped; max `chars_wanted` 65,864 | `ge0_growth_gate.json` |
| Enforcement inert at operating point | E6: 132/132 SHAs, 12/17 · 4/4 · 16/16 @ 31,569 unchanged | `CC_003_report.md` |
| Compact renderer alone insufficient | post-DR-001 max 37,934; still 561 of 1,000 turns over 32,000 | `DX_002_report.md` |
| Latency curve | 50→4.2021 ms, 500→66.36, 1000→189.99 ms | `artifacts/cc005/latency_curve.csv` |
| Exponent | 1.2524 over 50–1,000 (vs DR-002's 0.96 over 20–119) | `growth_measurement.json` |
| Clustering share | 0.374 at 50 → 0.807 at 1,000 | `latency_components.csv` |
| Projection error | ~40 ms projected vs 190 ms measured at 1,000; the projection extended 84× past its last point | `CC_005_report.md`; `ERRATA.md` |
| Disk | 4,743 bytes/turn marginal, 86% embeddings; 4.8 MB at 1,000 turns | `growth_measurement.json` |
| Stated horizon | comfortable to a few thousand episodes; unusable in an interactive loop before 10,000 | `CC_005_report.md` |

### Self-audit (§8)

| Correction | Value | Artifact |
|---|---|---|
| Scoring audit | 222 items re-scored, 19 changed, only VALIDATED verdict removed | `audits/scoring_integrity/` |
| DR-001 rendering | Q13/Q14 were 53,726 / 53,839 chars, 67.9% / 68.2% over budget, not 31,991 "saturated" | `ERRATA.md`; `DR_001_report.md` |
| Probe-order validator | three degradation probes requested facts before they were planted | `scripts/check_probe_fact_order.py` — **verify the count before use** |
| Embedder call shape | cosine agreement 0.999837, largest component difference 0.217, flips 6 of 146 payloads; now a startup assertion | `DX_001_report.md` §preamble; `episodic/README.md` H1 |
| Latency projection | 84× extrapolation, ~5× understatement | `CC_005_report.md` §3 |
| DX-002 near miss | conjunction rule checked only the terminal slope; a block that grew 23,000 chars read as flat | `DX_002_report.md` §The near miss; `DECISION_001_dx002_growth_branch.md` |
| AS-001 | `PRIMACY MECHANISM LIVE` withdrawn post-output; rank 27 first enters at 108,432 chars | `ERRATA.md`; `q4_packing/decisions/DECISION_001_invalidate_branch_d.md` |
| E002 targeted count | gate `preserved == required` was unsatisfiable by construction for any selector | `ERRATA.md` 2026-08-01 |
| MMR submodularity | repository's own unverified claim refuted against Lin & Bilmes (2011) | `ERRATA.md` |
| Tier 6 seal | computed over mixed LF/CRLF; `study.db` never committed | `ERRATA.md` |

### Limitations (§9)

| Item | Value | Artifact |
|---|---|---|
| No error bars anywhere | every comparison single-run, one seed | program-wide; `AGENTS.md` runtime rules |
| External calibration boundary | LongMemEval-S run in EC-001; LoCoMo unrun; substituted evaluator forbids official comparator score | `external/longmemeval/EC_001_REPORT.md` §§1,7 |
| One literal breadth probe | Q11 is the program's only enumeration question; LongMemEval multi-session is an analogue, not an identical task | `DR_002_report.md` §3.5; `EC_001_REPORT.md` §6 |
| AI raters, AI adjudicators | self-consistency 97.47%, control disagreement 11.54% | `audits/scoring_integrity/` — **verify 97.47 before use** |
| Oracle contains prior probe answers | 4 of 5; registered rule is `source_turn < 120` | `artifacts/e005/prior_answer_fraction.csv` — **verify before use** |
| Amendments | 12 in the bakeoff alone, each with a per-amendment "before results?" column | `retrieval_bakeoff_report.md` §Amendment Legitimacy |
| O6 runtime independence unmeasured | one model, one quant, one machine | `CC_005_report.md` §6 |
| Horizon | 1,000 turns says nothing about 10,000 | `DX_002_report.md`, `CC_003_report.md` boundaries |

### EC-001 external calibration

| Measurement | Value | Artifact |
|---|---|---|
| Primary rank result | top four contain no evidence on 69/470 (14.7%); median evidence-session rank 2, p95 23, max 49 | `external/longmemeval/EC_001_REPORT.md` §2; `runs/tier1_001/tier1_summary.json` |
| Tier 1 exact-turn availability | any 79/470 (16.8%); all 20/470 (4.3%) | `EC_001_REPORT.md` §3; `tier1_summary.json` |
| Tier 2, equal quota | 28/140 (20.0%) | `EC_001_REPORT.md` §4; `codex_integrity_score_summary.json` |
| Tier 2, post-stratified | 12.22% | same |
| Exact availability gap | 8/118 available vs 11/118 correct; −2.54 percentage points | `EC_001_REPORT.md` §5; `codex_integrity_score_summary.json` |
| F3 absence detection | 0/500 component signals; reader correct on 17/20 abstention items | `EC_001_REPORT.md` §§4,6 |
| Instrument audit | 358 registered predicate hits; not 358 adjudicated defects | `EC_001_REPORT.md` §8; `instrument_audit.json` |
| Reporting boundary | Codex-substituted integrity only; no official or direct published-system comparison | `AMENDMENT_010_two_hosted_replacements.md`; `EC_001_REPORT.md` §7 |

---

## 3. Verification outcomes

### V1 — Greedy optimality range: spec says 0.955–0.9996; measured 0.9536–0.9996

`optimality_bounds.csv`, 405 of 438 rows computable (all A2 and A3; A1's bound is
not computable, consistent with MMR being non-monotone — see the MMR erratum).

| Arm | Pool | n | min | max |
|---|---|---:|---:|---:|
| A3 | full_eligible_store | 132 | 0.9548 | 0.9994 |
| A3 | cosine_top_100 | 132 | 0.9608 | 0.9996 |
| A3 | deployed_n_union_k | 132 | 0.9536 | 0.9996 |
| A2 | full_eligible_store | 3 | 0.9961 | 0.9996 |
| **All computable** | | **405** | **0.9536** | **0.9996** |

The spec's "0.955" is the primary-pool A3 minimum rounded. **Paper states the
full range (0.9536–0.9996 over 405 configurations) and notes that A1's bound is
not computable.** The argument — that the search, not the objective, is the
limit — is unaffected and arguably strengthened.

### V2 — "4 of 5 oracle episodes are prior probe answers" holds, but not from the file the name suggests

`prior_answer_fraction.csv` does **not** measure this. It records, per
configuration, the fraction of *selected* episodes that are prior probe answers
(e.g. 0.333 for the primary config). It says nothing about the oracle set.

The claim is nonetheless supportable by turn arithmetic. The oracle set is
{90, 112, 113, 116, 118}. The probe turns, from `generality_batched.json`, are
Q1→112, Q2→113, Q4→115, Q5→116, Q6→117, Q7→118, Q8→119, Q10→118, Q11→120. Four
oracle turns — 112, 113, 116, 118 — are probe turns; turn 90 is not.

**Paper states it as derived from the probe-turn map, cites
`generality_batched.json` and `AR_001_report.md`, and does not cite
`prior_answer_fraction.csv` for it.**

### V3 — Probe-order validator: script exists, count not verified

`scripts/check_probe_fact_order.py` is committed. The "three degradation probes
requested facts before they were planted" figure is not traced to a committed
output artifact in this pass. **Demoted: the paper describes the validator and
the class of error it caught without asserting a count**, unless Pass 2 finds
the artifact.

### V4 — Self-consistency 97.47% / control disagreement 11.54%

11.54% is confirmed in `ERRATA.md` and `README.md` as 3 of 26 control-sample
disagreements. 97.47% is not yet traced. **Paper uses 11.54% (sourced) and omits
97.47% unless Pass 2 locates it.**

### V5 — Study 010 exploratory continuation

`AGENTS.md` digest 010 and `README.md` both state: post-stop L beat S 14–12 on
breadth only, targeted tied, scores unaudited, Q13/Q14 violated the budget by
67.9%/68.2%, Bar 3 NOT EVALUABLE. **Paper reports it as unaudited and
budget-noncompliant wherever it appears, or not at all.**

---

## 3b. F1 was not drawable at full resolution at draft time

**No committed artifact contains the cosine rank of all 119 candidate
episodes.** What exists:

| Artifact | Covers |
|---|---|
| `dr_002/selection_ranks.csv` | the 15 *selected* episodes: rank, cosine, chars, fact-bearing, items |
| `dx001/cost_comparison.csv` | the same 15 plus turn 90, each with `cosine_rank` |
| `ar_001/episode_coverage.csv` | all 119 episodes with `fact_count`, domains, items — **but no cosine** |
| `dr_002/generality_batched.json` | Q11 structural facts: top-4 hits 0, first hit rank 5, last needed rank 87 |

Joining `episode_coverage.csv` to a cosine ordering would require the query
vector. Recomputing it requires the carried embedder
(`src/analysis/dr002_generality_check.py` takes `--embedding-model`), and no
`.gguf` is present — `*.gguf` and `models/` are gitignored. The source store
`study.db` is present locally but untracked, and `*.db` is gitignored too.

The turn-120 episode vector inside `study.db` is **not** a substitute: it was
embedded at store time as a single item, and DX-001 established that this
embedder returns a materially different vector for the same text embedded alone
versus in E005's nine-query batch — the exact hazard `episodic` now asserts
against at startup. Using it would reproduce the wrong ordering.

**Resolution.** F1 is drawn from committed data only, at the resolution that
data supports: the 16 episodes whose ranks are committed, positioned on a
1–119 axis, with the top-4-carry-zero region, the first-hit and last-needed
ranks, the oracle marks, and the pool cuts at 34 and 100 drawn as committed
structural facts. The caption states what is plotted and what is not, and names
the experiment that would produce the full curve. This costs the figure some
visual force and is the correct trade.

**RD-001 update.** The exact carried embedder and hash-anchored source store
were available locally. RD-001 replayed E005's nine-query call, recovered all
119 ranks, and reproduced the 16 prior checks with only the known rank-21 to
rank-20 correction. Figure 3 now reads
`artifacts/rd001/full_rank_inventory.csv`. The rank gap is closed; the rarity
measurement is not, because only six fact-bearing episodes have prior rarity
scores and no primary of the three variants was registered.

**Rarity-variant provenance correction.** The historical audit did not choose a
primary formula and did not state the later categorical conclusion "IDF worse."
That sentence first appeared in the retrieval ledger. It matches
`rarity_mean` only: 5/5 eligible hard-plant spans rank worse than density,
versus 3/5 for `rarity_max` and 4/5 for `rarity_sum_per_word`. The family-level
negative claim is withdrawn in `ERRATA.md`; no historical artifact or score is
changed.

---

## 4. Figure data sources

---

## 4. Figure data sources

| Fig | Data | Path |
|---|---|---|
| F1 | All 119 recovered ranks × Q11 facts; selected and oracle marks; pool cuts at 34/100; first-hit and last-needed annotations | `rd001/full_rank_inventory.csv`, `e005/raw/q11_selection.jsonl`, `dx001/cost_comparison.csv`, `dr_002/generality_batched.json` |
| F2 | chars vs facts for A0 / E005 primary / AR-001 exact and greedy | `e005_results.json`, `a0_baseline.json`, `ar_001/achievability.json` |
| F3 | pool 34/100/119 × facts, domains, oracle overlap, for the frozen config | `DR_002_report.md` §1 (values also in `pool_secondaries.csv` per config) |
| F4 | corrected vs original treatment score by study | `arm_totals.json` |
| F5 | A0/A1/A2/A3/A4 × facts, domains, per-domain, targeted | `configuration_sweep.csv`, `per_domain_counts.csv`, `a0_baseline.json`, `ar_001/achievability.json` |
| F6 | left: DX-002 runner buckets vs CC-003 library buckets; right: latency curve + withdrawn projection | `dx002/dx002_results.json`, `cc003/ge0_growth_gate.json`, `cc005/latency_curve.csv` |

Do **not** use `dr_002_results.json` `timings` for F6: those are the
greedy-loop-only figures (1.28 ms at pool 119) that DR-002 §3 supersedes with a
4.756 ms total after cluster setup was moved inside the timed region. The
committed JSON was not regenerated. Use `CC_005`'s `latency_curve.csv`.

`q11_item_matrix.csv` is a 17-row item availability list, not per-episode data.
It is not a figure source.
