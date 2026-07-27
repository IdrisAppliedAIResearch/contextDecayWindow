> **CORRECTION (2026-07-26):** Treatment remains 11.0; control corrects 12.0 -> **11.5**. Bar 3 still fails and the PARTIAL verdict is unchanged. Original claims remain below. See `../audits/scoring_integrity/audit_report.md`.

# Extractive Dreaming for Factual Memory Formation in a Bounded Conversational Architecture

## Study 005 Final Report - contextDecayWindow

**Idris Applied AI Research**

**Status:** COMPLETE - PARTIAL (Bar 1 failed, Bar 2 not evaluable, Bar 3 failed)

**Date:** July 22, 2026

**Pre-registration:** `20aa7707e780543ccbe462efadf3bb1263b3813e`

**Accepted treatment:** `study_005_full_001`

**Seeded Study 004 control:** `promotion_seeded_001`

**Score lock:** `1bbfad7`

## Abstract

Study 005 replaced selective STM-to-LTM promotion with permissive episodic
capture followed by extractive dreaming. Every turn entered the raw store.
Dream passes at turns 31, 61, 91, and 111 scored whole conversation episodes
by named entities plus twice their numeric-token count, selected the top three
per topic, and copied them verbatim into distilled LTM. A same-seed accepted
Study 004 promotion architecture served as the control.

Both arms completed 121 turns. Their first 30 prompts and responses were
byte-identical, confirming the paired trajectory before memory formation
diverged. Dreaming wrote 12 records with 100% provenance faithfulness, zero
non-content records, zero inference calls, and a 10.81% distilled-to-dreamed
ratio. Those mechanical properties passed. The central formation criterion did
not: the locked fact matcher found rubric-critical facts in only civil
engineering and monetary policy, 2 of 4 domains rather than the required 3.
Art and marine plants ranked far below the top-three cutoff.

The treatment scored 11.0/13.0 on Q1-Q13 and 0.5 on Q14, versus control scores
of 12.0/13.0 and 0.0. Bar 1 failed. Bar 2 was therefore not evaluable under the
pre-registration, even though five distilled records reached each breadth
probe. Bar 3 failed because treatment scored below control overall and in the
middle and late categories. The confirmatory outcome is PARTIAL under the
locked evaluator, with no confirmatory bar passed and one bar conditionally not
evaluable.

The failure is attributable to formation, not extractive fidelity. Whole-turn
salience rewarded long, number-rich generated answers rather than concise
user-planted facts. The read path is still not functionally validated.

## 1. Research questions

1. Does extractive dreaming form a distilled LTM containing salient planted
   facts from at least three domains, with faithful provenance and no junk?
2. Given successful formation, does distilled retrieval recover four-domain
   breadth?
3. Does dreaming preserve targeted recall relative to a same-seed promotion
   control?
4. Observationally, what does dreaming retain, how compact is the store, and
   how do distilled records enter probe contexts?

## 2. Changes from Study 004

- Every conversation turn is appended to a permissive raw episodic store.
- Novelty, repetition, association, emotional, weighted-threshold, and bypass
  promotion routes are retired from the treatment write path.
- Dreaming is the selective stage and makes no inference-model calls.
- Salience is `named_entities + 2 * numeric_tokens` over a whole user/assistant
  conversation episode.
- Near-duplicates at cosine similarity 0.95 or above collapse before selection.
- At most three records are retained per topic, subject to salience floor 2.
- Distilled text is a verbatim source span with source IDs, turns, event, and
  salience provenance.
- The carried LTM tier queries distilled LTM, top M = 5.
- Runtime is fixed-seed, single-slot, and non-speculative.

## 3. Method

### 3.1 Runtime and determinism

- Model: Qwen3.6 27B UD-Q6_K_XL.
- Server: llama.cpp build 9294 (`0f3cb3fc8`).
- Context: `--ctx-size 50000`, realized as 50,176 tokens.
- Response budget: 2,048 tokens.
- Embeddings: Qwen3-Embedding-0.6B Q8_0, 1,024 dimensions.
- Sampling: temperature 1, top-p 0.95, top-k 20, min-p 0, no
  presence penalty, repeat penalty 1.
- Seed: 5005; parallel slots: 1; speculative decoding: off.
- Script SHA-256:
  `D8BA73FD02BFD41BEC156904FB6A3328BBED3D0DA8BFF05E4667D2E450752F01`.

The accepted determinism gate replayed ten turns on fresh servers with 10/10
prompt and response byte matches. In the confirmatory arms, turns 1-30 also
matched exactly: 30/30 prompts and 30/30 responses.

### 3.2 Control discipline

The control used accepted Study 004 base
`994a490155bcb32a388222abfa3b8f2946d62fe4` in a separate worktree. Adapter
`a8a29aa65e55088a9dbf273deec482df9bb6c4dc` changed only the launcher,
deterministic model-visible rule IDs, and their tests. The launcher rejected a
dirty worktree, unexpected diff, script hash, import escape, or Study 005 dream
engine. It recorded module paths, server properties, command, and process ID
before inference.

### 3.3 Evaluation sequence

1. Lock pre-registration and fixed seed.
2. Pass unit, synthetic, runtime, determinism, and 35-turn ablation gates.
3. Commit the explicit GO decision.
4. Run the seeded promotion control and treatment on fresh identical servers.
5. Verify run completeness and same-seed prefix equality.
6. Score both rubric response artifacts and compute formation/faithfulness.
7. Commit score and structural lock at `1bbfad7`.
8. Open dream, retrieval, and arbitration logs for mechanism analysis.

Manual scoring used the unchanged Study 002 Q1-Q13 rubric and Study 004 Q14
criteria. Completion stdout included truncated fragments of turns 1, 2, 120,
and 121 after each run; no dream, retrieval, arbitration, or probe-context log
was opened before the score lock.

## 4. Run integrity

| Measure | Promotion control | Dreaming treatment |
|---|---:|---:|
| Completed turns | 121 | 121 |
| Peak estimated context | 10,006 | 16,171 |
| Fraction of 50k capacity | 20.01% | 32.34% |
| Average tokens/s | 37.318 | 36.022 |
| Minimum tokens/s | 12.757 | 9.572 |
| Generated tokens | 83,377 | 88,885 |
| Runner duration | 38m46s | 40m47s |
| Strict-monitor abort | No | No |

Both peaks remained below the registered 40,000-token monitor ceiling. Each
arm wrote 121 performance and context rows and both rubric artifacts.

## 5. Results

### 5.1 Rubric

| Question | Control | Treatment |
|---|---:|---:|
| Q1 - early numerical facts | 1.0 | 1.0 |
| Q2 - early entity/load | 1.0 | 1.0 |
| Q3 - rule recall | 1.0 | 1.0 |
| Q4 - middle multi-fact | 1.0 | 1.0 |
| Q5 - pigment technique | 1.0 | 0.5 |
| Q6 - middle bleed probe | 1.0 | 1.0 |
| Q7 - late multi-fact | 1.0 | 1.0 |
| Q8 - bioluminescence | 1.0 | 0.5 |
| Q9 - topic bleed | 1.0 | 1.0 |
| Q10 - researcher disambiguation | 1.0 | 1.0 |
| Q11 - full enumeration | 0.0 | 0.0 |
| Q12 - rule recall | 1.0 | 1.0 |
| Q13 - rule compliance | 1.0 | 1.0 |
| **Q1-Q13** | **12.0 / 13.0** | **11.0 / 13.0** |
| Q14 - second breadth probe | 0.0 | 0.5 |

Treatment categories were Cat 1 = 3.0/3.0, Cat 2 = 2.5/3.0, Cat 3 =
1.5/2.0, Cat 4 = 2.0/3.0, and Cat 5 = 2.0/2.0. Control held Cat 1 =
3.0, Cat 2 = 3.0, Cat 3 = 2.0, Cat 4 = 2.0, and Cat 5 = 2.0.

Q11 treatment recovered 9 of the 17 locked values/entities, below the 80%
threshold. Q14 supplied valid planted specifics for civil engineering,
monetary policy, and marine biology. Its Renaissance detail, `Renovatio
Romanorum`, was not in the locked plant key, yielding exactly one lapse and
0.5 credit.

### 5.2 Formation, fidelity, and compactness

| Measure | Result |
|---|---:|
| Raw conversation episodes | 121 |
| Episodes reached by dream cadence | 111 |
| Distilled content records | 12 |
| Distilled / dreamed | 10.81% |
| Distilled / full run | 9.92% |
| Faithful records | 12 / 12 |
| Non-content records | 0 |
| Marker records | 0 |
| Dream inference calls | 0 |
| Near-duplicates collapsed | 0 |

The selected source turns were:

| Dream event | Selected source turns |
|---:|---|
| 31 | 4, 17, 20 |
| 61 | 31, 40, 41 |
| 91 | 61, 69, 84 |
| 111 | 92, 105, 108 |

Locked fact coverage was:

| Domain | Fact present? | Matching locked facts |
|---|---|---|
| Civil engineering | Yes | `civil_steel`, `civil_load` |
| Renaissance art | No | None |
| Monetary policy | Yes | `monetary_taylor` |
| Marine biology | No | None |

Formation therefore covered 2 of 4 domains. The promotion control's 14-row
store covered three domains under the same matcher: civil, Renaissance art,
and marine biology, but not monetary policy.

### 5.3 Pre-registered bars

| Bar | Criterion | Observed | Result |
|---|---|---|---|
| 1 - Dream formation | At least 3/4 domains, 100% faithful, zero non-content | 2/4 domains; 12/12 faithful; zero non-content | **FAIL** |
| 2 - Breadth recovery | Conditional on Bar 1; Q11 and Q14 thresholds plus distilled provenance | Bar 1 failed | **NOT EVALUABLE** |
| 3 - Targeted non-regression | Treatment at least control overall; Cats 1-3 held | 11.0 < 12.0; Cats 2 and 3 lower | **FAIL** |

**Confirmatory outcome: PARTIAL.** No confirmatory bar passed; Bar 2 is
conditionally not evaluable rather than failed. This nomenclature follows the
locked evaluator, which reserves VALIDATED for all three passes and otherwise
reports PARTIAL.

### 5.4 Probe retrieval anatomy

Both breadth probes had zero STM arbitration candidates and five distilled-LTM
records in the final set.

| Probe | Distilled source turns |
|---|---|
| Q11, turn 120 | 4, 41, 61, 17, 92 |
| Q14, turn 121 | 4, 61, 84, 105, 17 |

The query path was active, but the store content was insufficient. Q11 reached
nominal source domains across the run but not the locked art and marine facts.
Q14 received no art record. The valid art answer was not recovered, and its
named art detail was carried from generic conversational content rather than a
locked plant. Distilled placement alone does not validate useful retrieval.

### 5.5 Topic consolidation

The run ended with five topics. The only merge occurred at turn 20 within the
civil domain. No cross-domain purity event was logged. The probe-bridge guard
was not exercised in the full run, so it receives no new confirmatory credit;
its active path remains established only by the passing synthetic fixture.

## 6. Why formation failed

### 6.1 Whole-turn salience selected verbosity

The scorer operated on one combined user/assistant episode per turn. Generated
answers were often much longer and contained many incidental names and
numbers. The top-three cap therefore favored verbose answers over concise
plant turns.

| Plant source | Domain | Salience rank in event | Selected? |
|---:|---|---:|---|
| 3 | Civil identity/span | 28 | No |
| 4 | Civil steel/load | 3 | Yes |
| 55 | Art identity/year | 18 | No |
| 56 | Art pigment | 28 | No |
| 60 | Art patron role | 19 | No |
| 61 | Taylor Rule/year | 1 | Yes |
| 62 | Federal Reserve/mandate | 5 | No |
| 65 | Mehta/2.3%/2% | 6 | No |
| 100 | Marine identity/depth | 11 | No |
| 101 | Marine photophores | 16 | No |
| 102 | Marine feeding | 17 | No |

The algorithm behaved exactly as specified. The specification's proxy for
factual salience was the failing assumption.

### 6.2 Coverage was topical, not factual

The per-topic cap guaranteed that every outgoing topic supplied up to three
records, but it did not guarantee that those records contained durable facts.
Unlike the sparse-topic floor, all real topics had abundant high-scoring text,
so the floor and marker path could not distinguish useful plants from verbose
generic content.

### 6.3 Deduplication did not create room

No episode pair crossed the 0.95 threshold. The selected records were not near
duplicates under the embedding metric, so deduplication never freed a slot for
lower-ranked plants.

## 7. Interpretation

Study 005 validates the mechanical form of extractive dreaming but not its
selection policy. The system can append every turn, trigger on schedule, copy
verbatim spans, preserve provenance, exclude acknowledgment-class junk, write
a compact store, and retrieve from it. It cannot yet decide which episode
spans deserve the limited slots.

The same-seed design makes the contrast stronger than prior studies. The arms
are exactly identical through turn 30, then diverge at their first formation
event. The treatment's one-point targeted regression and lower Cat 2/Cat 3
totals are therefore consequences of the post-event architecture trajectories,
not an uncontrolled seed difference.

The Q14 improvement from 0.0 to 0.5 is not enough to claim breadth recovery.
Q11 remained zero, Bar 1 failed, and the art specific was outside the locked
key. The pre-registered retrieval-diversity trigger was specifically Bar 1 pass
plus Bar 2 fail; that condition did not occur. Retrieval diversity should not
be built yet. Formation remains the first problem.

## 8. What should change next

1. Select atomic source spans rather than whole user/assistant episodes.
2. Score user-provided factual spans separately from model-generated response
   text, or normalize entity/numeric counts by span length.
3. Replace a pure top-three ranking with explicit fact-bearing coverage within
   each topic, while retaining verbatim provenance and a preregistered floor.
4. Re-run a synthetic adversarial fixture where long number-rich generated
   answers compete against short planted facts.
5. Preserve fixed seed, single-slot serving, deterministic model-visible IDs,
   and score-before-mechanism-log sequencing as the default protocol.
6. Defer retrieval diversification until a future run first passes the store
   content precondition.

An abstractive dreaming study is also premature. Extractive fidelity was not
the bottleneck; selection was. Generative summarization would add a
faithfulness problem before the simpler selection problem is solved.

## 9. Limitations

- One fixed seed and one 121-turn script establish a controlled paired result,
  not population-level performance.
- Manual scoring used one rater. Q5 and Q8 partial-credit judgments retain the
  prior rubric interpretation but remain judgment calls.
- The capitalized-sequence fallback is weaker than a trained NER model and can
  overcount formatted answer text.
- Token context estimates use character-based approximation.
- The full-run probe-bridge guard was not exercised.
- Completion stdout exposed short response fragments after each run, although
  all formal scoring used the hashed rubric response artifacts and preceded
  mechanism-log inspection.
- The treatment peak context was 61.6% larger than control because distilled
  episodes were longer; both remained far below the safety ceiling.

## 10. Conclusion

Study 005 moved selectivity to dreaming and made the experiment reproducible.
That produced a clean diagnosis. Extractive storage, provenance, cadence,
junk exclusion, compression, and retrieval all worked mechanically. The
episode-level salience policy did not retain enough rubric-critical facts.

The result is COMPLETE - PARTIAL: Bar 1 failed, Bar 2 is not evaluable, and Bar
3 failed. Active LTM retrieval is still not functionally validated. The next
study should stay extractive and fix span granularity and factual selection
before adding retrieval diversity or abstraction.

## Appendix A. Key artifacts

- Pre-registration: `experiments/study_005/pre_registration.md`
- Score lock: `experiments/study_005/evaluation/score_lock.md`
- Executable evaluator: `scripts/evaluate_study_005_full.py`
- Machine-readable results:
  `experiments/study_005/evaluation/study_005_results.json`
- Treatment mechanism analysis:
  `experiments/study_005/runs/study_005_full_001/condition_c/ltm_analysis/analysis_report.md`
- Runtime verification:
  `experiments/study_005/runtime/s5_001_runtime_verification.md`
- Synthetic verification:
  `experiments/study_005/tests/synthetic_verification_report.md`
- Ablation report: `experiments/study_005/ablation/ablation_report.md`

Raw databases, turn JSONL, retrieval JSONL, constructed prompts, and snapshots
remain preserved locally and ignored by Git. Curated responses, score sheets,
runtime manifests, dream logs, metrics, analysis, and reports are tracked.
