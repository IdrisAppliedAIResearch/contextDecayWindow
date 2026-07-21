# Study 004 — Sprint Plan
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Pre-registration:** `experiments/study_004/pre_registration.md`
**Task numbering:** S4-T-001 onward
**Sprint numbering:** S4_001–S4_010
**Green light is reached at S4_007** (ablation GO). Sprints S4_008–S4_010 are the post-authorization run, scoring, and close.

**Reading order for the coding agent:** the pre-registration is the design contract. Where this plan and the pre-registration appear to differ, the pre-registration wins — stop and flag rather than reconciling silently. Do not introduce parameters, thresholds, or architectural choices not stated in one of the two documents.

---

## Dependency overview

```
S4_001  pre-reg lock + decision records + runtime swap
   │
S4_002  baseline corrections (Association decoupling, turn-111 flush, purity instrumentation)   ── independent of read path
   │
S4_003  XML-tagged context construction                                                          ── must land before read path integrates
   │
S4_004  LTM read path + arbitration + dedup (the new component)
   │
S4_005  logging + Q14 wiring
   │
S4_006  synthetic mini-script end-to-end verification                                            ── exercises flush, guard, breadth, decoupling
   │
S4_007  35-turn ablation on real script + GO/NO-GO   ◄── GREEN LIGHT
   │
S4_008  full 120-turn run (+ Q14 at turn 121)
S4_009  scoring + arbitration analysis
S4_010  report + memory files
```

Rationale for the order: the three baseline corrections (S4_002) touch the write path and consolidation and are independent of the read path, so they land and verify first. XML restructuring (S4_003) changes how context is assembled and must be in place before the read path writes into it. The read path (S4_004) is the new component and sits on top of both. Nothing that can be verified in isolation waits for the ablation.

---

## Sprint S4_001
### Pre-Registration Lock, Decision Records, Runtime Swap
**Goal:** Commit the locked pre-registration and Q14 criteria as a clean pre-registration. Write the two decision records the pre-registration references. Swap the runtime to UD-Q6_K_XL and confirm it serves.

---

#### S4-T-001 — Commit pre-registration and Q14 criteria

Copy `study_004_pre_registration.md` to `experiments/study_004/pre_registration.md` and `q14_criteria.md` to `experiments/study_004/q14_criteria.md`. Before committing, **verify the Study 003 pre-registration SHA** in the header and appendix against the live Study 003 paper header (`experiments/study_003/README.md` → pre-registration commit field). Correct it if it differs. Commit both files together with message: `"Study 004 pre-registration + Q14 criteria — contextDecayWindow [no implementation changes]"`. Record the resulting SHA in the pre-registration header.

**Acceptance criteria:**
- Both files exist under `experiments/study_004/`
- Study 003 SHA verified against the live 003 header (note in commit body: "003 SHA verified" or "003 SHA corrected from X to Y")
- Commit contains no implementation files
- Study 004 pre-registration SHA recorded in its own header

---

#### S4-T-002 — Write decision records

Create two records under `experiments/study_004/decisions/`:

1. `DECISION_association_decoupling_study004.md` — states the Study 003 finding (weighted route structurally unreachable; N+A complement capped at 0.35), the resolution (Option A: Association = max cosine similarity across per-topic LTM centroids, Novelty unchanged), the rejected alternatives (rebalance weights; re-register as bypass detector) with one line each on why rejected, the bypass-exclusion sub-decision, and the known single-topic degeneracy. Author-authorized line required (this is the amendment-attribution hygiene item carried from Study 003).

2. `DECISION_runtime_revert_study004.md` — states that NVFP4 (Study 003) showed capability loss in offline testing, the revert to UD-Q6_K_XL as the strongest quant fitting the 32 GB GPU, and that this supersedes the NVFP4-as-standing-baseline decision. One line noting the comparison chain now spans Q6_K / NVFP4 / UD-Q6_K_XL and that the 12/13 baseline is therefore a soft floor. Author-authorized line required.

**Acceptance criteria:**
- Both records committed under `experiments/study_004/decisions/`
- Each carries an explicit author-authorization line
- The pre-registration's references to these paths resolve

---

#### S4-T-003 — Runtime swap and speed test

Point the study runner at Qwen3.6 27B UD-Q6_K_XL on the local llama.cpp HTTP server (/completion endpoint). Confirm the embedding model is unchanged (Qwen3-Embedding-0.6B Q8_0 GGUF, 1024 dims). Run the GPU speed test: generate 200 tokens, record tok/s.

**Acceptance criteria:**
- Server serves UD-Q6_K_XL and responds on /completion
- Embedding model and dimensionality unchanged from Study 003
- Speed test > 30 tok/s (if below, stop and diagnose before any further sprint)

---

**Sprint S4_001 complete when:** pre-registration + Q14 committed with verified SHA, both decision records committed, runtime serving UD-Q6_K_XL above the speed floor.

---
---

## Sprint S4_002
### Baseline Corrections (Write Path and Consolidation)
**Goal:** Land the three fixes from Study 003 that are independent of the read path: Association decoupling, end-of-session flush, and consolidation purity instrumentation with the probe-turn guard. Each is unit-tested before the read path is touched.

---

#### S4-T-004 — Association decoupling (Fix 3, Option A)

Implement the revised Association filter per pre-registration Fix 3. This replaces the global-centroid Association only; Novelty, Repetition, Emotional, the weights, and both thresholds are unchanged.

```
A(e) = max over t in LTM_topics of cosine_similarity(embedding(e), centroid(t))
```

Implementation contract (all from the pre-registration — do not reinterpret):
1. `LTM_topics` = canonical topic groups in the LTM store at batch-snapshot time. Each LTM row's stored `topic` label is resolved through the **current canonical consolidation mapping** before grouping; rows resolving to the same canonical topic pool into one group; one centroid = mean of member embeddings; group size 1 permitted.
2. Association is the **max** over per-topic centroids, **not** the outgoing episode's own topic (which is absent from LTM at promotion time by construction).
3. Empty LTM → A = 0.0. Empty-LTM bypass suspension unchanged for all filters.
4. Snapshot discipline: all per-topic centroids and the global centroid computed once at batch start, frozen for the batch, recomputed only after all batch writes complete.
5. Association is **excluded from the all-or-nothing bypass**. Bypass-eligible: novelty, repetition, emotional. Association acts through the weighted route only.

**Required unit tests (mirror pre-registration list):**
- Empty LTM → A = 0.0
- Single-topic LTM → A = cos(e, c₁), N = 1 − cos(e, c₁) (documented complement case)
- Two-topic LTM → A = max of the two, not the mean
- Post-merge grouping: two rows with different stored labels resolving to one canonical topic → one pooled centroid
- Snapshot: A identical for every episode in a batch even as promotions write mid-batch
- A = 0.95, all else 0, LTM non-empty → NOT promoted (bypass excludes association); weighted = 0.19 → not promoted

**Acceptance criteria:**
- All six unit tests pass
- No change to Novelty/Repetition/Emotional scoring, weights, or thresholds (diff-reviewed)

---

#### S4-T-005 — End-of-session promotion flush

Add a promotion pass at **turn 111** (last turn before the probe block) that evaluates the currently active topic's not-yet-promoted episodes against the standard filter path (including the revised Association), using the batch-snapshot centroids. Turns 112–121 remain excluded from event emission (Amendment 004 carried forward).

**Sequencing (binding):** the turn-111 flush must complete and write before the turn-112 probe turn begins, so probe-time LTM retrieval sees the full four-domain store.

**Acceptance criteria:**
- A flush event fires for the active topic at turn 111 even though no topic transition occurs there
- Flush uses the same evaluation path as transition-triggered promotion (no divergent logic)
- Flush completes before turn 112 (assert ordering in the runner; unit test the guard that blocks turn 112 until flush returns)
- Probe-block emission suppression still holds (no promotion events at turns 112–121)

---

#### S4-T-006 — Consolidation purity instrumentation and probe-turn guard

Two pieces.

**(a) Cross-domain merge detection.** The script assigns every turn a ground-truth domain (civil engineering / Renaissance art / monetary policy / marine biology). Instrument consolidation so that whenever a merge occurs, the ground-truth domains of the two merged clusters' member episodes are compared. A merge joining episodes whose ground-truth domains differ is logged as a `cross_domain_merge` event with turn, the two labels, and the connecting similarity. This is the instrument for Bar 3's zero-cross-domain-merge clause.

**(b) Probe-turn merge-bridge guard.** Episodes generated at turns 112–121 may be assigned to topics but must not act as merge bridges: reject any merge whose connecting similarity path runs through a probe-turn episode. Log each rejected merge as a `probe_bridge_blocked` event.

**Acceptance criteria:**
- `cross_domain_merge` events written to `consolidation_purity.csv` with all fields; zero such events on clean same-domain synthetic data, ≥1 on deliberately mixed synthetic data (test both)
- Probe-turn guard rejects a synthetic merge bridged by a turn-115 episode and logs `probe_bridge_blocked`
- Non-probe merges are unaffected by the guard (regression check on turns < 112)

---

**Sprint S4_002 complete when:** Association decoupling unit-tested, turn-111 flush firing with verified ordering, purity instrumentation and probe guard verified on synthetic data.

---
---

## Sprint S4_003
### XML-Tagged Context Construction
**Goal:** Restructure the constructed context into the pre-registered tagged blocks, with faithful post-arbitration placement. This lands before the read path so the read path writes into a known structure.

---

#### S4-T-007 — Implement tagged block rendering

Render the constructed context as the five ordered blocks from the pre-registration: `<pinned_rules>`, `<recent_context>`, `<retrieved_stm>`, `<retrieved_ltm>`, `<current_turn>`. Until the read path lands (S4_004), `<retrieved_ltm>` renders empty (self-closing) — that is correct and expected at this sprint.

Binding placement rules (from pre-registration):
1. Provenance `stm` → `<retrieved_stm>`; provenance `ltm` or `both` → `<retrieved_ltm>` (once, with LTM metadata). Never duplicate a `both` episode into both blocks.
2. Empty block → self-closing tag, never omitted.
3. An episode qualifying for both recency (N) and similarity (K) is placed in `<recent_context>` only.
4. Attribute values are metadata only (turn, topic, similarity, promoted_at_turn, trigger_type). No filter scores or arbitration internals in the context.

**Acceptance criteria:**
- Snapshot test: given a fixed retrieval set, the rendered context string matches an expected tagged fixture exactly (byte-for-byte on structure; content substrings verified)
- Empty `<retrieved_ltm/>` renders self-closing when no LTM episodes present
- Recency/similarity dedup rule verified (an episode in both N and K appears once, in recent_context)
- No numeric scores leak into any tag attribute (assert)

---

**Sprint S4_003 complete when:** tagged rendering passes the snapshot test with correct empty-block and dedup behavior; LTM block renders empty pending the read path.

---
---

## Sprint S4_004
### LTM Read Path + Arbitration (New Component)
**Goal:** Activate parallel STM∥LTM retrieval with an arbitration layer that deduplicates, tags provenance, and ranks by similarity alone. This is the component under test. The degenerate fallback must fall out of the general mechanism correctly.

---

#### S4-T-008 — Parallel retrieval

On each turn, after the user message is embedded, issue two queries concurrently and await both:
- STM: existing N + K (unchanged parameters)
- LTM: top-M = 5 promoted episodes by cosine similarity to the query embedding

Use the established async pattern (e.g. `asyncio.gather`), respecting the existing inference/embedding lock. The LTM query reads the LTM store's embeddings; it must not mutate the store.

**Acceptance criteria:**
- Both queries issued concurrently and jointly awaited (not sequential)
- LTM query returns ≤ 5 episodes ranked by similarity
- LTM query is read-only (store row count unchanged across a query; assert)
- With an empty LTM store, LTM query returns an empty list without error

---

#### S4-T-009 — Arbitration: dedup, provenance, ranking

Implement the arbitration layer that consumes the STM and LTM candidate sets and produces the final retrieval set.

Binding sequence:
1. **Dedup before ranking**, on `episode_id`. An episode present in both sets survives once. Provenance tag: `stm` (STM only), `ltm` (LTM only), `both` (both). A promoted episode must never receive two votes.
2. **Rank** the deduplicated union by cosine similarity to the query embedding, **tier-agnostic** — equal similarity means equal rank regardless of source. No tier boost.
3. **Cap** at K_total = K_stm + M, subject to the context budget.
4. Hand off to the tagged renderer (S4-T-007) with provenance preserved.

**Acceptance criteria:**
- Dedup unit test: an episode in both sets appears exactly once in the output, provenance `both`
- No-tier-bias test: an STM and an LTM candidate with identical similarity rank adjacently by similarity, not by tier
- Cap test: union larger than K_total is truncated to the top K_total by similarity
- Provenance survives into the rendered context (a `both` episode lands in `<retrieved_ltm>` with LTM metadata, per S4-T-007 rule 1)
- Dedup violation is impossible to emit: add an assertion that no episode_id appears twice in the final set; test that it never trips on the real retrieval path

---

#### S4-T-010 — Degenerate fallback correctness

The fallback (LTM-only-when-STM-empty) must be the degenerate case of the general mechanism, not a separate branch. Verify: with the STM K set empty (and N reduced to nothing retrievable beyond the current turn), arbitration output equals the LTM-only ranking. There must be no special-case code path for "STM empty."

**Acceptance criteria:**
- With K_stm empty, final set = LTM top ranked by similarity (equality test against a direct LTM-only ranking)
- Grep/diff review confirms no `if stm_empty:` style special-casing in arbitration
- With both tiers empty, final set is empty and context renders all-empty retrieval blocks without error

---

**Sprint S4_004 complete when:** parallel retrieval concurrent and read-only, arbitration dedups and ranks tier-agnostically with a no-double-vote assertion, and the degenerate fallback provably equals LTM-only ranking with no special-casing.

---
---

## Sprint S4_005
### Logging and Q14 Wiring
**Goal:** Emit the arbitration and provenance logs that make Bar 1 attributable, and insert Q14 at turn 121.

---

#### S4-T-011 — Arbitration and provenance logging

Write per-turn to `arbitration_events.csv`: turn, stm_candidates, ltm_candidates, duplicates_removed, final_set_size, ltm_episodes_in_final_set, provenance_list. Additionally, every LTM episode that reaches the constructed context is logged with its promoted_at_turn and trigger_type. This is the record Bar 1's attribution requirement reads.

**Acceptance criteria:**
- `arbitration_events.csv` has one row per turn with all fields
- duplicates_removed equals the count dropped by dedup (cross-checked against a turn with a known `both` episode)
- Every LTM-in-context episode is individually logged with promotion provenance
- Header + rows verified on the synthetic run (S4_006), not first seen at the real ablation

---

#### S4-T-012 — Q14 insertion and rubric extension

Insert Q14 (from `q14_criteria.md`) as **turn 121**, after Q13 and after all Study-003-equivalent probes. Turns 1–120 must remain byte-identical to the Study 002/003 script — verify by hashing the turns 1–120 payload against the Study 003 script. The rubric becomes 14 questions; non-regression (Bar 2) is evaluated on Q1–Q13 only, breadth (Bar 1) on Q11 + Q14.

**Acceptance criteria:**
- Turns 1–120 hash-identical to the Study 003 script payload
- Q14 delivered at turn 121 with the exact text from `q14_criteria.md`
- The turn-111 flush precedes the probe block; Q14 at 121 sees the full store
- Scoring harness records Q14 on the 0/0.5/1.0 scale; Bar arithmetic wired (Q11+Q14 ≥ 1.5, each ≥ 0.5)

---

**Sprint S4_005 complete when:** arbitration logging faithful and Q14 wired at turn 121 with the turns 1–120 payload proven unchanged.

---
---

## Sprint S4_006
### Synthetic Mini-Script End-to-End Verification
**Goal:** Exercise every new mechanism end-to-end on a purpose-built synthetic script before the real ablation — so the ablation is not the first firing of the read path, the flush, the guard, or the decoupled Association.

---

#### S4-T-013 — Author the synthetic verification script

Create `experiments/study_004/tests/synthetic_study004_script.json`. Requirements — the script must, in a compact turn budget (~24 turns), produce all of the following conditions:
- **At least three distinct topics** before a promotion batch, so LTM holds ≥ 2 topics when a later batch is evaluated (exercises Association max-over-per-topic-centroids, not the single-topic degeneracy).
- **A repeated/retrieved fact** in an early topic so Repetition has signal.
- **A breadth query** near the end demanding a specific from each topic (miniature Q11/Q14) so the read path's breadth behavior is observable.
- **A final active topic with no outgoing transition**, plus a designated flush turn, to exercise the end-of-session flush.
- **A short probe block** at the tail (≥ 2 turns) including one turn crafted to bridge two topics, to exercise the probe-turn merge guard.

This is a test fixture only; it never touches run data.

**Acceptance criteria:**
- Script produces ≥ 3 topics and a ≥ 2-topic LTM state before the final batch
- Contains a breadth query, a flush point, and a probe-block bridge turn
- Committed under `tests/`, documented as fixture-only

---

#### S4-T-014 — Run synthetic end-to-end and verify

Run the synthetic script through the full Study 004 architecture (real embeddings, real consolidation, real LLM emotional scoring, real arbitration — no mocks). Verify:

| Check | Expected |
|-------|----------|
| Parallel retrieval | Both tiers queried concurrently; LTM returns candidates once populated |
| Dedup | A `both` episode appears once; `duplicates_removed` > 0 on at least one turn |
| Provenance in context | LTM episode rendered in `<retrieved_ltm>` with metadata; STM-only in `<retrieved_stm>` |
| Degenerate fallback | On a turn with empty K_stm, final set equals LTM-only ranking |
| Association decoupling | On a ≥2-topic-LTM batch, logged A = max per-topic similarity and differs from what a global-centroid A would produce (assert the two are computed and unequal on ≥1 episode) |
| Bypass exclusion | No promotion attributed to an association all-or-nothing trigger |
| Turn-111-equivalent flush | Final active topic promoted at the designated flush turn; no events during the probe block |
| Probe guard | The bridge turn's merge is rejected and logged `probe_bridge_blocked` |
| Cross-domain merge instrument | `consolidation_purity.csv` written; correctly flags a deliberately mixed merge if present |
| Tagged rendering | All five blocks present every turn; empty blocks self-closing |
| Logs | `arbitration_events.csv` populated with correct per-turn fields |

Document results in `experiments/study_004/tests/synthetic_verification_report.md`.

**Acceptance criteria:**
- All checks pass
- Report committed
- Any failure: stop, fix, re-run before proceeding to the real ablation

---

**Sprint S4_006 complete when:** every new mechanism is verified end-to-end on the synthetic script and the report is committed.

---
---

## Sprint S4_007
### 35-Turn Ablation + GO/NO-GO — GREEN LIGHT
**Goal:** Run the mandatory ablation on the real script and produce the go/no-go decision. This sprint authorizes (or blocks) the full run.

---

#### S4-T-015 — Run 35-turn ablation on the real script

Run turns 1–35 of the real script under the full Study 004 architecture. 35 turns reaches the first topic change (≈ turn 31), so LTM becomes non-empty and the read path can be exercised from ≈ turn 32. Note the mechanisms that **cannot** be exercised at 35 turns on the real script — the turn-111 flush, the probe-turn guard, multi-topic Association decoupling, and Q14 — were verified on the synthetic script in S4_006; the ablation confirms the real-script integration of what is reachable by turn 35.

Inspect and document in `experiments/study_004/ablation/ablation_report.md`:

| Check | Expected | Actual | Pass? |
|-------|----------|--------|-------|
| GPU speed (UD-Q6_K_XL) | > 30 tok/s | | |
| Consolidation fires | At least once | | |
| Topic count at turn 35 | Trending toward the [3,10] band pace | | |
| Cross-domain merges | Zero (`consolidation_purity.csv`) | | |
| First LTM promotion | At ≈ turn 31 | | |
| Decoupled Association computed | A logged as max-per-topic on the turn-31 batch (single-topic case documented) | | |
| Parallel retrieval active | Both tiers queried from ≈ turn 32 | | |
| LTM episode reaches context | ≥ 1 LTM-provenance episode in a post-31 constructed context | | |
| Dedup correct | No episode_id twice in any final set; `duplicates_removed` sane | | |
| Degenerate fallback | Verified on at least one low-STM turn or by the S4-T-010 test re-run | | |
| Tagged blocks | All five present each turn; empty blocks self-closing | | |
| `arbitration_events.csv` | Populated, all fields | | |
| No promotion during any probe (n/a < 112) | No probe turns in range — confirm N/A | | |

**Acceptance criteria:**
- All applicable checks pass
- Ablation report written and committed
- Any failure: stop, diagnose, fix, re-run the ablation from scratch

---

#### S4-T-016 — Go/No-Go decision (GREEN LIGHT)

Write one line to the ablation report:

```
DECISION: GO — all applicable checks passed; synthetic verification (S4_006) covered flush/guard/decoupling/Q14. Full 120-turn run authorized.
```
or
```
DECISION: NO-GO — [check] failed. Reason: [...]. Fix required before proceeding.
```

Commit the report with the decision before any run code executes.

**Acceptance criteria:**
- Explicit GO or NO-GO recorded and committed
- On GO: this is the green light. Proceed to S4_008.

---

**Sprint S4_007 complete when:** ablation report committed with a GO decision and all applicable checks passing. **← GREEN LIGHT**

---
---

## Sprint S4_008
### Full 120-Turn Run (+ Q14 at Turn 121)
**Goal:** Execute the full Study 004 run. Log everything. Do not score during the run.

---

#### S4-T-017 — Prepare run directory

Create `experiments/study_004/runs/run_001/` mirroring the Study 003 layout, adding `logs/arbitration_events.csv`, `logs/consolidation_purity.csv`, and an `ltm_analysis/` subtree. All log handles open before turn 1.

#### S4-T-018 — Execute the run

Run turns 1–120 plus Q14 at turn 121 under Condition C v4. Log every turn's context token count, K retrieval, LTM retrieval, arbitration event, consolidation event, topic assignment, promotion event (including the turn-111 flush), and every guarded merge. Write model responses turn-by-turn.

Monitoring: do not interrupt except per the Study 003 monitoring rules (context > 20k tokens → note and continue; ≥ 3 consecutive empty/truncated responses → stop and report). The turn-111 flush must complete before turn 112. Q14 fires at 121.

**Acceptance criteria:**
- 121 turns complete without crash (120 + Q14)
- `responses.md` has 121 entries; `context_sizes.csv` 121 rows
- Three transition promotion events (≈31/61/91) plus one turn-111 flush event
- `arbitration_events.csv` has 121 rows; LTM-in-context provenance logged
- Peak context recorded

---

## Sprint S4_009
### Scoring and Arbitration Analysis
**Goal:** Score the 14-question rubric manually (Q1–Q13 on the locked criteria, Q14 on `q14_criteria.md`), evaluate the three bars, then analyze arbitration data — scoring committed before analysis opens.

---

#### S4-T-019 — Extract and score

Extract the probe responses; score Q1–Q13 against `experiments/study_002/rubric_filled.md` and Q14 against `q14_criteria.md`. Commit scores before opening any arbitration logs.

#### S4-T-020 — Evaluate bars

| Bar | Criterion | Observed | Pass? |
|-----|-----------|----------|-------|
| 1 | Q11 ≥ 0.5 AND Q14 ≥ 0.5 AND (Q11+Q14) ≥ 1.5, with LTM-provenance episodes attributable in probe-turn contexts | | |
| 2 | Q1–Q13 ≥ 12.0/13.0, Cat 1–3 ≥ 3.0/3.0/2.0, Cat 5 ≥ 2.0 | | |
| 3 | Turn-121 topic count in [3,10] AND zero cross-domain merges | | |

Apply the category-analysis caveat to any Bar 2 miss before verdict. Record the confirmatory outcome (VALIDATED / PARTIAL / FAILED).

#### S4-T-021 — Arbitration analysis

Compute the observational measures: LTM contribution rate, dedup rate, tier-overlap profile, displacement events, breadth-turn retrieval anatomy (Q11 and Q14 full candidate lists with provenance), turn-111 flush behavior, revised weighted-route activity (did the weighted route fire post-decoupling?), latency delta vs Study 003. Document in `ltm_analysis/analysis_report.md`. Do not interpret as pass/fail.

---

## Sprint S4_010
### Report and Memory Files
**Goal:** Write the Study 004 report; update both memory files; close the study.

---

#### S4-T-022 — Write the report

`experiments/study_004/study_004_report.md`, Study 003 structure: summary (result), questions, changes from 003, method, results (14-question rubric, bar table), discussion (breadth recovery and its attribution, non-regression under the confound stack, purity, weighted-route revival, flush behavior), what I'd do differently, protocol notes, limitations, next steps, appendix. The discussion must state explicitly whether Bar 1 passes were attributable to LTM provenance.

#### S4-T-023 — Update memory files

Update `MUZAFFER_PROFILE.md` and `CLAUDE_CONTEXT.md`: **first correct the stale "Study 003 ready for S3_001" state to Study 003 COMPLETE/PARTIAL** (this was outstanding), then record Study 004's result, the runtime now at UD-Q6_K_XL, and the next component in the pipeline (dream-cleaning / async parallel retrieval per the brain-pipeline target). Update timestamps.

#### S4-T-024 — Close study

Final checklist: report committed; memory files updated; run logs archived under `runs/run_001/`; arbitration and purity CSVs committed; ablation report committed; both decision records committed; synthetic verification report committed; pre-registration SHA confirmed in the report header.

---
---

## Summary

| Sprint | Scope | Output | Gate |
|--------|-------|--------|------|
| S4_001 | Pre-reg lock, decision records, runtime swap | SHA recorded, records committed, UD-Q6_K_XL serving | speed > 30 tok/s |
| S4_002 | Baseline corrections (Association decouple, flush, purity) | Three fixes unit-tested | all tests pass |
| S4_003 | XML-tagged context | Tagged rendering | snapshot test |
| S4_004 | LTM read path + arbitration + dedup | New component | no-double-vote assertion; fallback equals LTM-only |
| S4_005 | Logging + Q14 | Arbitration logs, Q14 at 121 | turns 1–120 hash-identical |
| S4_006 | Synthetic end-to-end | Verification report | all mechanisms fire |
| **S4_007** | **35-turn ablation + GO/NO-GO** | **Ablation report** | **← GREEN LIGHT** |
| S4_008 | Full 120-turn run (+Q14) | Logs, responses | 121 turns, no crash |
| S4_009 | Scoring + arbitration analysis | Bars evaluated | scores before analysis |
| S4_010 | Report + memory files | Study closed | all committed |
