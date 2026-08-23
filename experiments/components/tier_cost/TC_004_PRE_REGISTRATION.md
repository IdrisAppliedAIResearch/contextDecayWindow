# TC-004 Pre-Registration — predict which candidate should be split

**Status:** `PRE-REGISTERED — TREATMENT VECTORS DO NOT EXIST — STUDY NOT RUN`
**Integrity anchor:** the commit that first contains this file; the report records
that commit SHA and this file's LF-normalized SHA-256 without editing this file
**Standing:** `REGISTERED-OFFLINE` characterization at most; LoCoMo development
has been observed by prior studies
**Corpus:** LoCoMo development conversations `conv-41`, `conv-42`, `conv-47`,
`conv-48`
**Primary budget:** 16,000 exact serialized characters
**Secondary budget:** 32,000 exact serialized characters
**Seed:** not applicable; every operation is deterministic
**Planned embedding calls after lock:** 2,661 exact solo calls: one sentinel and
2,660 unique child texts
**Planned LLM/generation calls:** 0
**Date:** August 22, 2026

---

## 0. The author's definition of “model-free”

The roadmap asks for a “computable, model-free predictor.” The author resolved
the only ambiguity before registration:

> *“Model-free refers to no LLM calls, we don't count the embedding model as a
> model in this context.”*

This registration therefore uses a frozen embedding-derived statistic. It makes
no LLM or generative call. The Qwen embedder is still pinned, counted, cached,
and reported; the clarification changes the arc's terminology, not the runtime
integrity requirements.

## 1. Claim

For an adjacent-turn LoCoMo parent candidate and a query, the increase from the
parent's query cosine to its best child's query cosine predicts whether replacing
that parent alone by its independently ranked source turns improves complete
evidence availability. It will identify beneficial splits at a rate better than
ranking parents by source-text length alone.

The proposed score is:

```text
embedding_localization_gain(parent, query)
    = max(cosine(child_i, query)) - cosine(parent, query)
```

The baseline is descending parent source-text character length. Beating length,
not beating chance, is the registered comparison.

This is an operational predictor study. It does not claim that every candidate
should be split, that source turns are the optimum chunk, that raw length causes
dilution, or that delivered evidence becomes a correct answer.

## 2. Pre-lock basis and unopened result

The committed Part 1 proof of mechanism uses the 465-item LongMemEval NF-005
population. No splitting reproduces 351/465 any and 201/465 complete evidence;
splitting every parent reproduces 461/465 any and 454/465 complete evidence.
There are 213 beneficial one-parent cases across 110 questions and 19 harmful
ones.

On that development population, mean within-question average precision is .053
for length, .233 for lexical localization, and .542 for embedding localization.
Embedding localization is better/worse than length on 101/9 questions. These
numbers motivated transfer; they are not TC-004 outcomes and cannot set its
disposition.

The TC-004 transfer result remains mechanically unopened. LoCoMo development
contains 2,660 unique exact child texts. Only 68 singleton texts occur in the
retained parent/query cache; **2,592 required child vectors are absent**. No
embedding-localization score, actual child ranking, beneficial-split label,
average precision, or direction can be computed until the post-lock vector
capture in G5.

## 3. Population and stable identities

The source is the exact LoCoMo file at SHA-256
`79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`,
2,805,274 bytes. Conversation membership is the four development IDs above,
selected before adapting questions or evidence.

The source contains 882 question records. Eleven repeated QA records have
`duplicate_ordinal > 0` and remain excluded exactly as in TC-001 through
TC-003. The primary complete-evidence population additionally excludes three
unique questions with unresolved evidence IDs, leaving **868** questions. The
secondary any-evidence population includes all **871** unique questions with at
least one resolved evidence ID and evaluates only those resolved IDs.

Question identity is the carried SHA-256 over conversation ID, canonical QA
content, and duplicate ordinal. Parent identity is the carried LoCoMo pair
identity over conversation, session, dialogue IDs, and complete parent text.
Child identity is SHA-256 over the literal namespace `tc004-child`, conversation
ID, session ID, source dialogue ID, and complete speaker-labelled child text.
Generated database IDs, timestamps, paths, and row positions are never
comparison keys.

The four conversations contain 1,365 adjacent-pair parents. Exactly 1,297 have
two source turns and are predictor trials. Sixty-eight contain one terminal
source turn; they cannot express a split and remain unsplit under every policy.

## 4. Candidate construction, rendering, ranking, and packing

### 4.1 Parents

Parents are the committed `PairCandidate` values from
`analysis.locomo_nf_development`. Their text is exactly:

```text
{speaker_1}: {turn_1_text}
{speaker_2}: {turn_2_text}
```

or one line for a singleton. They are adapted to the exact TC-001 episode
record and rendered by `episodic._render.render_episode_element`.

### 4.2 Children

A two-turn parent's children are its exact individual speaker-labelled lines.
The two child texts joined by one LF must reproduce the parent byte-for-byte.
A split **replaces** the parent; parent and children never coexist.

Each child uses the committed episode renderer with:

- `user_message` equal to the complete speaker-labelled child text;
- `assistant_message` equal to the empty string;
- `turn_number` equal to `{one-based parent position}.{zero-based child offset}`;
- `ground_truth_domain` equal to the source session ID.

This representation is locked because renderer overhead is part of the cost.
No alternate child wrapper, truncation, overlap, sentence split, or hidden
separator is permitted.

### 4.3 Scores and ties

An unsplit parent uses its retained exact-solo Qwen query cosine. A split child
uses its own post-lock exact-solo Qwen query cosine. All surviving units compete
in one descending-cosine order. Exact score ties break by source session order,
parent pair order, then child offset; an unsplit parent has offset `-1`.

The proposed predictor orders the 1,297 splittable parents by descending
`embedding_localization_gain`, with source session and pair order as ties. The
length baseline orders them by descending `len(parent.text)` with the same ties.

A descriptive lexical ablation uses maximum child/query lowercase token-count
cosine minus parent/query lowercase token-count cosine. It has no bar and cannot
change disposition.

### 4.4 Exact budget

Mixed candidates are handed to `episodic._packing.pack_stm_payload` as the
retrieved tier with an empty recent tier. Budget is measured by `len(payload)`
over the exact serialized UTF-8 Python string. The primary is 16,000 characters;
32,000 is descriptive secondary. Skip-on-overflow continues scanning after a
candidate does not fit. No candidate is truncated.

At zero splits this mechanism must reproduce TC-001 `A_FLAT` byte-for-byte and
by selected identities. PF4 does so on all 868 primary questions at both
budgets, including 749/868 complete evidence at 16,000 and 810/868 at 32,000.

## 5. Vectors and the post-lock capture

Parent and query vectors come from the committed 2,236-entry development cache:

- file SHA-256
  `2ba617018a1b043bf439bb50e756191d8141fb7ca01a2e4a68c9eb822eba26f8`;
- content SHA-256
  `e103b2933ee9ec7b8e9236f43037797618da524e413b83a9f3973a19d28b1b2a`.

Child vectors use Qwen3-Embedding-0.6B Q8_0 at SHA-256
`06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`,
`llama-cpp-python` 0.3.25, 1,024-dimensional float32 output, `n_ctx=512`,
`n_gpu_layers=0`, `n_threads=1`, `n_threads_batch=1`, and one text per call.

Before any child vector is accepted, one solo call on
`episodic call-shape sentinel: one text per call` must reproduce vector SHA-256
`baecf77627380f36f75a69c4454b064d886133f04255c5e5b4d3f24f00e7c4b8`.
Then all 2,660 unique child texts are captured once into a new empty cache,
sorted by SHA-256 of complete text. The cache is sealed by file, canonical
text-to-vector, model, dimension, dtype, and call-shape hashes, committed, and
reopened read-only. Expected calls are 2,661 including the sentinel. A partial
cache, reuse of the 68 parent-cache hits, batching, retry into a partial cache,
or any different cardinality stops the study.

## 6. Primary endpoint and statistic

For each primary question:

1. Run the zero-split `A_FLAT` parent store.
2. For each of its splittable parents independently, replace only that parent
   by its two children, rank all surviving units by own cosine, and pack.
3. Label that parent `beneficial` only when complete evidence changes from false
   at zero split to true under that one-parent split.
4. Label it `harmful` only when complete evidence changes from true to false.
   Every other parent is neutral.

No evidence field enters construction, predictor scoring, ranking, or packing.
The labels are joined to frozen selections afterward.

For every question with at least one beneficial parent, compute standard
average precision within that question under the proposed predictor order and
under the length order. Questions with no beneficial parent do not have a
defined AP and are excluded from the paired predictor statistic, while their
operational availability remains reported.

Primary paired statistics:

- AP gains: questions where embedding localization AP exceeds length AP;
- AP losses: questions where length AP exceeds embedding localization AP;
- ties;
- mean and distribution of both APs and their paired difference;
- one-sided exact binomial sign-test *p* for gains over losses, excluding ties.

The positive-label population must contain at least six questions. Fewer than
six is `INSTRUMENT_INADEQUATE`: the corpus could not evaluate the registered
predictor bar, so the mechanism receives no failure disposition.

## 7. Dispositions, fixed before child vectors exist

There is one registered comparison, so no multiplicity divisor is required.
The minimum improvement is the paired win rate against length—not a comparison
with chance.

| Disposition | Primary condition |
|---|---|
| **`OPERATIONAL_TEST_WORKS`** | at least 6 AP-evaluable questions; gains >= 2 × losses; one-sided exact *p* <= .05; and mean embedding-localization AP > mean length AP |
| **`CARRIES_SIGNAL`** | not `OPERATIONAL_TEST_WORKS`; gains > losses; one-sided exact *p* <= .20; and mean embedding-localization AP > mean length AP |
| **`NO_PREDICTIVE_SIGNAL`** | AP population is adequate and neither condition above holds |
| **`INSTRUMENT_INADEQUATE`** | fewer than 6 questions contain a beneficial parent, or the positive and adverse controls do not exist at G0 |

`gains >= 2 × losses` is the registered minimum improvement over length for the
upper tier. The lower tier exists independently and prospectively under
`AGENTS.md` §9.3. Neither may be added, relaxed, or reinterpreted after G7.

PF4 demonstrates reachability on the exact renderer and corpus without actual
child vectors. At 16,000, 99 questions can express an oracle beneficial
one-parent split and 749 can express an adverse one. Six gains and zero losses
reach the upper tier (*p*=.015625); four and one reach only the lower tier
(*p*=.1875); one and one reach no-signal (*p*=.75). The corresponding positive
and adverse populations also exist at 32,000.

## 8. Registered descriptive analyses — no bars

None of the following can change §7:

- any resolved evidence at 16,000 over 871 unique questions;
- complete and any evidence at 32,000;
- harmful and neutral parent counts;
- AP by conversation, category, parent-length quartile, child-length ratio,
  parent cosine, and number of evidence IDs;
- lexical-localization AP;
- proposed and length policies applied to every candidate at matched split
  rates `0, .01, .02, .05, .10, .20, .30, .50, .75, 1.0`, with
  `ceil(rate × splittable parents)` except exact zero and full endpoints;
- all-split versus no-split availability, packed characters, renderer overhead,
  delivered unit count, and exact policy convergence at zero and full split;
- selected-identity and payload digests for every mixed policy cell.

The matched-rate curves are the required operational surrogate check. A
predictor may pass AP while false-positive distractor splits make the complete
store worse. Such disagreement is reported as a limitation, not used to change
the predictor disposition or choose a favorable rate.

## 9. Standing arms

Roadmap §1.1's three standing arms travel unchanged:

- `A_FLAT`;
- `A_DUAL`;
- `A_DUAL_RANKED`.

`src/analysis/tc_standing_arms.py` remains their registry. `A_FLAT` is also the
zero-split reproduction anchor. `A_DUAL` and `A_DUAL_RANKED` are reported
descriptively at both budgets. No standing-arm contrast is registered because
TC-004 asks which parent should split, not whether tiers beat flat; adding a
contrast after the result is forbidden.

## 10. Gate order

Gates execute in this order and stop on first failure:

1. **G0 registration identity.** Pin this file's first-commit SHA and
   LF-normalized SHA-256. A mismatch stops before creating or opening a child
   vector cache.
2. **G1 inputs and population.** Assert every hash and count in §§2–5: four
   conversations, 882 records, 871 unique resolved-evidence questions, 868
   complete-evaluable questions, 1,365 parents, 1,297 splittable parents, 68
   singletons, 2,660 unique child texts, and 2,592 absent child vectors.
3. **G2 leakage.** Grep and import-graph checks prove candidate construction,
   predictors, ranking, packing, and vector capture cannot read evidence IDs,
   answers, categories, or outcome rows. A planted forbidden import and planted
   evidence-field access both fail.
4. **G3 reproduction.** Before treatment-vector access, reproduce zero-split
   `A_FLAT` byte-for-byte and by selected identities on every question at both
   budgets; reproduce 749/868 and 810/868 complete evidence only in measurement;
   reproduce the committed standing-arm digests.
5. **G4 implementation tests.** Prove exact parent/child reconstruction, stable
   identities, singleton exclusion, replacement rather than duplication,
   float32 matrix-vector call shape, source-order ties, exact renderer charging,
   skip-on-overflow continuation, own-score ranking, stable predictor order,
   and evidence-blind selection.
6. **G5 vector capture and seal.** Reproduce the sentinel, capture exactly 2,660
   child texts by solo calls into a new empty cache, seal it, commit its manifest,
   reopen read-only with zero misses, and record exactly 2,661 calls including
   the sentinel and zero LLM/generation calls.
7. **G6 evidence-blind determinism.** Run two complete selection replays from
   the sealed caches without evidence joins. Require byte-identical ordered
   identities and payload digests for zero split, every one-parent split, the
   matched-rate policies, and standing arms. Commit G0–G6 before G7 opens labels.
8. **G7 sealed outcome.** Join frozen delivered dialogue IDs to evidence IDs,
   compute the primary AP rows and disposition inputs, and commit one outcome
   artifact before opening subgroup or discordant diagnostics.
9. **G8 integrity and report tables.** Recompute every aggregate from rows,
   require a byte-identical outcome replay, verify zero measurement calls, apply
   §7 exactly once, then open registered descriptive analyses.

The G0 artifact commit must be an ancestor of the G7 outcome commit. The G7
runner reads and records that ancestry before joining evidence.

## 11. Preflight Part 1

**Behavioral identity.** A split replaces one parent pair and aggregate cosine
with its exact independently ranked source turns; split children and unsplit
parents then compete in one exact serialized pack.

**Name-to-behavior checks.** The LongMemEval proof reproduces both committed
granularity endpoints. The intended LoCoMo adapter reconstructs every parent
from its children, records the 68 singleton no-ops, and verifies the proposed
score's ingredients exist only after child capture. The author's definition of
model-free is recorded in §0 rather than inferred.

**Distribution.** The Part 1 artifacts contain full candidate, score, AP,
matched-rate, tie, length, and degenerate-state distributions. LoCoMo parents
have median 237 source characters and children 114; the pre-capture lexical
ablation spans 285,185 question/parent cases. LongMemEval's operational curves
show why a selective predictor is not an all-split claim.

**Degenerate states.** There is no feedback. Singleton parents cannot split.
At zero and full splitting every policy converges, so neither endpoint can test
the predictor. A score can be constant or tied and falls through the registered
source-order key. Full-store policy behavior remains separate from candidate AP.

## 12. Preflight Part 2

**PF1 — Inputs exist.** Verified at commits `0fcc6f12`, `3ab7e2cb`, and
`c3a29aeb`. Part 1 artifact SHA-256 is
`5833cdb331412961bd9a73c767363fc83c12b6a0cf1eb6ca22e42be8cc66df6a`;
LoCoMo split inventory is
`3b771ac61a548e4e93f3e5cdbc0b479f83e007bcae031fcab4b2380e0632a74b`;
PF4 is
`512e75d4dd6c7c1067f6e9ae43c3e00fd0a2e9855ac8c6f176e856d4cdb21623`.
The source corpus, retained cache, and development manifest are readable and
hash-identified. The post-lock child cache is a G5 deliverable; early existence
stops G0.

**PF2 — Mechanism identity.** Executed on committed LongMemEval and LoCoMo
data. PF4 found and corrected a real mismatch: row-wise float32 dot products can
reorder near ties relative to TC-001's matrix-vector call. The final preflight
uses the carried dtype and call shape and reproduces `A_FLAT` on 1,736
question/budget cells.

**PF3 — Gate ordering.** G0–G6 are one committed precondition. G7 asserts that
commit as an ancestor before evidence access. Planted registration, cache,
leakage, replay, and ancestry failures make G7 unreachable.

**PF4 — Thresholds achievable.** The committed PF4 artifact supplies the exact
populations and the upper, lower, and no-signal examples in §7. Both helpful and
harmful branches exist at both budgets. Actual predictor direction is absent.

**PF5 — Comparison keys stable.** Question, parent, and child identities are
content-and-source hashes. Delivered equality uses stable IDs and payload
digests. Paths, generated IDs, timestamps, and database order are excluded.

**PF6 — Reproduction anchor.** Zero split reproduces committed `A_FLAT`
byte-for-byte and by identities on every intended question and budget. The
LongMemEval proof reproduces 351/465 no-split and 461/465 all-split any-evidence
anchors before the LoCoMo transfer is specified.

**PF7 — Absorbing state.** No mechanism output changes a later input. The only
degeneracies are singleton no-ops, zero/full policy convergence, exact ties, and
budget ceilings, all measured on full real traces.

**PF8 — Ablation length.** This is a full-population deterministic offline
replay, not a live 120-turn run, so no 35-turn ablation applies. It can detect
predictive rank and availability on this store at two budgets. It cannot detect
reader use, learned store evolution, or transfer to a new corpus/embedder.

**PF9 — Surrogate audit.** AP can pass while full-store splitting loses; the
matched-rate curves expose that residual. Availability can pass while the
reader fails. Oracle PF4 shows instrument capacity, not predictor quality.
Splitting changes rank localization, unit cost, and wrapper count together.
Length is beaten as a predictor but not isolated as a cause.

**PF10 — Live evaluation.** Availability is not a verdict. No result authorizes
shipping, production chunking, reader-quality claims, or a best chunk size. A
live adoption claim requires a separate prospective reader registration;
TC-006 owns that question.

## 13. Leakage and result order

Mechanism code receives stable identity, source order, parent/child text,
vectors, predictor score, and budget only. It must not receive or read evidence
IDs, answers, categories, resolved/unresolved status, question outcome, or
benefit labels. The adapter may retain source dialogue IDs solely as opaque
post-selection join keys; the mechanism cannot inspect their membership in an
evidence set.

G7 is the first stage allowed to label a split beneficial, harmful, or neutral.
It commits per-question AP values, gains, losses, ties, mean APs, exact *p*, and
the mechanical disposition inputs before subgroup or discordant inspection.
Git order is the evidence.

## 14. What a result here does not establish

- **No answer-quality claim.** This study measures delivery only.
- **No shipping decision.** TC-002 and `PAPER_002.md` §9.3 already show that a
  confirmed availability gain can fail live; TC-006 owns adoption.
- **No optimum split rate or chunk size.** The matched rates are descriptive
  and source-turn boundaries are corpus-supplied.
- **No raw-length causality.** Splitting changes localization and renderer
  granularity together.
- **No universal predictor.** One observed corpus and one pinned embedder cap
  the finding at characterization.
- **No claim that all candidates should split.** Harmful cases and full-store
  false positives remain first-class outputs.
- **No confirmation.** LoCoMo development is exhausted.

## 15. Artifacts and commit order

1. Preflight Part 1 and PF4 — committed before this file.
2. **This registration alone.**
3. Study mechanism, vector-capture runner, outcome runner, and tests.
4. G0–G6 artifact and sealed child-vector cache/manifest.
5. G7 outcome artifact.
6. G8 integrity artifact and report.
7. Rule 4 dependency re-read, `README.md`, `AGENTS.md`, and memory.
8. TC-004 pull request.

Planned paths:

```text
src/analysis/tc004_exploration.py
src/analysis/tc004_preflight.py
src/analysis/tc004_study.py
scripts/run_tc004_preflight.py
scripts/run_tc004_reachability.py
scripts/run_tc004_study.py
tests/test_tc004_granularity.py
tests/test_tc004_preflight.py
tests/test_tc004_study.py
experiments/components/tier_cost/artifacts/tc004/
experiments/components/tier_cost/runs/tc004/g0/
experiments/components/tier_cost/runs/tc004/run/
experiments/components/tier_cost/TC_004_REPORT.md
```

## 16. Authorization

The author directed:

> *“We can begin implementing TC 004.”*

and then fixed the ambiguous mechanism term:

> *“Model-free refers to no LLM calls, we don't count the embedding model as a
> model in this context.”*

Those instructions authorize TC-004 as scoped here. They do not authorize a
reader run, production adoption, alternate chunk size, parameter sweep, or any
post-result repair.
