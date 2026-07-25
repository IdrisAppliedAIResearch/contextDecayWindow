# Study 005 — Pre-Registration (DRAFT v1)
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** LOCKED. All design decisions resolved; fixed seed selected before implementation or inference.
**Study 005 pre-registration SHA:** 20aa7707e780543ccbe462efadf3bb1263b3813e
**Study 004 paper:** `experiments/study_004/study_004_report.md` (COMPLETE, PARTIAL — 1 of 3 bars)
**Study 004 accepted v4 run:** `study_004_full_002` (7.0/13.0, Q14 0.0)
**Study 004 v3 control:** `v3_control_002` (11.0/13.0)

---

## Summary

Study 005 replaces Study 003's promotion policy with a different division of labor and introduces the pipeline's next stage, **dreaming**. Study 004 established that the LTM read path is mechanically sound — parallel retrieval, deduplication, tier-neutral arbitration, and tagged rendering all worked without defect — but that the store it read was populated by a promotion policy that admitted early and generic-novel episodes while rejecting the compact planted facts the breadth probes required. Retrieval faithfully served a store that did not contain the answers. The binding constraint is therefore memory *formation*, not retrieval.

Study 005 inverts the write path. Promotion stops being the selective gate. Instead:

- The **write path becomes a permissive, append-only raw episodic store** that keeps every turn, including non-content turns. The four Study 003 promotion filters (novelty, repetition, association, emotional) and the Study 004 association-decoupling revision are **retired**.
- **Dreaming becomes the selective stage.** It runs during the conversation, distilling the raw store into a compact LTM by extractive selection: it scores episodes for factual salience, deduplicates, enforces per-domain coverage under a salience floor, and writes selected episode spans — verbatim — to distilled LTM. Dreaming never generates new text.

This maps the biology more honestly than the prior design: fast, broad episodic capture, followed by sleep-time consolidation that distills a semantic layer. It also relocates selectivity — the function that failed at the Study 004 write gate — to the stage suited for it.

Because the read path was validated mechanically but never functionally (Study 004 could not show a breadth benefit from a store that lacked the facts), Study 005 is where the read path is finally tested against a store built to contain the right facts. A Study 005 breadth pass jointly validates dreaming (formation) and the carried-forward read path (retrieval).

The response budget (2,048, Amendment A005), runtime (UD-Q6_K_XL), and read-path/arbitration/tagging architecture are carried forward from the accepted Study 004 configuration. **Deterministic seeding is mandatory** (see Method).

---

## Research Questions

**Primary (confirmatory):** Does extractive dreaming produce a distilled LTM that contains the domains' salient planted facts (formation), and does retrieving that store recover four-domain breadth (payoff), without regressing targeted recall?

**Secondary (confirmatory):** Does the permissive-store / extractive-dream inversion hold targeted recall relative to a same-seed promotion-based baseline?

**Observational:** What does dreaming keep and discard — non-content rate in distilled LTM, compression ratio, per-domain coverage, provenance fidelity, and whether a compact distilled store makes retrieval-diversity mechanisms unnecessary?

---

## The one new component and the retirements

**New component: extractive dreaming (the selective stage).** Full specification below.

**Retired (this is a departure from the usual fix-plus-new-component split — dreaming *is* the promotion fix):**
- Study 003 promotion filters: novelty, repetition, association, emotional. Removed.
- Study 004 association-decoupling. Removed (sunset code).
- The weighted threshold, all-or-nothing bypass, and per-topic-centroid association machinery. Removed.

**Carried forward unchanged (accepted infrastructure):**
- Read path: parallel STM∥LTM retrieval, tier-neutral arbitration, episode-ID dedup, tagged context blocks (`<recent_context>`, `<retrieved_stm>`, `<retrieved_ltm>`, etc.). The LTM tier now queries **distilled LTM** (dreaming's output) instead of the promoted-episode store.
- Topic assignment (user-message embeddings, canonical consolidation mapping) — retained because dreaming needs topic boundaries to enforce coverage.
- Consolidation purity instrumentation and the probe-turn merge-bridge guard (Study 004 Bar 3 machinery).
- Runtime UD-Q6_K_XL, 2,048-token budget, 120,000 context, Qwen3-Embedding-0.6B.

---

## Changes from Study 004

| Parameter | Study 004 | Study 005 | Reason |
|-----------|-----------|-----------|--------|
| Write path | Selective promotion (4 filters + bypass) | Permissive append-only raw store; no write-time filter | Promotion rejected the planted facts; selectivity moves to dreaming |
| LTM population | Promoted episodes | Distilled records written by dreaming | Formation is the binding constraint |
| Selective stage | Promotion filters | Extractive dreaming | New component |
| Non-content turns | Filtered implicitly by promotion | Kept in raw store; dreaming expected to exclude them from LTM | Test whether dreaming subsumes junk-filtering; write-time filter deferred |
| Seeding | Stochastic (server defaults) | **Deterministic, fixed seed, single-slot** | Study 004's self-feedback property made unseeded runs measure trajectory noise |
| Retrieval diversity | None | Deferred/contingent (built only if a compact LTM still buries domains) | Compression may make it unnecessary |
| Tagged/read-off third arm | Requested by 004 report | Explicitly deferred | 005 changes the architecture wholesale; re-litigating 004's regression attribution is out of scope |

---

## Method

### Condition

**Condition C — Iterative Construction v5.** Per turn: the user message is stored to the raw episodic store; context is constructed by parallel STM∥LTM retrieval with arbitration (carried from v4), where the LTM tier queries distilled LTM. At each dream trigger, a dream pass runs over the raw store and updates distilled LTM before the next turn.

### Runtime and seeding (pre-registered)

| Parameter | Value |
|-----------|-------|
| Inference model | Qwen3.6 27B UD-Q6_K_XL |
| Runtime | Local llama.cpp HTTP server, /completion |
| Context capacity | **50,000 tokens (`--ctx-size 50000`)** |
| Response budget | 2,048 tokens |
| Embedding model | Qwen3-Embedding-0.6B Q8_0, 1024 dims |
| Server slots | Single-slot (`--parallel 1`) |
| RNG seed | **5005** |

**Pre-registered launch command (both arms, identical).** The llama.cpp server is launched with exactly these flags; the full command is recorded verbatim in each run header, and the server build/commit hash is recorded alongside:

```
--ctx-size 50000
--parallel 1
--cache-type-k q8_0
--cache-type-v q8_0
--flash-attn on
--jinja
--metrics
--temp 1
--top-p 0.95
--top-k 20
--min-p 0.0
--presence-penalty 0.0
--repeat-penalty 1.0
--seed 5005                   # REQUIRED, recorded in header
```

**Context capacity lowered to 50,000** (from the operator's 120,000) for VRAM headroom. Observed peak context was ~11k in Study 004 and ~10.7k in Study 003; Study 005 does not increase per-turn context (the permissive raw store lives in the database, not the window; retrieval is N + K + M=5 as in v4), so 50k is ≈4× the expected ceiling. `--ctx-size` is a capacity ceiling and is behaviorally inert as long as no run reaches it — at the ~11k operating point the model behaves identically at 50k or 120k — so lowering it does not confound the paired comparison or anything measured here. The tok/s benefit is VRAM-dependent (a smaller q8_0 KV cache frees ~7 GB) and is **confirmed, not assumed**: the pre-run speed test measures tok/s at 120k vs 50k and the faster is retained; if neutral, 50k stands as the harmlessly-safer choice.

Sampling is fixed at temp 1.0 / top-p 0.95 / top-k 20 / min-p 0.0 (Qwen3's intended sampling regime), penalties disabled, identical across the control and treatment arms.

**Two changes from the operator's default personal flags, made for reproducibility:**

1. **Speculative decoding removed.** The `--spec-type draft-mtp`, `--spec-draft-n-max`, and `--spec-draft-type-k/v` flags are dropped (default: off). Speculative decoding is a known source of run-to-run nondeterminism, and reproducibility is non-negotiable given Study 004's self-feedback finding. The speed cost is accepted.

2. **Fixed seed added.** `--temp 1` is not greedy, so reproducibility depends on a fixed RNG seed. The default seed is random; a fixed `--seed` is pre-registered and recorded in every run header. With temp 1 + fixed seed + `--parallel 1` + no speculative decoding, sampling is reproducible run-to-run.

KV-cache quantization (`--cache-type-k/v q8_0`) is retained (kept for the 120k context budget) and is deterministic run-to-run given fixed inputs; it is held identical across both arms so it cannot confound the paired comparison. It is a numerical setting that differs from any Study 004 default, so token-level outputs are not cross-comparable to pre-A005 runs — this does not affect any measured quantity here.

The determinism spot-check (re-run a fixed prefix under the same seed, assert turn-identical output) remains the gate. Any two arms sharing a seed are turn-identical until the first turn at which their constructed contexts diverge (empty-LTM turns 1–30 are identical across arms). Residual float nondeterminism is accepted.

### Script

121 turns, unchanged from Study 004: turns 1–120 hash-identical to Study 002/003, Q14 at turn 121. SHA-256 of the 121-turn script recorded in the run header and asserted equal to the Study 004 script hash.

### Evaluation

Manual scoring, single rater, on the locked 14-question rubric (Q1–Q13 `study_002/rubric_filled.md`; Q14 `study_004/q14_criteria.md`). Scores committed before any dreaming/arbitration logs are opened. In addition, two **pre-scoring structural checks** (facts-in-LTM, faithfulness) are computed from the distilled store and committed alongside scores — see Success Criteria.

---

## Extractive Dreaming (New Component) — full specification

This section is the implementation contract. No interpretive latitude is delegated. Dreaming is **extractive**: it selects and copies existing episode text; it does not call the inference model to generate or summarize. Generative/abstractive dreaming is a future study with its own faithfulness bars and is explicitly out of scope.

### Raw episodic store

Append-only. Every turn (user message + model response) is stored as an episode with: episode_id, turn, role, text, embedding, assigned_topic (from the carried-forward topic assigner), and a `dreamed` flag (initially false). No write-time filtering. Non-content turns ("got it", bare acknowledgments, rule-only turns) are stored like any other.

### Dream trigger cadence

A dream pass fires at each topic transition (≈ turns 31, 61, 91) and at the turn-111 flush point — the same cadence as Study 004 promotion, reusing that structure. This ensures distilled LTM is populated before the probe block (turns 112+). The turn-111 pass must complete and write before turn 112 begins (carried sequencing rule). Probe-block turns (112–121) are never dreamed.

### Dream pass algorithm (extractive)

At each trigger, for the topic(s) being consolidated at that event (the outgoing topic under the transition logic; at 111, the final active topic):

1. **Scope.** Collect raw-store episodes assigned to the topic with `dreamed == false`. Snapshot this set; freeze it for the pass.
2. **Salience score** per episode:
   ```
   salience(e) = named_entity_count(e) + 2 × numeric_token_count(e)
   ```
   - `numeric_token_count`: count of numeric tokens via regex (integers, decimals, units-adjacent numbers, years, measurements).
   - `named_entity_count`: count of named entities. Default extractor: spaCy `en_core_web_sm` NER if available; else a documented fallback (capitalized multi-word sequences excluding sentence-initial tokens and a stoplist). The chosen extractor is recorded in the run header.
   - Numbers are weighted ×2 because the planted facts are number-dense and numerals are rarer and more distinctive than capitalized nouns. **This weighting is a locked design choice, noted as a tunable in Limitations** (the Study 003 lesson: weights are choices, not truths).
3. **Deduplicate.** Within the scoped set, collapse near-duplicate episodes (pairwise cosine ≥ **0.95**); keep the higher-salience member. Record collapsed ids as provenance on the survivor.
4. **Select.** Rank survivors by salience; take the top **C = 3** per topic.
5. **Coverage under a salience floor.** Let **F = 2** (minimum salience to count as a salient fact — a bare acknowledgment scores 0 and fails F).
   - If the topic's top episode has salience ≥ F: write the selected records (≥1 guaranteed).
   - If **no** episode in the topic clears F: write a single marker record `{topic, status: "present_no_salient_fact", source: <highest-salience episode_id>}` — do **not** promote a sub-floor episode to satisfy coverage. This prevents recreating Study 004's generic-representative failure on a sparse topic.
6. **Write to distilled LTM.** Each distilled record stores: distilled_id, topic, verbatim text of the source episode span, provenance (source episode_id(s), source turn(s)), salience, dream_event. Mark source episodes `dreamed = true`.
7. **Extractive assertion.** The dream pass makes zero inference-model calls. Assert programmatically that distilled record text is a substring (or exact span) of a source episode; a distilled record that does not match a source episode verbatim is a hard failure.

### Distilled LTM and the read path

The read path's LTM tier queries distilled LTM (top-M by cosine similarity to the query embedding; M = 5 carried from v4). If a compact distilled store means M retrieves most of it on any query, breadth coverage may follow without a diversity mechanism — see the contingent retrieval fix.

### Locked dream parameters

| Parameter | Value | Rationale |
|-----------|-------|-----------|
| Per-topic cap C | 3 | 4 domains × 3 ≤ 12 records — comparable in size to Study 004's store but salience-selected |
| Salience floor F | 2 | Excludes non-content turns; a single entity-or-number pair clears it |
| Number weight | ×2 | Planted facts are number-dense; tunable |
| Dedup threshold | 0.95 cosine | Collapse near-identical restatements only |

All four are pre-registered and flagged tunable in Limitations.

---

## Baseline Corrections (from Study 004)

1. **Promotion selectivity failure → fixed by the inversion.** Permissive capture keeps the planted facts; extractive dreaming with salience-floored coverage selects them into LTM with a guaranteed per-domain slot (or an honest "no salient fact" marker). This is the headline correction.
2. **Error-cascade / path-dependence → controlled by mandatory seeding.** Seeding does not remove the self-feedback dynamic (generated episodes are stored and retrieved), but it makes runs reproducible and lets the control be a clean paired contrast rather than a noise comparison.
3. **Breadth-retrieval diversity → deferred/contingent.** Built only if the facts-in-LTM check passes but breadth still fails (see Success Criteria's disentanglement). Not built pre-emptively; compression may obviate it.
4. **Bar 3 probe-bridge guard unconfirmed-in-action (from the Study 004 analysis) → carried, still cheap, still unconfirmed unless exercised.** Reported honestly; not credited unless a probe-bridge merge is actually attempted and blocked.

---

## Success Criteria

Three bars. Baseline for the non-regression bar is a **same-seed promotion-based control** (the accepted Study 004 v4 architecture, seeded, at the v5 runtime) — see Control Run. The facts-in-LTM check makes the two causes of a breadth failure separable by construction, which is the study's central methodological gain.

### Bar 1 — Dream Formation (the new component's direct job)
**Distilled LTM contains a rubric-critical planted fact for at least 3 of the 4 domains, each traceable to a source episode (faithfulness), with zero non-content records.**
- The set of rubric-critical planted facts per domain is drawn from the existing plant key (the facts Q4/Q5/Q7/Q8/Q10 and the breadth probes depend on); the exact per-domain target list is enumerated in `q_facts_key.md`, committed with this pre-registration.
- This bar is checkable **independent of retrieval** — it reads the distilled store directly. It is the precondition Study 004 failed (that store had zero of the later-domain planted facts).
- "Zero non-content records" operationalizes the deferred-filter bet: if any sub-F / acknowledgment-class record reached LTM, dreaming failed at the junk-exclusion job assigned to it, and Bar 1 fails on that clause alone.

### Bar 2 — Breadth Recovery (the payoff), conditional on Bar 1
**Q11 ≥ 0.5 AND Q14 ≥ 0.5 AND (Q11 + Q14) ≥ 1.5, with the probe-turn arbitration log showing distilled-LTM records from the recovered domains.**
- **Store-content precondition (the Study 004 lesson):** Bar 2 is evaluated only if Bar 1 passes. If the planted facts are not in distilled LTM (Bar 1 fails), Bar 2 is recorded as **not evaluable — read path untested**, not "failed." A read-path bar is only meaningful given a store that contains the target facts.
- **Disentanglement:** if Bar 1 passes (facts are in LTM) and Bar 2 still fails, the cause is isolated to **retrieval** — this is the trigger to build the deferred breadth-diversity mechanism, and it is a clean, attributable result rather than the entangled Study 004 outcome.

### Bar 3 — Targeted Recall Non-Regression
**Q1–Q13 ≥ the same-seed promotion control's Q1–Q13 score, with Cat 1–3 held outright (early/middle/late targeted recall not below the control's per-category totals).**
- The comparison is against the **seeded** control, not Study 004's contaminated 7.0/13.0 (which was depressed by the unseeded error-cascade). With a shared seed, turns 1–30 are identical across arms and divergence begins at the first dream/promotion event, so the contrast isolates the write-path architecture.
- Targeted questions are served mainly by STM; the risk this bar guards is that distilled-LTM records displace or mislead on targeted recall. Category-analysis caveat carried from Study 003.

All three bars pass → VALIDATED. Bar 1 pass + Bar 2 not-evaluable is reported as such, not as failure. Mixed outcomes → PARTIAL, criteria unchanged.

---

## Auxiliary Control Run

**Purpose.** Same-seed promotion-based baseline for Bar 3; also a clean promotion-architecture reference under seeding (which Study 004 never had).

**Configuration.** The **accepted Study 004 v4 implementation** (promotion-based LTM, read path on, tagging on), run at the v5 runtime and the **same fixed seed and sampling** as the v5 treatment, same 121-turn script. This is a real committed architecture, not a flag-crippled v5 — so the flag-off objection from Study 004 does not apply. Run on the Study 004 accepted runner.

**Sequence.** Control and treatment both run under the fixed seed. Order does not gate (unlike Study 004, the internal facts-in-LTM check is the gate, not the control). Score both before opening dreaming/arbitration logs.

**Scoring.** Full 14-question rubric, same rater.

---

## Observational Measures (No Pass/Fail)

| Measure | Description |
|---------|-------------|
| Compression ratio | raw episodes evaluated : distilled records written, per dream event and overall |
| Non-content rate in LTM | count of sub-F / acknowledgment-class records reaching distilled LTM (Bar 1 requires zero; the count is also reported as a graded measure) |
| Per-domain coverage | distilled records per domain; count of "present_no_salient_fact" markers |
| Provenance fidelity | fraction of distilled records whose text matches a source episode verbatim (extractive assertion; must be 100%) |
| Dedup activity | near-duplicate collapses per event |
| LTM contribution & dedup at probes | carried Study 004 arbitration measures over the distilled store |
| Breadth retrieval anatomy | full candidate lists + provenance for Q11/Q14 — used for the Bar 2 disentanglement |
| Compactness vs diversity | distilled store size vs whether breadth recovered — evidence on whether the retrieval-diversity fix is needed |
| Seeding determinism spot-check | re-run a short prefix under the same seed; confirm turn-identical output |

---

## Pre-Run Checklist (Mandatory)

- [ ] GPU speed test > 30 tok/s on UD-Q6_K_XL, single-slot
- [ ] Server launched with the exact pre-registered flag set (no speculative decoding); full command + build hash recorded in the run header
- [ ] `--seed` set to the fixed value and recorded; determinism spot-check passes (identical prefix on re-run)
- [ ] Speed test compares tok/s at 120k vs 50k ctx-size; faster retained; chosen value recorded
- [ ] Context-ceiling monitor active: peak per-turn context logged; alert if any turn exceeds 80% of `--ctx-size` (40k)
- [ ] Raw store is append-only; a non-content turn is stored (not filtered) — verified
- [ ] Promotion filters / association-decoupling removed — verified absent from the write path
- [ ] Dream pass unit tests: salience scoring, ×2 number weight, dedup at 0.95, cap C=3, coverage floor F=2 including the sparse-topic marker path
- [ ] Extractive assertion: every distilled record matches a source episode verbatim; zero inference calls in the dream pass
- [ ] Dream cadence: passes fire at 31/61/91/111; distilled LTM non-empty before turn 112; turn-111 completes before 112
- [ ] Read path retargeted to distilled LTM; arbitration/dedup/tagging carried tests still pass
- [ ] facts-in-LTM harness + faithfulness harness run on synthetic data
- [ ] Purity instrumentation + probe-bridge guard carried and verified
- [ ] 35-turn ablation: all above reachable checks; GO/NO-GO documented

---

## Failure Conditions

| Condition | Meaning | Next action |
|-----------|---------|-------------|
| Bar 1 fails: planted facts absent from LTM | Dreaming's selection missed the facts | Inspect salience scores of the missed plants; the heuristic under-values them → revise salience (pre-registered), not thresholds post-hoc |
| Bar 1 fails: non-content records in LTM | Junk-exclusion bet failed | Add the deferred write-time filter; re-register |
| Bar 1 passes, Bar 2 fails | Facts in store, retrieval buried them | Build the deferred breadth-diversity retrieval fix — clean, attributable |
| Extractive assertion trips | A distilled record isn't verbatim from source | Stop; dreaming is fabricating/mangling; fix before any run |
| Bar 3 fails | Inversion hurt targeted recall vs seeded control | Examine which STM episodes the distilled store displaced |
| Determinism spot-check fails | Seeding not effective | Confirm `--seed` is set and single-slot; then diagnose serving/batch and float-reduction paths |
| Peak context approaches `--ctx-size` | A run nears the 50k ceiling (unexpected given ~11k peaks) | Treat as a deviation (the 2,048-budget lesson): stop, raise `--ctx-size`, re-run; never let a run silently truncate at the ceiling |

---

## Limitations

Single scripted run per arm, single rater. Salience heuristic (entity+2×number, F=2, C=3, dedup 0.95) is a set of locked design choices, not tuned values; the ×2 number weight especially is a judgment call. Extractive dreaming cannot fabricate but can mis-select; provenance-to-source catches mangling, not poor selection. Seeding controls but does not eliminate the self-feedback dynamic; residual float nondeterminism accepted. The read-path-vs-tagging regression from Study 004 remains unattributed (third arm deferred). Distilled store and retrieval evaluated only under this script and model. Dreaming here is extractive only; abstractive dreaming (and its faithfulness risks) is a separate future study.

---

## Resolved Decisions (all locked)

1. **Salience extractor:** use the documented capitalized-sequence fallback. Neither spaCy nor `en_core_web_sm` was installed on the run box at lock time; adding that dependency after the heuristic was specified would create avoidable environment drift.
2. **Bar 1 threshold:** at least 3 of 4 domains, with all-4 coverage reported as the stronger outcome.
3. **Control necessity:** run the same-seed promotion control using the accepted Study 004 v4 implementation.
4. **Plant key:** `experiments/study_005/q_facts_key.md`, authored and locked with this pre-registration.
5. **Fixed seed:** 5005, chosen as a mnemonic study-specific value before implementation, model serving, or inspection of Study 005 outputs.

---

## Appendix

- Study 005 pre-registration SHA: `20aa7707e780543ccbe462efadf3bb1263b3813e`
- Study 004 paper: `experiments/study_004/study_004_report.md`
- Study 004 pre-registration: `experiments/study_004/pre_registration.md`
- Amendment A005: `experiments/study_004/protocol_amendment_005_response_budget_and_v3_control.md`
- Authoritative rubric (Q1–Q13): `experiments/study_002/rubric_filled.md`
- Q14 criteria: `experiments/study_004/q14_criteria.md`
- Plant key: `experiments/study_005/q_facts_key.md`
- Pre-registration path: `experiments/study_005/pre_registration.md`
