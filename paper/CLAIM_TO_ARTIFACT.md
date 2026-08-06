# PAPER-001 Appendix A — Claim-to-Artifact Table

Every claim PAPER-001 makes, with the committed artifact that supports it. Built
in Pass 2, before prose. The program's standing rule is that no result may be
reported which cannot be traced to a committed artifact; this table is how that
rule was enforced for this paper, and it stays in the repository as the audit
trail.

**Method.** Hashes are SHA-256 over git blob content — `git show HEAD:<path> |
sha256sum` — first 16 hex digits, matching the convention used in
`episodic/README.md`. Blob content is LF-normalized, so these values are stable
across platforms; working-tree hashes on Windows are not, and are not used.
Verified against two independently published values: `e005_results.json`
`07b714389697c6e5` and `dx001_results.json` `2f07a462e09bdf79`, both of which
`episodic/README.md` already cites. Repository state: branch `paper-001` from
`main` at `8a8a6229`, updated through EC-002 A1 evidence commit `4168a05c`.

**Status column.**

- **VERIFIED** — the value is read directly from the named artifact.
- **DERIVED** — computed from named artifacts; the computation is stated.
- **DEMOTED** — could not be traced to a committed artifact in this pass. Stated
  in the paper without the unverifiable quantity, or as an open question.
- **CUT** — removed from the paper.

---

## A.1 Artifact hash index

| # | Artifact | Introduced | SHA-256 (16) |
|---|---|---|---|
| R1 | `…/artifacts/ar_001/AR_001_report.md` | `cb696c7f` | `7930a81b6ea7b6b4` |
| R2 | `…/artifacts/ar_001/achievability.json` | `cb696c7f` | `770792d09e07978d` |
| R3 | `…/artifacts/ar_001/episode_coverage.csv` | `cb696c7f` | `29276780d2bfac57` |
| R4 | `…/artifacts/e005/E005_report.md` | `cf0df291` | `e1066df429c3b851` |
| R5 | `…/artifacts/e005/e005_results.json` | `cf0df291` | `07b714389697c6e5` |
| R6 | `…/artifacts/e005/a0_baseline.json` | `cf0df291` | `7645e4746715a965` |
| R7 | `…/artifacts/e005/configuration_sweep.csv` | `cf0df291` | `1ad625d10fb988f9` |
| R8 | `…/artifacts/e005/per_domain_counts.csv` | `cf0df291` | `050c3b4989285b30` |
| R9 | `…/artifacts/e005/optimality_bounds.csv` | `cf0df291` | `aa836ef225f37d0d` |
| R10 | `…/artifacts/e005/oracle_overlap.csv` | `cf0df291` | `4306fd929a11ca63` |
| R11 | `…/artifacts/e005/pool_secondaries.csv` | `cf0df291` | `5987d05846c64f97` |
| R12 | `…/artifacts/e005/targeted_no_regression.csv` | `cf0df291` | `09cbcd27c0cf40aa` |
| R13 | `…/artifacts/e005/dr_002/DR_002_report.md` | `aaaadbf9` | `df1a5e93c9647a65` |
| R14 | `…/artifacts/e005/dr_002/selection_ranks.csv` | `f04d7afb` | `6fdff4022997ab83` |
| R15 | `…/artifacts/e005/dr_002/generality_batched.json` | `05cbfe76` | `7e1fa13ef71a8077` |
| R16 | `…/artifacts/e005/dr_002/dr_002_results.json` | `f04d7afb` | `43e92b956637301c` |
| R17 | `…/artifacts/dx001/DX_001_report.md` | `8ede8c9d` | `ba4d55feee804cc1` |
| R18 | `…/artifacts/dx001/dx001_results.json` | `8ede8c9d` | `2f07a462e09bdf79` |
| R19 | `…/artifacts/dx001/cost_comparison.csv` | `8ede8c9d` | `1ca40da99315c719` |
| R20 | `…/artifacts/dx001/greedy_trace.csv` | `8ede8c9d` | `058268409c642d65` |
| R21 | `…/retrieval_mechanism_ledger/RETRIEVAL_MECHANISM_LEDGER.md` | `05cbfe76` | `3969956f40f5365a` |
| R22 | `…/deployment_closeout/artifacts/dx002/DX_002_report.md` | `c7f2e956` | `456c474f546e61a0` |
| R23 | `…/deployment_closeout/artifacts/dx002/dx002_results.json` | `c7f2e956` | `f8ab79ab041cb3e3` |
| R24 | `…/deployment_closeout/artifacts/cc003/ge0_growth_gate.json` | `517aa353` | `350fe20bbc3beed9` |
| R25 | `…/deployment_closeout/artifacts/cc005/latency_curve.csv` | `9c4d93ef` | `0d2b8075ff5a971f` |
| R26 | `…/deployment_closeout/artifacts/cc005/latency_components.csv` | `9c4d93ef` | `82bbbe38e9423d00` |
| R27 | `…/deployment_closeout/artifacts/cc005/growth_measurement.json` | `9c4d93ef` | `20d65a018e28b03f` |
| R28 | `…/deployment_closeout/CC_003_report.md` | `517aa353` | `12905fa7a4557f4d` |
| R29 | `…/deployment_closeout/CC_005_report.md` | `9c4d93ef` | `af2b07da813c95a7` |
| R30 | `…/audits/scoring_integrity/corrected_scores/arm_totals.json` | `3bb340f8` | `443282df34a3a4ba` |
| R31 | `…/surveys/retrieval_bakeoff/retrieval_bakeoff_report.md` | `4e98a676` | `681208a78d12f591` |
| R32 | `ERRATA.md` | `4485d640` | `2ff9a0158c7358d8` |
| R33 | `…/artifacts/rd001/full_rank_inventory.csv` | `765f48e8` | `7d8874f54d8e9729` |
| R34 | `…/artifacts/rd001/measurement_feasibility.json` | `765f48e8` | `cfdb5155854686c8` |
| R35 | `…/artifacts/rd001/rank_replay.json` | `765f48e8` | `c12448b1a6ce893e` |
| R36 | `…/RD_001_RARITY_PROVENANCE_AUDIT.md` | `4485d640` | `9c10690001f50fd8` |
| R37 | `…/external/longmemeval/EC_001_REPORT.md` | `070ab94c` | `0113f4bcb1de02fd` |
| R38 | `…/runs/tier1_001/tier1_summary.json` | `08e90fa3` | `376ef7c7a16cbc0b` |
| R39 | `…/runs/tier1_001/instrument_audit.json` | `08e90fa3` | `2754bcdd09f24e28` |
| R40 | `…/final_codex_integrity/codex_integrity_score_summary.json` | `e59f86cd` | `178321282e180792` |
| R41 | `…/final_codex_integrity/codex_integrity_score_ledger.jsonl` | `e59f86cd` | `3a293c0973637b45` |
| R42 | `…/runs/tier1_001/retrieval_path_diagnostic.json` | `7b38badb` | `fc6589071af5a092` |

Path prefix `…` is `experiments/components/retrieval_mechanism_ledger` for
R1–R21 and R33–R36, and `experiments/components` for R22–R29.
For R37 it is `experiments`; for R38–R42 it is
`experiments/external/longmemeval`.

---

## A.2 Claims — the decomposition (paper §5)

| # | Claim | Value | Source | Status |
|---|---|---|---|---|
| C1 | All 17 breadth items are present in the store | 17/17, missing 0 | R1, R2 | VERIFIED |
| C2 | Episodes carrying ≥1 item | 76 of 119 | R2 `coverage_episode_count` | VERIFIED |
| C3 | Exact minimum for ≥14/17 | 5,058 chars, 5 episodes, 26,942 headroom | R1, R2 | VERIFIED |
| C4 | Greedy known optimum | 15/17 at 5,455 chars | R1; R5 `oracle` | VERIFIED |
| C5 | Cost of 17/17 | 7,592 chars | R5 `secondary_reference_points.ar_001_exact_frontier_17` | VERIFIED |
| C6 | Domain optima | civil 826, art 3,182, monetary 2,913, marine 824 | R1 | VERIFIED |
| C7 | Exact-threshold set is turns {90,112,113,115,118} | 5 episodes | R1 §Exact Threshold Set | VERIFIED |
| C8 | The carried "oracle" is the **greedy** set, turns {90,112,113,116,118} | 5 ids, 15 facts, 5,455 chars | R5 `oracle.episode_ids`; R10 column headers | DERIVED — R10's columns are `turn_90, turn_112, turn_113, turn_116, turn_118`; R5's `oracle.fact_count` is 15 and `serialized_chars` 5,455, both matching R1's greedy row, not its exact row |
| C9 | Deployed baseline A0 | 6/17, 3/4 domains, 31,946 chars, 8 episodes | R6; R5 `a0_baseline` | VERIFIED |
| C10 | E005 primary configuration | 12/17, 4/4, 16/16 targeted, 31,569 chars, 15 episodes, `A3_l0.1_r0.0_k16` | R5 `primary_configuration`; R4 | VERIFIED |
| C11 | Best by arm | A0 6, A1 12, A2 13, A3 12, A4 15 | R5 `best_by_arm`, `oracle` | VERIFIED |
| C12 | A2 delivers monetary 0/4 at every setting and passes no gate | 3 A2 rows, monetary 0 | R7, R8 | VERIFIED |
| C13 | Configurations swept per pool | 146; 0 inference calls; determinism PASS | R5 | VERIFIED |
| C14 | Every configuration beats the 6/17 baseline **on the 119-episode pool only** | min 7/17 on the 119-pool; min 5/17 on top-100; **min 4/17 on the deployed 34-pool**, where the shipped config scores 5/17 against the baseline's 6/17 | R7 (min over `q11_fact_count` by pool); R4 §Result | **CORRECTED** — R4 states this unscoped and it holds only on the primary pool. Cycle 1 objection A1. This is the paper's forced-order result (§5.3, §5.6) |
| C15 | Greedy optimality ratio range | **Primary pool: 0.9548–0.9996 over 135 computable configurations**; all three pools: 0.9536–0.9996 over 405; primary config 0.9927 | R9; R5 `primary_configuration.optimality_ratio` | DERIVED — min/max over rows with `computable == True`. The paper quotes the **primary-pool** range, which is the population `RETRIEVAL_MECHANISM_LEDGER.md` reports as 0.955. The wider 0.9536 counts all three pools; neither supersedes the other and no published number changes. A1's bound is not computable (33 rows), consistent with MMR being non-monotone (R32) |
| C15b | **Art has no representative anywhere in the top 34, so the deployed pool cannot reach four domains at any setting** | both art contributors at cosine ranks 50 and 86; deployed pool returns art 0/4 | R13 §2; R14 (turns 115, 116) | VERIFIED — **this is the claim the forced order rests on** (§5.6). It is structural: it follows from the pool's contents, so no single run, seed, or measured comparison bears on it. The 5/17-vs-6/17 reading (C14) illustrates the same ordering and is one count from one run |
| C16 | Pool ablation, frozen configuration | 34 → 5/17, 2/4; 100 → 9/17, 3/4; 119 → 12/17, 4/4 | R13 §1 | VERIFIED |
| C17 | Oracle overlap by pool, frozen configuration | 1/5, 0/5, 4/5 | R13 §1 | VERIFIED |
| C18 | Best-of-sweep is 13/17 on **all three** pools | 13, 13, 13 | R5 `best_by_pool` | VERIFIED — the distinction that keeps C16 honest |
| C19 | Pool brittleness | dropping the 19 lowest-cosine episodes costs 3 facts, all of art, and all oracle overlap, though 4/5 oracle episodes survive | R13 §1 | VERIFIED |
| C20 | Top-4 by cosine carry zero Q11 facts | `top4_hits: 0` | R15 Q11 row; R13 §2 | VERIFIED |
| C21 | Q11 first fact-bearing rank / last needed item | 5 / 87 | R15 Q11 row | VERIFIED |
| C22 | Worst fact-bearing rank; registered rule fires at ≥80 | 86 | R13 §2; R15 `worst_fact_bearing_rank_unchanged` | VERIFIED |
| C23 | Both art contributors lie at ranks 50 and 86 | turns 115, 116 | R14 | VERIFIED |
| C24 | Oracle cosine ranks | 14, **20**, 22, 86, 112 | R15 `selection_rank_corrections`; R32 | VERIFIED — supersedes R13's published 21 |
| C25 | Targeted probes place every needed item inside rank 2 | 8 of 8 probes, `last_needed` ≤ 2 | R15 | VERIFIED |
| C26 | Top-4 carry a target item on every targeted probe | 1–4 of 4, never 0 | R15 | VERIFIED |
| C27 | The residual episode | turn 90, rank 112/119, cosine 0.0560, 2,862 chars, 4 monetary items | R17, R18, R19 | VERIFIED |
| C28 | No configuration selects it | 0 of 146 | R17 §D.2.1; R18 | VERIFIED |
| C29 | What it would have needed | cosine 0.225032 against 0.05599; shortfall 0.169042 | R17 §D.3.1; R20 | VERIFIED |
| C30 | Cluster collision refuted | diversity term payable in full at 15 of 15 steps; cluster never entered | R17 §D.3; R20 `counterfactual_wins` all False | VERIFIED — the registered prediction was wrong and the paper says so |
| C31 | Only 20 of 119 episodes clear the needed cosine | 20 | R17 §D.3.1 | VERIFIED |
| C32 | Best rank the target reaches anywhere | 4, at `A3_l1.0_r1.0_k16`; never 1 | R17 §D.2.5 | VERIFIED |
| C33 | Selection terminated on budget | 31,569 of 32,000; 431 left; 0 affordable unselected | R17 §D.2.6 | VERIFIED |

---

## A.3 Claims — the arc (paper §4)

| # | Claim | Value | Source | Status |
|---|---|---|---|---|
| C34 | Bakeoff T1 raw-store reachability | 8/17, below the 11/17 formation-era ceiling | R31 §Outcome, Tier 1 | VERIFIED |
| C35 | T3 routing oracle ceiling | 6.09%, against a registered 10% build threshold | R31 Tier 3 | VERIFIED |
| C36 | T4A graphs | no configuration cleared advancement; 4B never ran | R31 Tier 4 | VERIFIED |
| C37 | T5 ANN | recall degraded at synthetic scale | R31 Tier 5 | VERIFIED |
| C38 | Widened raw STM, formation-blind facts | 6/6 available, 5/6 used correctly | R31 §Primary Positive Result | VERIFIED |
| C39 | 8/17 and 13/17 measure different objects | offline single-block content vs live end-to-end answer; different denominators | R31 §Reconciling | VERIFIED — the paper must not present 13/17 as overturning 8/17 |
| C40 | Density ranks the six hardest plants 89th–316th; the three IDF variants disagree | mean 5/5 eligible spans worse; max 3/5 worse and 2/5 better; sum/word 4/5 worse and 1/5 better | R32, R36 | CORRECTED — no primary IDF variant was registered; family-level negative claim withdrawn |
| C41 | Study 003's weighted promotion route was structurally unreachable | all promotion via bypass | `AGENTS.md` digest 003 | VERIFIED |
| C42 | Topic layer | 52 topics at 120 turns; 12 domains → 2 at 1,000 | `AGENTS.md` digests 002, 010 | VERIFIED |
| C43 | Study 007 | model used 10 of 10 delivered facts, invented none; 7 required facts absent | `AGENTS.md` digest 007 | VERIFIED |
| C44 | Study 008 stopped at pre-run gates | no fill cap 1–50 passed breadth and targeted jointly | `AGENTS.md` digest 008 | VERIFIED |
| C45 | E002 at matched budget | 6/17 @ 31,946 → 10/17 @ 21,761, 3/4 domains; KILL against 14/17 | R32 §E002 budget interpretation; R21 F1 | VERIFIED |
| C46 | E002 targeted, corrected | 14/16 → 16/16; KILL unaffected; the gate was unsatisfiable by construction | R32 2026-08-01 | VERIFIED |
| C47 | E001 attention oracle | 0.120422 → 0.210318 best-found against K = 0.48; 0 of 714 rows reached K; 266/384 heads non-sparse | R21 F2 | VERIFIED |
| C48 | Study 009 same-seed null test | S 9.0 vs L 12.0 | R30 | VERIFIED — the program's only clean architectural comparison |

---

## A.4 Claims — what survives (paper §6)

| # | Claim | Value | Source | Status |
|---|---|---|---|---|
| C49 | The graveyard | 11 mechanisms, each with the result that killed it | R21 §6 | VERIFIED |
| C50 | Surviving architecture | append-only store, recency window, cosine-threshold similarity, set-level coverage selection; 0 inference calls in the memory path | `episodic/README.md`; R5 `inference_calls` | VERIFIED |
| C51 | Extraction is behavior-preserving | 132/132 A3 payload SHAs, 3/3 rendered blocks byte-identical | `CC_002_library_extraction.md` T3/T4 | VERIFIED |
| C52 | `context()` is byte-identical across processes | CC-002 T7 | `CC_002_library_extraction.md` | VERIFIED |
| C53 | Suite | 1,007 tests | R29 §5 | VERIFIED |

---

## A.5 Claims — growth and cost (paper §6.4, Figure 6)

| # | Claim | Value | Source | Status |
|---|---|---|---|---|
| C54 | DX-002 verdict | Branch B — an unbudgeted component is climbing | R22, R23 | VERIFIED |
| C55 | Runner STM p95 growth over the final five buckets | +23,238 chars arm L; +28,701 arm S; record held in the last bucket of both | R22 §Saturation; R23 | VERIFIED |
| C56 | Runner LTM saturates | −867 chars over the same buckets | R22 | VERIFIED |
| C57 | Window over window, runner | arm L STM +33.0%; arm S STM +46.8% | R22 | VERIFIED |
| C58 | Smallest detectable slope | 17.20 chars/turn on `arm_l.total` → 17,203 chars undetectable over 1,000 turns | R22 §What this fit can and cannot rule out | VERIFIED |
| C59 | Residuals are autocorrelated | Durbin-Watson 1.83–2.33; sawtooth series | R22 | VERIFIED |
| C60 | Rule pinning contributed zero — but was disabled before the run | 0 of 1,000 turns; constant 15 chars; untested, not cleared | R22 §Rule pinning | VERIFIED — the caveat is not optional |
| C61 | Library replay is bounded | p95 +18 chars; −0.0236% window over window; 0 of 1,000 turns over budget | R24; R28 | VERIFIED |
| C62 | The library truncates on most turns | 895 of 1,000; max 70 episodes dropped; max `chars_wanted` 65,864 | R24 `truncation` | VERIFIED — bounded because enforced, not because demand is small |
| C63 | Enforcement is inert at the operating point | 132/132 SHAs; 12/17 · 4/4 · 16/16 @ 31,569 unchanged | R28 E6 | VERIFIED |
| C64 | Compact rendering alone did not fix the budget | post-DR-001 max 37,934; 561 of 1,000 turns still over 32,000 | R22 §LTM against its budget | VERIFIED |
| C65 | Latency, measured | 4.2021 ms @ 50; 66.36 @ 500; 189.99 @ 1,000 | R25 | VERIFIED |
| C66 | Empirical exponent | 1.2524 over 50–1,000, against DR-002's 0.96 over 20–119 | R27; R13 §3 | VERIFIED |
| C67 | Clustering share | 0.374 at 50 → 0.807 at 1,000 | R26 | VERIFIED |
| C68 | The projection error | ~40 ms projected vs 190 ms measured at 1,000; the projection ran 84× past its last measured point | R29 §3; R32 | VERIFIED |
| C69 | Disk | 4,743 bytes/turn marginal; 86% embeddings; 4.8 MB at 1,000 turns | R27 `disk` | VERIFIED |
| C70 | Stated horizon | comfortable to a few thousand episodes; unusable interactively before 10,000 | R29 §4 | VERIFIED |

---

## A.6 Claims — self-audit (paper §7)

| # | Claim | Value | Source | Status |
|---|---|---|---|---|
| C71 | Scoring audit | 222 items re-scored, 19 changed, only VALIDATED verdict removed | R30; R32 | VERIFIED |
| C72 | Study 002 C and A falls | 13.0 → 8.5; 8.0 → 5.5 | R30 | VERIFIED |
| C73 | Corrected treatment series | 8.5, 11.5, 6.5, 11.0, 9.0, 12.0, 12.0 | R30 | VERIFIED |
| C74 | The series is not controlled | runtime and response budgets changed across it | `README.md` §Corrected Numbers | VERIFIED — plotted with the caveat in the caption |
| C75 | Residual error estimate is extrapolated | 3 of 26 (11.54%) over 143 unreviewed → 16.5, reported as "about 20" | R32 | VERIFIED |
| C76 | DR-001 rendering | Q13/Q14 were 53,726 / 53,839 chars, 67.9% / 68.2% over budget, not 31,991 "saturated" | R32 §Study 010 LTM Budget Accounting | VERIFIED |
| C77 | Embedder call-shape dependence | cosine agreement 0.999837; largest component difference 0.217; flips 6 of 146 payloads | R17 preamble; R32 | VERIFIED |
| C78 | It is now a startup assertion | `CallShapeError` on every store open | `episodic/README.md` H1 | VERIFIED |
| C79 | DX-002 near miss | a three-clause rule checked only its terminal clause; a block that grew 23,000 chars read as flat | R22 §The near miss; `DECISION_001_dx002_growth_branch.md` | VERIFIED |
| C80 | AS-001 verdict withdrawn post-output | `PRIMACY MECHANISM LIVE`; rank 27 first enters at 108,432 chars | R32; `q4_packing/decisions/DECISION_001_invalidate_branch_d.md` | VERIFIED |
| C81 | The program refuted its own literature claim | MMR is non-monotone submodular; the reason given for "no guarantee" was wrong, the conclusion stands | R32 §MMR Submodularity | VERIFIED |
| C82 | Tier 6 seal limitation | computed over mixed LF/CRLF; `study.db` never committed | R32 | VERIFIED |
| C83 | Probe-order validator caught invalid degradation probes | **count not traced** | `scripts/check_probe_fact_order.py` | **DEMOTED** — the script is committed; no output artifact recording "three probes" was located. Paper describes the validator and the error class without asserting a count |
| C84 | Rater self-consistency 97.47% | **not traced** | — | **CUT** — 11.54% control disagreement (C75) is sourced and is the number the paper uses |

---

## A.7 Claims — limitations (paper §8)

| # | Claim | Value | Source | Status |
|---|---|---|---|---|
| C85 | No error bars anywhere in the program | every comparison single-run, one seed | `AGENTS.md` §4 runtime rules; absence across all reports | VERIFIED — stated as an absence, which is what it is |
| C86 | External calibration boundary | LongMemEval-S now run; LoCoMo unrun; no official comparator score | R37 §7; R40 | VERIFIED — replaces the former “no external calibration” claim |
| C87 | Literal enumeration rests on one probe | Q11 is the only literal enumeration question; EC-001 adds multi-session reasoning as an analogue | R13 §3.5; R37 §6 | VERIFIED |
| C88 | The known optimum contains prior probe answers | 4 of 5 | R15 probe-turn map + R1 oracle set | DERIVED — probe turns are 112, 113, 115, 116, 117, 118, 119, 120; oracle turns are 90, 112, 113, 116, 118; four intersect. **Not** from `prior_answer_fraction.csv`, which measures a different quantity (fraction of *selected* episodes that are prior answers, per configuration) |
| C89 | Achievability holds under `source_turn < 120`, not a plant-source-only bound | — | R1 §Interpretation Boundary | VERIFIED |
| C90 | Amendments after results exist | 12 in the bakeoff, each with a before/after column | R31 §Amendment Legitimacy | VERIFIED |
| C91 | Runtime independence unmeasured | one model, one quantization, one machine | R29 §6 | VERIFIED |
| C92 | Horizon limit | 1,000 turns says nothing about 10,000 | R22 §Boundary; R28 §5 | VERIFIED |
| C93 | AI raters with AI adjudicators | final adjudication used AI reviewers, not humans | R32; `README.md` §Corrected Numbers | VERIFIED |
| C94 | The inversion is not a dominant external ranking pattern; its cause remains unresolved and the adapted delivery path still fails | LongMemEval top-four failure 69/470; top-four evidence 401/470 but session recall only 96/401; RD-001 stopped before correlation | R37 §§2–3; R38; R42; R34 | VERIFIED — external ordering narrows the inversion claim without validating downstream retrieval or identifying vocabulary as the cause |
| C95 | Full Q11 cosine ordering recovered under the pinned call | 119/119; 16-rank replay PASS with known 21→20 correction | R33, R35 | VERIFIED |

---

## A.8 EC-001 external calibration claims

| # | Claim | Value | Source | Status |
|---|---|---|---|---|
| C96 | LongMemEval top-four inversion rate | 69/470 = 14.7%; median evidence-session rank 2, p95 23, max 49 | R37 §2; R38 | VERIFIED |
| C97 | LongMemEval exact-turn availability | any 79/470 = 16.8%; all 20/470 = 4.3% | R37 §3; R38 | VERIFIED |
| C98 | Codex-substituted Tier 2 result | 28/140 = 20.0% equal-quota; 12.22% post-stratified | R37 §4; R40 | VERIFIED — explicitly not official or benchmark-comparable |
| C99 | External availability-minus-correctness gap | 8/118 vs 11/118; −2.54 percentage points | R37 §5; R40 | VERIFIED |
| C100 | Multi-session and temporal Tier 2 | 0/20 in each stratum | R37 §4; R40 | VERIFIED |
| C101 | Component absence signal vs reader abstention | 0/500 component signals; 17/20 reader-correct | R37 §§4,6; R38; R40 | VERIFIED — different levels of the system; retires F3 as a component requirement for this tested reader, not as a universal capability |
| C102 | Instrument-audit inventory | 358 predicate hits across five registered kinds | R37 §8; R39 | VERIFIED — not described as 358 adjudicated defects |
| C103 | Favourable external session rank does not become delivery | evidence top-four on 401/470; session recall on 96/401; 232/500 K-candidate questions but 20/500 with delivered non-recency K | R42 | VERIFIED — post-hoc path diagnostic, no counterfactual parameter claim |
| C104 | EC-001 delivered path is recency dominated | all 500 blocks truncated; median 16 recency, 0 K, 1 coverage; 91/109 session hits from recency | R42 | VERIFIED — observed path attribution, not a retuning result |

---

| C105 | K-first packing causally recovers evidence sessions offline | any-session 109/470 -> 261/470; 152 gains, 0 losses | `external/longmemeval/runs/ec002_k_first/a1_k_first/paired_comparison.json` | VERIFIED - same-store paired counterfactual |
| C106 | K-first raises exact-turn-any availability with two losses | 79/470 -> 196/470; 119 gains, 2 losses | same | VERIFIED - no materiality threshold or reader-level claim |
| C107 | EC-001 is not bit-replayable | original vector cache unrecoverable; A0 is a reproduction under recomputed embeddings | `external/longmemeval/amendments/AMENDMENT_011_ec002_recomputed_embedding_reproduction.md`; `EC_002_REPORT.md` section 5 | VERIFIED - CC-006 protection is prospective |

---

| C108 | The internal deployed order starved the similarity path completely | K delivered 0 episodes and 0 characters at 8 of 8 probes under recency-first; 9 episodes and 14,796 characters under K-first | `internal/packing_priority/runs/ic001/b1_k_first/path_split.csv` | VERIFIED - observed path attribution on frozen candidate identities |
| C109 | Internal breadth availability rises under K-first without a targeted loss | Q11 6/17 -> 7/17, 1 gain 0 losses; eight targeted probes 14/21 -> 18/21, 4 gains 0 losses | `internal/packing_priority/runs/ic001/b1_k_first/paired_comparison.json` | VERIFIED - availability only, one probe, no variance |
| C110 | The internal 6-of-17 baseline is packing-conditioned | same store, identities, and selector deliver 7/17 in 31,863 characters against 6/17 in 31,946 | `internal/packing_priority/runs/ic001/b0_recency_first/b0_gate.json`; `.../b1_k_first/b1_arm.json` | VERIFIED - B0 reproduces the committed deployed result exactly |
| C111 | K-first did not reproduce the LV-001 displacement offline | no targeted probe fell; the Q11 window gains the turn-1 and turn-2 episodes B0 dropped | `internal/packing_priority/runs/ic001/b1_k_first/targeted_per_probe.csv`; `.../b1_arm.json` | VERIFIED - offline availability on a different arm; not a repair of LV-001 |

---

## A.9 Claims deliberately not made

| Claim the evidence does not support | Why |
|---|---|
| "Similarity retrieval fails" | R13 §3.5 measures the opposite on 8 of 9 probes. The paper's claim is bounded to enumeration queries on this corpus |
| "Our approach doubles performance" | True of 6/17 → 12/17 and misleading without 14/17 and the 15/17 known optimum beside it (C3, C4) |
| Any comparison to HippoRAG, Mem0, Zep, Letta | None were run |
| Novelty for MMR, facility location, or submodular selection | Established methods. The contribution is the decomposition and the measurement |
| That the pool cut costs 7 facts in general | C16 is one frozen configuration; C18 is the sweep. The general claim is about domains |
| That the 15/17 optimum is achievable by a retriever | It is computed with the answer key (R1 §Interpretation Boundary) |
| That `episodic` is bounded in general | C61 is one store, one conversation shape, one horizon (R28 §5) |

---

## A.9b Restructure note (2026-08-02)

After a three-reader readability review the paper was restructured: §5 now
follows the forced order it claims (pool → objective → floor), the scoring-audit
figure was cut, and the remaining figures renumbered 1–5. **No claim in this
table changed value, was added, or was removed.** The section numbers cited in
paper prose moved; the claim/artifact pairs did not. Claims C71–C75 (the scoring
audit) remain supported and are now reported in §7.1 prose rather than in a
figure.

Three figure/text contradictions were also repaired, all of the same species —
the figures were generated in Pass 3 and the review cycles corrected the prose
without re-auditing the images:

| Figure | Contradiction | Fix |
|---|---|---|
| 2 | Plotted baseline against shipped configuration with no indication the pool changed too — the confound C15/§5.3 exists to refute | Every bar now names its pool; footnote states the confound |
| 4 (was 5) | Footnote asserted "all 146 configurations beat the deployed 6/17", true only on the 119-pool (C18) | Names the pool; states the 5/17 inversion |
| 1 | Callout asserted "selected by 0 of 146 configurations", the count C28's §5.4 declines to lean on | Replaced with the arithmetic: needs 0.225, has 0.056 |

## A.10 Figure-source note

`dr_002_results.json` (R16) carries a `timings` block reading 1.28 ms at pool
119. That is the greedy-loop-only measurement which DR-002 §3 itself supersedes:
with cluster setup moved inside the timed region the total is 4.756 ms. The JSON
was not regenerated after the correction. **Figure 6 uses R25, not R16.** Noted
here because the stale value is the one a reader parsing the JSON would find.

A second instance, **now fixed**: `ERRATA.md`'s latency table (R32) was headed
"Median build_context" while drawing its 50- and 500-candidate rows from R26's
`stage_total_ms`, its 1,000-candidate row from R25, and its "119" row from
neither — CC-005 has no 119-candidate point, and that row paired the
100-candidate median with the 50-candidate per-candidate cost. The table is
replaced with all nine rows of R25, and the entry now carries a dated
correction-to-itself recording what was wrong.

One claim in that entry did not survive: "per-candidate cost is flat to about
119 candidates" is not a reading of CC-005's curve, where cost rises 84.0 → 100.1
µs between 50 and 100 candidates. The flatness belongs to DR-002's measurement,
which times a narrower span. The headline values — 190 ms at 1,000, exponent
1.25, clustering 81% — were always read from the right artifacts and stand.

The paper uses R25 throughout and never reproduced the faulty row.
