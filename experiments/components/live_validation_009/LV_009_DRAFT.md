# LV-009 — full-LoCoMO compact-community reader validation

**Type:** draft full-population live reader validation  
**Status:** DRAFT ONLY; NOT PRE-REGISTERED OR RUNNABLE  
**Date:** 2026-08-26  
**Authorization:** program owner requested LV-008's renderer comparison across
all LoCoMo questions

## 1. Question and exact meaning of “all LoCoMo questions”

Across the complete locked LoCoMo corpus, does the LV-008 `COMMUNITY_QB`
renderer improve answer correctness over pairwise parent-child rendering, and
how much of that effect comes from compact semantic-community organization
versus repeating the question before and after memory? Does repeating the same
question after every community add a further measurable improvement?

The population is all ten LoCoMo conversations and all 1,986 raw QA records:

- 1,540 standard benchmark-scored questions in categories 1–4;
- 446 category-5 adversarial questions, which the published LoCoMo evaluator
  excludes and LV-009 reports separately; and
- no development-conversation filter and no duplicate-question removal.

With four arms and one frozen reader sample per question, the complete run is
7,944 reader answers. All 6,160 category 1–4 arm-answers receive three blind
judge passes, producing 18,480 parseable judgments. All 1,784 category-5
arm-answers receive the frozen exact-refusal measurement. Thus every LoCoMo
question is answered in every arm and every generated answer receives a
registered outcome.

LV-009 can establish an internal full-LoCoMo score and whether the rendering
effect transfers beyond the four conversations used to develop it. It cannot
establish reader-model generality, an official Mem0-comparable score,
production latency, or deployment fitness. A positive result makes the
renderer eligible for a separately verified `episodic-chat` port; it does not
itself modify or deploy the library.

## 2. Frozen corpus, retrieval and claim boundary

- LoCoMo source: 2,805,274 bytes, SHA-256
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Development conversations: `conv-41`, `conv-42`, `conv-47`, `conv-48`.
- Transfer conversations: `conv-26`, `conv-30`, `conv-43`, `conv-44`,
  `conv-49`, `conv-50`.
- Raw population counts are fixed at 1,986 total, 1,540 categories 1–4 and
  446 category 5. Part 1 must reproduce these counts and their per-conversation
  and per-category distributions before registration.
- Context is the exact 32,000-character TC-014 `opportunity` pipeline carried
  by LV-008: CC80 semantic selection plus protected ASPECT fan-out with exact
  opportunity admission, containment deduplication, skip-on-overflow packing
  and unused spread capacity returned to CC80.
- TC-014's parameters, candidate unit, carried vectors, scores, parent-child
  edges, admission rule, 50/50 protected allocation and 32,000-character total
  budget are unchanged.
- Recency is absent because this is retrieval evaluation over completed LoCoMo
  conversations, matching the LV-008 prompt surface. LV-009 makes no claim
  about the deployed library's additive last-32 continuity tier.

The existing TC-014 artifact freezes the mechanism on the four development
conversations. Before registration, Part 1 must apply the same label-blind
mechanism to the remaining six conversations, verify all required vectors or
record embedding-cache misses separately, and seal all 1,986 selected identity
sets and payloads without opening answers, evidence labels or prior reader
outcomes. This is mechanism transfer, not parameter refitting.

The 17 LV-008 rows are reproduction anchors only. LV-007/LV-008 answers,
judgments and item outcomes are forbidden as LV-009 outcomes. Stable keys are
canonical corpus record, question and episode-content hashes; generated ids,
timestamps and paths may not act as comparison keys.

## 3. Frozen rendering arms

Every arm receives the exact same selected episode identities for its question
and preserves every compact `<episode>`, `<user>` and `<assistant>` element
byte-for-byte and exactly once. Only deterministic organization markup, order
and question placement differ.

### C0 `PAIRWISE`

The exact LV-008 pairwise parent-child behavior generalized mechanically to all
1,986 rows: semantic parents remain in CC80 order, each selected ASPECT child
is placed with its frozen parent, the group uses the frozen temporal-guidance
wrappers and wording, and the question appears at the bottom.

### T1 `COMMUNITY`

The exact LV-008 compact semantic-community behavior generalized mechanically
to all rows. Over the already selected identities, affinity is frozen as

`0.8 * cosine + 0.2 * facet_ochiai`.

Visit identities in frozen selection order. Assign to the open group below
eight items with greatest mean affinity when that mean is at least `.04`;
otherwise create a new group. Exact ties prefer the earlier-created group.
Groups remain in creation order and items within a group are sorted by numeric
conversation turn, then content hash. Render the exact compact `<g>` schema and
organization note from LV-008. The question appears at the bottom.

### T2 `COMMUNITY_QB`

T1's byte-identical memory block with the exact question additionally inserted
immediately after the reader template's first line. The same question remains
at the bottom. This is LV-008's combined candidate renderer.

### T3 `COMMUNITY_QEACH`

Use T2's exact top question, community groups, group order, episode order and
normal bottom question. After every non-final `</g>`, insert exactly:

```text
<question_reminder>Question to answer: {exact question}</question_reminder>
```

The normal bottom `Question: {exact question}` is the reminder following the
final group; no additional reminder is inserted beside it. For `G` community
groups, the exact question therefore appears `G + 1` times: once before memory
and once after each group. A one-group row is intentionally byte-identical to
T2. No paraphrase, query expansion, group-specific rewrite or accumulated
answer state is introduced.

The 51 prompts from LV-008 must reproduce byte-for-byte as a subset. No new
clusterer, coefficient, threshold, cap, wrapper, summary, entity label,
supersession rule, retrieval route or prompt instruction is permitted.

## 4. Reader schedule

- Ollama `0.33.0`, raw `/api/generate`, thinking disabled, streaming disabled,
  one request at a time, `keep_alive=30m`, and no speculative decoding.
- Model alias `lv008-qwen38-q4:latest`, manifest SHA-256
  `281d02f0ad1a4b4928fcf1450e6bd1bb88e0d57c0051df03a993265ec6662adc`.
- Source `Qwen3.8-27B-UD-Q4_K_XL.gguf`, SHA-256
  `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372`.
- `num_ctx=65536`; all 21,558,366,042 runtime bytes must remain resident on
  the NVIDIA GeForce RTX 5090 before and after every run phase.
- Reader settings: `num_predict=8192`, temperature `.6`, top-p `.95`, top-k
  `20`, min-p `0`, repeat penalty `1.0`.
- One reader sample per question-arm. Let `h` be SHA-256 of
  `lv009-reader-seed-v1 || NUL || comparison_key`; the seed is
  `5100 + (big_endian_uint64(h[0:8]) mod 16400)`. The same question seed is
  used for all four arms. Part 1 must verify this exact equation and its
  resulting distribution.
- Question-arm execution order is ascending SHA-256 of
  `comparison_key || arm` under domain `lv009-order-v1`.
- Append, flush and fsync every answer before starting the next request.

One sample per arm is deliberate. The 1,540 paired benchmark items estimate
population direction; five replicates would increase the schedule to 39,720
reader and 92,400 judge calls without adding new questions. LV-009 can detect a
population-level renderer difference but cannot estimate per-question reader
stability. LV-008's five-replicate result remains the separate instability
characterization on its selected 16-item primary sample.

The 8,192-token ceiling is provisional until Part 1 examines full-population
prompt and response risks. Before registration it may be raised if necessary
and context-safe; after registration it is immutable. A row is complete when
Ollama returns `done=true` and nonempty response bytes. A nonempty response
ending by length is retained and scored exactly as returned, with cap status
reported. Output length is part of reader behavior, not grounds to discard the
other 7,943 answers.

One retry is allowed only for a mechanical transport failure and both attempts
are preserved. The run stops before scoring for an empty/incomplete response,
unresolved transport failure, wrong model, loss of full GPU residency, context
overflow, or a missing/extra/duplicate schedule row. It does not stop merely
because a nonempty response reaches `num_predict`.

## 5. Blind scoring

All 7,944 answers and the generation summary are committed before blind
surfaces are created. The 6,160 category 1–4 answers receive content-derived
blind ids under domain `lv009-blind-v1`. The judge sees question, gold and
answer only—never arm, renderer, conversation split, prompt structure,
predecessor result or mapping.

Use the frozen HH-001 correctness rubric and closed-think/`VERDICT:` parse
repair with the same registered Qwen3.8 alias. Judge settings are three passes
with seeds `9100`, `9101`, `9102`, temperature `.2`, top-p `.9`, top-k `20`,
min-p `0`, repeat penalty `1.0`, and `num_predict=4096`.

A capped judgment counts only when the frozen parser obtains a verdict; cap
status is reported. An unparseable judgment is a validity failure and is not
silently retried or repaired after inspection. Exactly 18,480 parseable
judgments are required before the blind mapping opens. Majority of three gives
the answer verdict. Normalized gold containment is a secondary direction
check, not the correctness endpoint.

Category 5 is excluded from the primary endpoint because the published LoCoMo
metric excludes it. All 1,784 category-5 arm-answers receive the same frozen
exact-refusal measurement used by LV-008 and are reported separately.

## 6. Primary endpoints and registered strata

There are two co-primary paired comparisons over all 1,540 category 1–4
questions:

1. `FULL_vs_PAIRWISE`: `COMMUNITY_QB` versus `PAIRWISE`, testing whether the
   exact LV-008 candidate transfers to full LoCoMo.
2. `QUESTION_EACH_INCREMENT`: `COMMUNITY_QEACH` versus `COMMUNITY_QB`, testing
   whether refocusing after every community improves over top-and-bottom
   refocusing.

For each report correct counts and percentages, gains, losses, ties, net,
percentage-point difference and exact one-sided McNemar p in both directions.
Holm controls these two co-primary treatment-direction tests at familywise
`.01`; practical effect and regression guards still apply independently.

Binding transfer and guardrail strata are:

- four development conversations: 692 scored raw questions;
- six transfer conversations: 848 scored raw questions;
- categories 1, 2, 3 and 4: 282, 321, 96 and 841 questions; and
- each of the ten conversations separately.

Evidence-derived targeted/breadth/other labels are reported descriptively only
where mechanically resolvable. They do not define the primary population and
are forbidden from prompt construction.

Secondary comparisons are:

1. `COMMUNITY_vs_PAIRWISE`, testing compact communities plus wrapper changes.
2. `QUESTION_REPEAT_INCREMENT`, testing T2 versus T1 and isolating question
   placement.
3. `QUESTION_EACH_vs_PAIRWISE`, reporting the complete T3 renderer versus the
   pairwise control. This comparison is also a required safety check if T3
   clears its incremental test.

For every arm also report containment, response-token distribution, prompt
tokens, block characters, length stops, judge disagreement, wall time,
per-category totals, per-conversation totals and category-5 refusal results.

## 7. Dispositions

For either co-primary comparison, a treatment **works** only when combined net
is at least `+31` of 1,540 (at least two percentage points), its exact one-sided
McNemar p survives the two-test Holm family at `.01`, the six-conversation
transfer net is positive, no category has a negative raw net of ten or more,
and no category or conversation shows a significant control-direction
regression at Holm-adjusted familywise `.01`.

It **carries signal** when the works branch does not fire, combined net is at
least `+16` (at least one percentage point), treatment-direction `p <= .05`,
the transfer net is positive and no regression guardrail fires. Absolute net
below 16 without a guardrail is no material difference. A negative practical
effect or fired guardrail is regression. A validity failure or opposite
nonzero statistically significant semantic/containment direction is not
interpretable.

Apply the architecture disposition in order:

1. **`QEACH_SELECTED`:** `QUESTION_EACH_INCREMENT` works and T3 versus
   `PAIRWISE` independently meets the works practical, transfer and regression
   conditions with one-sided `p <= .01`. T3 is the library-port candidate.
2. **`QB_SELECTED_QEACH_SIGNAL`:** `FULL_vs_PAIRWISE` works; the incremental T3
   comparison carries signal but does not work. T2 remains the candidate and
   T3 remains research-only.
3. **`QB_SELECTED`:** `FULL_vs_PAIRWISE` works and the incremental T3 comparison
   has no material difference or regresses. T2 is the candidate.
4. **`RENDERER_CARRIES_SIGNAL`:** neither selection branch fires, but T2 versus
   C0 or T3 versus T2 carries signal without an overall T3 regression versus
   C0. No renderer is selected for a library port.
5. **`PAIRWISE_RETAINED`:** no treatment works or carries signal and no
   treatment regression is demonstrated.
6. **`RENDERER_REGRESSION_OR_MIXED`:** any remaining valid pattern.
7. **`NOT_INTERPRETABLE`:** any validity gate fails.

The practical bars prevent a large population from making a negligible change
look deployable. The transfer requirement prevents four development
conversations from carrying the result. Raw category tolerances prevent a
small stratum from killing a useful renderer on one stochastic flip, while the
adjusted regression test still catches demonstrated harm.

Secondary comparisons report the same counts and p-values but cannot override
the co-primary disposition or rescue an arm that fails its registered safety
comparison.

`QEACH_SELECTED` or either `QB_SELECTED` disposition authorizes a separately
registered library-port verification of the named renderer. It does not
authorize deployment, alter `episodic-chat`, claim reader generality, or select
a new retrieval method. No parameter tuning, best-conversation selection,
prompt revision, output rerun after a valid score, or post-result population
removal is permitted.

## 8. Part 1 exploration required before registration

This draft is not Part 1. Before it can become a locked pre-registration,
execute and commit a label-blind exploration that:

1. reproduces all 1,986 raw records, 1,540 category 1–4 records, 446 category-5
   records, ten conversations and their fixed distributions;
2. verifies that the six transfer conversations are selected before any
   answer, evidence identity, gold or prior reader result is read;
3. applies the frozen TC-014 opportunity mechanism to all 1,986 questions with
   unchanged 32k budget and parameters, reporting vector-cache hits, embedding
   calls and misses separately from LLM calls;
4. reproduces all 871 unique development TC-014 selections where keys overlap
   and all 51 LV-008 prompt strings byte-for-byte;
5. constructs all 7,944 prospective prompt strings twice and verifies
   byte-identical digests, identical selected identity sets across arms, exact
   episode-element preservation and all named renderer behaviors;
6. reports full distributions—not only means—for selected counts, semantic and
   spread counts, parent-child groups, community counts/sizes, join/new/cap
   decisions, block characters, prompt characters and evaluated prompt tokens;
7. demonstrates real singleton, multi-item, cap-bound and all-singleton
   community states, rows where community order differs from pairwise, and the
   exact T3 reminder count and placement for every group count;
8. selects the longest prompt and the highest-risk rows without labels, runs
   exploration-only seeds at the proposed 8,192 ceiling, and verifies context
   safety, nonempty output and full GPU residency;
9. exercises the prior LV-008 capped-reader prompt at 8,192 and the seven prior
   capped-judge surfaces at 4,096, recording stop reason, token count, response
   digest and judge parseability without importing correctness; and
10. mechanically demonstrates the accepted nonempty-length path and every true
    validity-stop path before parameters are locked.

Part 1 must also report the number and fraction of primary rows having at least
two communities. T3 must differ from T2 on at least half of the 1,540 primary
rows; otherwise `QUESTION_EACH_INCREMENT` lacks an adequate treatment
population and is removed from the draft before registration rather than run
as an inert arm.

If full-population prompts exceed context, 8,192 is inadequate, judge verdicts
remain unparseable, the carried mechanism cannot transfer without missing
vectors, or any renderer degenerates on a material population, revise or stop
this draft before registration. Do not repair those findings with an amendment
after the design is locked.

## 9. Preflight — binding after registration, before generation

- **PF1 inputs:** hash, identify and count registration, Part 1, full corpus,
  selection/prompt seals, vector cache, parser, renderer, model source and
  manifest, process and GPU.
- **PF2 mechanism identity:** verify every named route, allowance, group,
  variable, wrapper, order and question placement against committed real rows;
  reproduce the LV-008 prompt subset exactly and verify T3 inserts one reminder
  after each non-final group with the normal bottom question serving the final
  reminder.
- **PF3 gate ordering:** registration commit precedes implementation; complete
  label-blind selection and prompt seals precede answers; answers commit before
  blind surfaces; judgments commit before mapping. Planted early gold, evidence
  and mapping access must fail.
- **PF4 reachability:** demonstrate every disposition, practical threshold,
  Holm guardrail, sign guard, accepted length outcome and true validity stop on
  synthetic rows, with both positive and negative directions reachable; prove
  the T3 treatment population meets the registered half-population floor.
- **PF5 stable keys:** content hashes only; reject duplicate schedule keys while
  retaining distinct raw QA records through content hash plus frozen occurrence
  ordinal.
- **PF6 reproduction:** reproduce all overlapping TC-014 selections, all 51
  LV-008 prompts and LV-008's sealed analysis digest without importing old
  answers or verdicts into LV-009.
- **PF7 absorbing state/runtime:** prove renderer degenerate states on real
  traces, seed-to-order determinism, accepted output-length behavior, transport
  retry ledger and full GPU residency. No cross-question feedback is allowed.
- **PF8 adequacy:** all 1,540 standard questions can detect a population-level
  difference and the six-conversation split tests transfer. One reader sample
  per arm cannot estimate item-level stochastic stability or reader generality.
- **PF9 surrogate audit:** a tiny difference can become statistically
  significant at this sample size; a collapsing control can create a net win;
  compactness can improve without correctness; repeated questions can change
  verbosity; capped answers may omit conclusions; same-model judges can share
  bias. Practical bars, transfer and regression guards, blind scoring and
  containment checks mitigate but do not eliminate these residuals.
- **PF10 live requirement:** only the complete reader and blind-judge schedule
  yields a verdict. Retrieval availability, prompt identity, compactness and
  containment are not answer correctness.

Additional gates:

- **G-POPULATION:** exactly 1,986 question records, 7,944 prompts, 1,540
  primary questions and 446 category-5 questions.
- **G-CONTENT:** all four arms contain identical selected identity sets with
  each episode element byte-identical and emitted once.
- **G-QEACH:** T3 differs from T2 exactly on rows with at least two communities,
  has one top question, one reminder after each non-final group and the normal
  bottom question after the final group, and is active on at least 770 primary
  rows.
- **G-GENERATION:** exactly 7,944 nonempty answer rows, one per question-arm,
  with zero missing, extra or duplicate schedule keys.
- **G-SCORING:** exactly 18,480 parseable primary judgments, three per blind
  answer, plus 1,784 exact-refusal outcomes.
- **G-CONTEXT:** every reader and judge prompt evaluates below 65,536 tokens.
- **G-GPU:** the exact registered alias stays fully GPU-resident through every
  live phase.
- **G-SEPARATION:** prior answers, gold, evidence labels, mappings and outcomes
  cannot enter retrieval, rendering, scheduling or blind judging.

No new semantic coefficient, parser rule, clustering rule, retrieval route,
budget, summary, answer-derived selector or generated label is permitted after
registration. Embedding calls are counted separately and are not LLM calls in
this program's terminology.

