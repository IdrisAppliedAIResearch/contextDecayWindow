# TC-005 Pre-Registration — relevance efficiency under a half-budget

**Status:** `PRE-REGISTERED — OFFLINE AVAILABILITY STUDY`  
**Date locked:** August 23, 2026  
**Design and Preflight commit:** `d1ad648135c4fb82560ad7ae90a33248fe32d7f0`  
**Preflight Part 1 SHA-256:** `2687d48812d8862f7c0ff2ebe5abe6bd8011f136deb38efaacf34958296ba584`  
**Preflight PF4 SHA-256:** `c44a96b52ec796f06a9507b31b987d6bb1f9d17976f8134823a485d707c67b4d`  

This file is the authoritative parameter source. It is immutable after this
commit. Any genuine protocol correction requires a standalone amendment; no
observed result may change an arm, endpoint, population, budget, bar,
guardrail, tie-break, or selection rule below.

## 1. Question and claim boundary

Holding the LoCoMo adjacent-turn-pair candidates, query, dense vectors,
renderer, skip-on-overflow packer, and exact character budgets fixed, does
carried BM25 or carried dense-plus-sparse RRF deliver complete required
evidence for more direct, single-carrier questions than the current dense order
when relevance receives TC-007's 8,000- or 16,000-character half-budget?

This is an offline evidence-availability study. It can freeze one relevance
ordering for TC-007. It cannot establish reader accuracy, an optimal or
adaptive budget, unseen-corpus transfer, enterprise-scale latency, production
adoption, or a benefit from protected spread.

## 2. Frozen inputs and population

- Corpus: LoCoMo SHA-256
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Development conversations: `conv-41`, `conv-42`, `conv-47`, `conv-48`.
- Candidate unit: the same 1,365 adjacent-turn pairs used by TC-001 through
  TC-004, with content-derived identities and unchanged text.
- Question key: content SHA-256 plus frozen duplicate ordinal. Generated ids,
  paths, and timestamps are forbidden comparison keys.
- Unique questions: 871.
- Eligible questions: 868 — duplicate ordinal zero, at least one resolved
  evidence id, and no unresolved evidence id.
- Primary targeted population: 704 eligible questions whose complete evidence
  is confined to one adjacent-turn pair in one session.
- Descriptive breadth population: 44 eligible questions whose evidence spans
  at least three sessions.
- Other eligible population: 120. Ineligible: 3.

The question-visible diagnostic split is frozen before outcomes:
`surface_literal` iff the question contains a digit, currency/percent symbol,
double quotation mark, or all-uppercase token of at least two letters;
otherwise `paraphrase`. Its observed sizes are 169 and 702. It carries no bar
and cannot select an arm.

## 3. Arms — the only treatment change is order

All arms rank the complete candidate store for that conversation. They have no
threshold, top-k cut, coverage floor, recency insertion, or post-ranking
reorder. Conversation order `(session_order, pair_order)` breaks every score
tie.

| Arm | Frozen ordering |
|---|---|
| `A_DENSE` | Descending carried normalized float32 query/candidate matrix product, identical to TC-001 `A_FLAT` |
| `A_BM25` | Descending carried Unicode-casefold BM25 score, `k1=1.2`, `b=0.75` |
| `A_HYBRID` | Descending one-based RRF score `1/(60+dense_rank) + 1/(60+bm25_rank)` |

The BM25 tokenizer/formula and RRF formula are the carried retrieval-bakeoff
implementation. The common LoCoMo conversation tie-break replaces the prior
UUID tie-break for all three arms and is part of this registration.

Normalized dot and Euclidean distance are the same objective in exact
arithmetic. Preflight measured float64 dot/Euclidean order identity on 871/871
queries and carried-float32 agreement on 868/871. Numerical precision variants
are not additional arms.

## 4. Renderer, packer, cost, and budgets

Every arm uses the committed DR-001 episode renderer and
`episodic._packing.pack_stm_payload` with an empty recency block. Candidates are
considered in arm order, charged at exact serialized character cost including
wrappers and separators, skipped on overflow, and never truncated. Final
payload length must not exceed its budget.

- Primary half-budgets: **8,000 and 16,000 characters**.
- Secondary full-budget anchors: **16,000 and 32,000 characters**.
- The 16,000-character payload is generated once and carries two labels: the
  larger TC-007 arm's half-budget and the smaller total's full-budget anchor.
  It is not generated or counted twice.

These are continuity and successor operating points, not claimed production
optima.

## 5. Endpoints and recorded rows

The binding endpoint is question-level **complete required-evidence delivery**:
every adjacent-turn pair carrying any resolved required evidence for the
question is present in the serialized payload. The primary endpoint is this
boolean on the 704 targeted questions at 8k and 16k.

Secondary endpoints are any-evidence delivery; complete delivery on all 868
eligible questions; the 44 breadth and 120 other populations separately; the
16k/32k full-budget anchors; delivered characters and candidate count; best
and worst required-evidence ranks; and the frozen surface diagnostic. None may
override the binding disposition.

For every question, arm, and unique budget, record the ranking digest, ordered
candidate content identities, dense score/rank, BM25 score/rank, fused
score/rank, selected identities, skipped identities and reasons, exact payload
characters, required-evidence identities/ranks, and complete/any booleans.

## 6. Contrasts, bands, and multiplicity

The four primary directional contrasts are:

- `C1`: `A_BM25 - A_DENSE` at 8k, targeted complete evidence.
- `C2`: `A_BM25 - A_DENSE` at 16k, targeted complete evidence.
- `C3`: `A_HYBRID - A_DENSE` at 8k, targeted complete evidence.
- `C4`: `A_HYBRID - A_DENSE` at 16k, targeted complete evidence.

The four full-budget guardrail contrasts repeat BM25/dense and hybrid/dense on
the 868-question combined eligible population at 16k and 32k. The family has
eight directional tests. For each paired contrast, report treatment-only
complete deliveries as gains, dense-only deliveries as losses, ties, net
`gains-losses`, and the exact one-sided sign-test tail in the direction being
tested.

- Works family alpha: `0.01 / 8 = 0.00125`.
- Carries-signal family alpha: `0.10 / 8 = 0.0125`.
- Budget-specific practical bands from dense-only shams:
  `{8000: 1, 16000: 2, 32000: 0}`.
- A directional win clears a budget only when its net is **strictly greater**
  than that budget's band and its one-sided exact p-value is at or below the
  applicable alpha.
- A full-budget guardrail fails only when the adverse dense direction clears
  both that budget's practical band and the works alpha. A small or
  statistically unresolved adverse net is reported but does not fire the
  guardrail.

PF4 established that both candidate-exclusive directions exist for all 704
targeted and all 868 combined eligible questions at every budget, so every bar
and guardrail branch is mechanically reachable.

## 7. Per-treatment dispositions

Apply this table separately to `A_BM25` and `A_HYBRID` against `A_DENSE`, in the
listed order.

1. `TREATMENT_WORKS`: treatment direction clears the works bar at **both** 8k
   and 16k primary contrasts, and neither full-budget guardrail fails.
2. `DENSE_WORKS`: dense direction clears the works bar at both primary
   budgets. This is reported even if a secondary treatment guardrail is benign.
3. `TREATMENT_CARRIES_SIGNAL`: neither works branch fired; treatment direction
   clears the signal bar at at least one primary budget, the other primary
   budget has treatment-minus-dense net at least the negative practical band,
   and neither full-budget guardrail fails.
4. `DENSE_CARRIES_SIGNAL`: symmetric signal rule in the dense direction.
5. `MIXED_OR_NO_DIFFERENCE`: every remaining pattern, including opposite
   directional wins across the two half-budgets.

The lower tier is descriptive successor evidence only. It is not rounded up to
`WORKS` and cannot select a TC-007 input.

## 8. Frozen TC-007 selection rule

Only a treatment with `TREATMENT_WORKS` is eligible to replace dense.

- If exactly one treatment works, select it.
- If both work, select the larger sum of the two targeted nets at 8k and 16k.
- If tied, select the smaller summed loss count across those two contrasts.
- If still tied, select the larger worst-budget targeted net.
- If still tied, select `A_HYBRID`.
- If neither treatment works, select the frozen fallback `A_DENSE`, regardless
  of a carries-signal disposition or a full-budget-only win.

Thus a full-budget win cannot select a half-budget loser, and "measurably
better than flat" is required before TC-007 inherits a new relevance strategy.

## 9. Gates and execution order

### G0 — reproduction and integrity, binding before outcomes

G0 must be generated and committed before the outcome phase exists in an
eligible run state. It must pass all of the following:

1. the pre-registration is committed and byte-identical to its registered
   SHA-256;
2. both Preflight artifacts match the header hashes;
3. all 1,742 TC-001 dense question-budget payload checks reproduce;
4. all 288 prior M2/M3/M4 selected-identity lists and payload digests reproduce
   under the frozen one-thread call shape;
5. the LoCoMo read-only cache has zero misses;
6. no mechanism source imports or reads a rubric/key artifact, with a planted
   violation proving the leakage check can fail;
7. the exact study script and source hashes are recorded;
8. LLM/generative calls equal zero and embedding calls are reported separately;
9. the full test suite passes; and
10. the repository is clean and the G0 artifact is committed before `run` is
    accepted.

Any failure stops the study as `INSTRUMENT_FAILURE`; labelled outcomes are not
generated.

### Run

After committed G0, run all three arms over all 871 unique questions at the
three unique budgets. Repeat the deterministic computation in a fresh process
and require identical ranking, selected-identity, payload, and outcome digests.
Generate per-question artifacts before the summary and verdict. Any cache miss,
budget overrun, identity drift, missing row, duplicate comparison key,
unregistered arm/budget, dirty worktree, or non-identical replay stops the run.

This offline full-population run is the registered ablation. A 35-turn live
ablation and live reader run are not appropriate here because TC-005 makes no
reader claim. The later TC-006 reader validation must operate on contexts
frozen only after TC-007.

## 10. Surrogate and leakage audit

Rank score, lexical overlap, rank correlation, candidate count, characters,
any-evidence delivery, and a full-budget win can all pass while complete
targeted half-budget evidence is worse. They are descriptive only. Conversely,
complete evidence availability can improve without improving reader answers;
that residual is accepted here and is why TC-006 remains required.

Mechanism code may read only conversation pairs, question text, vectors, and
registered constants. Evidence mappings are measurement-only and may be joined
only after all three orders and payloads for that question are frozen. No
`q_facts_key.md`, rubric, expected answer, or answer text may enter ranking,
packing, gating, or arm selection.

## 11. Required closeout

The report must name the selected TC-007 relevance order or dense fallback,
state every works/signal/guardrail margin, report all primary and secondary
counts without reader language, and preserve the numerical near-tie limit.
Closeout must commit G0/run artifacts and tests, update `README.md`, update the
root `AGENTS.md` digest within 400 characters, update memory files, update
`ERRATA.md` only if a published number changes, and open the TC-005 PR.
