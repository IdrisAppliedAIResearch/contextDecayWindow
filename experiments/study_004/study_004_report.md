# Active LTM Retrieval with Tier Arbitration in a Bounded Conversational Memory Architecture

## Study 004 Final Report — contextDecayWindow

**Idris Applied AI Research**

**Status:** COMPLETE — PARTIAL (1 of 3 pre-registered bars passed)

**Date:** July 21, 2026

**Pre-registration:** `1b9eb204e32b6b7cb32dfce4cb647cfc7f0e4d0f`

**Amendment A005:** `9fbf4f9f95a1fad6205d56664db36b9911650d41`

**Accepted v4 run:** `study_004_full_002`

**Same-settings v3 control:** `v3_control_002`

**v4 score lock:** `8e097c07e7b092902cf57562f727d297569f5421`

## Abstract

Study 004 activated the read path for the LTM store built in Study 003. STM and
LTM were queried in parallel, deduplicated, ranked without tier preference, and
rendered in explicitly tagged context blocks. The study also added
ground-truth consolidation-purity checks, a turn-111 final-domain flush, and a
decoupled association score intended to revive the weighted promotion route.

An initial v4 run exposed a 1,024-token response-budget insufficiency. Locked
Amendment A005 raised the budget to 2,048 after a 4,096-ceiling verification and
required a same-settings v3 control before a fresh v4 run. The control scored
11.0/13.0 on Q1–Q13 and failed both breadth probes. The fresh v4 run completed
121 turns without truncation but scored 7.0/13.0 and Q14 = 0.0. Bar 1 (breadth)
and Bar 2 (targeted non-regression) failed; Bar 3 (consolidation purity) passed.

The LTM query path itself was reliable: LTM contributed to all 90 eligible
turns, including five episodes at each breadth probe. The failure was upstream.
The 12-row LTM store promoted nine early civil episodes and only one generic
episode from each later domain; none of the rubric-critical art, monetary, or
marine plants were promoted. The read path therefore retrieved what the store
contained, but the store did not contain the facts it was meant to recover.

## 1. Research questions

1. Does active LTM retrieval recover four-domain breadth without reducing
   targeted recall?
2. Do purity-constrained consolidation, final-domain flushing, and association
   decoupling correct Study 003's known architectural defects?
3. How often does LTM contribute, overlap with STM, deduplicate, or displace STM
   candidates in practice?

## 2. Changes from Study 003

- Active asynchronous STM/LTM parallel retrieval on every turn.
- Tier-neutral arbitration with episode-ID deduplication and stable tie breaks.
- Explicit `<recent_context>`, `<retrieved_stm>`, and `<retrieved_ltm>` context
  blocks with LTM promotion metadata.
- Consolidation purity measured against registered script domains; probe-topic
  bridge merges blocked.
- Turn-111 end-of-session promotion flush for marine biology.
- Association computed against the best per-topic LTM centroid, while novelty
  remains relative to the global centroid.
- A second breadth probe, Q14, appended at turn 121.
- Under A005, a 2,048-token response budget and a same-runtime v3 control.

## 3. Method

### 3.1 Runtime and script

- Model: Qwen3.6 27B UD-Q6_K_XL, served by llama.cpp.
- Context capacity: 262,144 tokens.
- Response budget: 2,048 tokens.
- Sampling: shared server defaults for control and v4.
- Embeddings: Qwen3-Embedding-0.6B Q8_0, 1,024 dimensions.
- Script: 121 turns; turns 1–120 hash-identical to Study 003, Q14 appended at
  121. SHA-256:
  `97C42E0FF612245C7CDAB3B6F6F3C1D4BD9DE5AAD14FD4519C63E37D63F93F0E`.

### 3.2 A005 control discipline

The control executed the accepted Study 003 v3 implementation from a separate
worktree, not the v4 runner with flags disabled. Its adapter changed only the
response budget and launcher/provenance wiring. Runtime module paths were
recorded before inference. A first control launch was invalidated before
scoring when editable-package resolution loaded v4; the hardened retry
`v3_control_002` resolved both runner and context builder inside the v3
worktree.

### 3.3 Evaluation sequence

1. Verify 2,048-token sufficiency.
2. Commit A005 and production budget change.
3. Re-run and pass the 35-turn v4 gate.
4. Run, score, and commit the v3 control.
5. Apply A005's behavioral-control gate.
6. Run all 121 v4 turns.
7. Score and commit Q1–Q14 before opening probe arbitration/provenance.
8. Evaluate bars and observational measures.

Manual scoring used the locked Study 002 Q1–Q13 rubric and Study 004 Q14
criteria. The same rater interpretation was retained, including full Q8 credit
when photophores and the mantle were both named despite overbroad extra anatomy.

## 4. Amendments, deviations, and run disposition

- `study_004_full_001_failed_truncation`: stopped under the registered rule
  after turns 8–10 all hit 1,024 tokens. The outputs were coherent, clean, and
  cut mid-sentence; it is preserved as a failed diagnostic and not scored.
- A005: response budget 1,024 → 2,048; historical Study 003 baseline replaced
  by a same-settings v3 control; Bar 1 and Bar 2 amended accordingly.
- `v3_control_001_invalid_import_resolution`: invalid v4 import resolution,
  detected before rubric scoring; preserved and excluded.
- `study_004_full_002_launch_failed_encoding_zero_turn`: CP1252 banner-print
  error before turn 1/inference; preserved initialization shell, not a study
  run. UTF-8 stdout relaunch changed no scientific setting.
- Context-construction latency was not instrumented. This affects one
  observational measure only and is documented separately.

## 5. Results

### 5.1 Run integrity

| Measure | v3 control | Fresh v4 |
|---|---:|---:|
| Completed turns | 121 | 121 |
| Empty responses | 0 | 0 |
| Responses at 2,048 cap | 0 | 0 |
| Maximum response | 1,434 | 1,393 |
| Peak estimated context | 9,251 | 11,376 |
| Runtime | 34m33s | 44m54s |
| Promotion events | 31, 61, 91 | 31, 61, 91, 111 flush |

The v4 run emitted 121 arbitration rows and 121 context-size rows. No response
echoed a v4 context tag or rule-detection tag.

### 5.2 Rubric

| Question | v3 control | v4 |
|---|---:|---:|
| Q1 — early numerical facts | 1.0 | 1.0 |
| Q2 — early entity/load | 1.0 | 1.0 |
| Q3 — rule recall | 1.0 | 1.0 |
| Q4 — middle multi-fact | 1.0 | 0.0 |
| Q5 — pigment technique | 0.0 | 0.0 |
| Q6 — middle bleed probe | 1.0 | 0.0 |
| Q7 — late multi-fact | 1.0 | 0.0 |
| Q8 — bioluminescence | 1.0 | 1.0 |
| Q9 — topic bleed | 1.0 | 1.0 |
| Q10 — researcher disambiguation | 1.0 | 0.0 |
| Q11 — full enumeration | 0.0 | 0.0 |
| Q12 — rule recall | 1.0 | 1.0 |
| Q13 — rule compliance | 1.0 | 1.0 |
| **Q1–Q13** | **11.0/13.0** | **7.0/13.0** |
| Q14 — second breadth probe | 0.0 | 0.0 |

v4 category totals were Cat 1 = 3.0/3.0, Cat 2 = 0.0/3.0, Cat 3 =
1.0/2.0, Cat 4 = 1.0/3.0, and Cat 5 = 2.0/2.0.

### 5.3 Pre-registered bars

| Bar | Result | Evidence |
|---|---|---|
| Bar 1 — breadth recovery | **Fail** | Q11 0.0; Q14 0.0; combined 0.0. Five LTM episodes reached each probe, but not the required plants. |
| Bar 2 — targeted non-regression | **Fail** | 7.0 < absolute floor 12.0 and < control 11.0; Cat 2 and Cat 3 also failed. |
| Bar 3 — consolidation purity | **Pass** | Five final topics; zero cross-domain merges. |

**Confirmatory outcome: PARTIAL — 1 of 3 bars passed.**

There was no Bar 1 pass to attribute. Although LTM provenance was present, it
did not provide the planted facts required for a breadth pass; no LTM benefit
is claimed.

### 5.4 Arbitration

- LTM contribution: 90/121 turns (74.38%), and 90/90 after LTM became
  available.
- LTM candidates/final episodes: 450/450.
- Deduplication: one duplicate among 450 LTM candidates (0.22%), at turn 116.
- Arbitration provenance: 23 STM, 449 LTM, 1 both.
- Displacement events: zero. Every unique arbitration candidate survived.
- Q11 LTM turns: 1, 2, 3, 35, 76.
- Q14 LTM turns: 1, 2, 3, 76, 8.

The breadth queries reached rules, early bridge facts, generic egg-tempera
content, and generic expectations content—not the art, monetary, and marine
plants in the scoring key.

### 5.5 Promotion, flush, and weighted route

| Event | Evaluated | Promoted | Route |
|---:|---:|---:|---|
| 31 | 30 | 9 | weighted threshold |
| 61 | 30 | 1 | repetition bypass |
| 91 | 30 | 1 | repetition bypass |
| 111 | 21 | 1 | novelty bypass |

The flush successfully evaluated the final domain but promoted generic turn
109 rather than planted turns 100–102. Association decoupling was numerically
active at events 91 and 111, but no post-decoupling episode was promoted
uniquely through the weighted route.

### 5.6 Consolidation purity

The run created six topic nodes and performed one consolidation merge at turn
20, within the registered civil-engineering domain. Five topics remained at
turn 121. No cross-domain or probe-bridge merge occurred. The purity fix
corrected Study 003's terminal collapse.

## 6. Discussion

### 6.1 Retrieval engagement was not memory usefulness

The read path was operational and pervasive. LTM appeared on every eligible
turn, logging was internally consistent, and no dedup or arbitration defect was
found. This rules out a dead query path. It does not establish useful memory.
Top-M retrieval can only recover episodes that promotion admitted, and the
store omitted every later-domain plant needed for the breadth rubric.

The final store's domain coverage was nominal rather than substantive: one
generic art episode, one generic monetary episode, and one generic marine
episode satisfied representation but not factual salience. Broad queries then
returned domain-shaped content that looked plausible while missing the locked
facts.

### 6.2 Targeted recall regressed without displacement

Relative to the same-settings control, v4 lost Q4, Q6, Q7, and Q10. This was not
the registered LTM-displacement failure mode: no unique STM candidate was ever
dropped by arbitration. Instead, the relevant v3 K episodes (art turn 55 and
marine turn 100) did not enter the corresponding v4 contexts. Generic LTM
episodes and earlier wrong probe answers filled the context instead.

A005 intentionally bundles read-path and XML-tagging changes. The control also
uses stochastic generation. Consequently, the pair demonstrates regression of
the v4 bundle but cannot identify whether tagged formatting, generated episode
content/embeddings, threshold crossings, or LTM context itself caused the
candidate-coverage change. A tagged/read-off third arm is required for that
attribution.

### 6.3 Promotion selectivity is the binding problem

The empty-LTM first batch promoted turns 1–9 wholesale through high novelty and
repetition. Later planted facts had repetition 0.2–0.6 and weighted scores below
0.50. Generic turns with repetition 1.0 or novelty above 0.90 entered through
the bypass. The architecture therefore encoded early repeated material and
isolated generic novelty rather than the compact facts later probes demanded.

The turn-111 flush and association decoupling solved structural reachability,
not selection quality. Their implementations worked, but neither changed which
marine facts the system retained.

## 7. What should change next

1. Add a tagged/read-off v3 arm before assigning regression to read path versus
   XML presentation.
2. Make promotion explicitly sensitive to durable factual salience and domain
   coverage, then pre-register the change. Candidate approaches include
   offline dream-cleaning/distillation, per-domain diversity constraints, or a
   compact fact-bearing score—not post-hoc threshold tuning on this run.
3. Add broad-query diversification so rules and the earliest domain cannot
   occupy most of Top-M when multiple canonical topics exist.
4. Fix latency instrumentation before another runtime comparison.
5. Pin deterministic generation seeds or run repeated seeds; one stochastic
   control/treatment pair is too fragile for fine attribution.

## 8. Limitations

- One scripted run and one manual rater per arm.
- v4 versus control bundles read path and tagging.
- Generation was stochastic despite identical settings.
- Q8's full-credit location interpretation is inherited from Study 003 and is
  intentionally held constant, but remains coarse.
- The rubric rewards planted facts rather than general factual plausibility.
- Context-construction latency was not recorded.
- The promoted store and Top-M were evaluated only under this script and model.

## 9. Reproducibility and artifacts

- Pre-registration: `experiments/study_004/pre_registration.md`
- Amendment A005:
  `experiments/study_004/protocol_amendment_005_response_budget_and_v3_control.md`
- Accepted run: `experiments/study_004/runs/study_004_full_002/`
- Rubric score lock: `condition_c/rubric/scores.md`
- Success bars: `condition_c/rubric/success_bars.md`
- Arbitration/LTM analysis: `condition_c/ltm_analysis/analysis_report.md`
- Control score: `controls/v3_same_settings/v3_control_002/iterative/rubric/scores.md`
- Failed truncation diagnostic:
  `runs/study_004_full_001_failed_truncation/`
- Ablation report: `experiments/study_004/ablation/ablation_report.md`

Heavy raw logs, prompts, snapshots, and databases are retained locally with
SHA-256 hashes in each run's notes. Curated responses, metrics, provenance,
scores, and reports are committed.

## 10. Conclusion

Study 004 validates consolidation purity but does not validate active LTM
retrieval as implemented. The system queried LTM reliably and rendered it
without duplication or displacement bugs, yet the promotion policy retained
generic or early episodes instead of the later planted facts. The immediate
research target is therefore memory formation—dream-cleaning, factual-salience
selection, and domain diversity—followed by a tagged/read-off ablation. Expanding
the read path before correcting what enters LTM would scale the wrong memory.
