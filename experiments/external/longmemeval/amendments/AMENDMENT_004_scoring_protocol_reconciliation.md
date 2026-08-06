# EC-001 Amendment 004 — Scoring protocol reconciliation

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Tier 2 subset anchor:** `cfcf4c010fc8c9b2534419ccde9b7ef402da8e2c`  
**Status:** AUTHORIZED BEFORE TIER 1, GENERATION, OR SCORING  
**Authorization:** Program author, August 3, 2026: “Go ahead. You are
authorized to make amendments.”

## Trigger

LongMemEval's pinned evaluator uses one `gpt-4o-2024-08-06` yes/no call with
no rationale. The program's standing scoring protocol instead requires a
calibration gate, three blind passes, an answer-grounded rationale for every
score, and H1–H5 adjudication. Two carried triggers refer to internal-study
artifacts that EC-001 does not have: H3 compares against an original score,
and H4 covers every Q11/Q14 item.

The protocols cannot both be followed literally without registering which
output is benchmark-comparable and how the standing integrity requirements
are layered around it.

## Change

### Reader surface

- Use the benchmark's non-chain-of-thought answer prompt, adapted only by
  placing the already-rendered `episodic` block in `History Chats`.
- Preserve the carried reader call shape: raw llama.cpp `/completion`, a
  prefilled closed reasoning block, `reasoning_format=none`, fixed seed 5005,
  one slot, and no speculative decoding.
- Only content outside reasoning blocks is scoreable. A reasoning-only,
  empty, or whitespace-only response is mechanically `NO_ANSWER` and scores
  zero without consulting a rater.

### Three-family scoring

- Lock three rater model families in a separate runtime record before
  generation. None may be Qwen, the reader family.
- Every family receives the benchmark's task-specific yes/no prompt with the
  question, reference answer/rubric, and masked scoreable response. The
  GPT-4o pass uses the benchmark's pinned evaluator snapshot and preserves the
  benchmark prompt bytes.
- Parse only an unambiguous `yes` or `no` decision. Reject missing, mixed, or
  unparseable labels.
- Obtain a second, label-conditioned call from the same family for an
  answer-grounded rationale. The rationale call cannot revise the first
  label. Missing rationales block scoring.
- Run the planted calibration set before any real answer reaches each family.
  It includes an answerable, substantive reasoning-only response that must be
  reduced to `NO_ANSWER` and score zero.
- Independently shuffle item order for each family from stable masked ids and
  a family-specific suffix.

### Outputs and precedence

- Report the pinned GPT-4o labels as the **benchmark-protocol score**. This is
  the only score compared directly with published LongMemEval numbers.
- Separately report the **three-family integrity score**. Unanimous labels are
  final unless selected by H5. Every disagreement is H2 and is adjudicated.
- An independent AI adjudicator is pinned in the runtime record. It receives
  masked question, reference, response, and locked scoring guidance, but not
  family identities or labels for H5. For H2 it receives the existence of a
  disagreement and the three rationales without model identities.
- Adjudicator labels take precedence for triggered items. Reports must call
  this AI adjudication, not human adjudication.

### H1–H5 applicability

- **H1:** any proposed positive score that conflicts with `NO_ANSWER`,
  completeness, truncation, or its own rationale. H1 blocks the score and
  triggers adjudication after the mechanical conflict is recorded.
- **H2:** any disagreement among the three family labels.
- **H3:** zero applicable items. EC-001 has no pre-existing original score.
- **H4:** zero applicable items. EC-001 has no Q11/Q14 identifiers. H4 is not
  waived or reassigned.
- **H5:** deterministic 10% sample of otherwise unanimous, non-H1 items using
  the standing seed `sia-h5-2026-07-26-v1`. H5 adjudication occurs before
  family labels are revealed.

### Aggregation

- Report all 140 item labels, every rationale, family disagreement, trigger,
  and adjudication basis.
- Report per-stratum accuracy, the raw seven-by-20 subset micro-average
  labelled non-benchmark-distributed, and the benchmark-population
  post-stratified aggregate.
- Report marker-availability minus correctness only where
  `exact_gap_evaluable` is true under Amendment 003.

## Rationale

The benchmark-protocol score remains reproducible and directly comparable,
while the second score satisfies the program's stronger integrity discipline.
Keeping them separate prevents a multi-family aggregation from being
misrepresented as the published benchmark's evaluator. Declaring H3/H4 empty
is faithful to their locked definitions; inventing substitutes after seeing
answers would change the adjudication surface.

## Alternatives rejected

- **One GPT-4o pass only:** repeats LV-001's known protocol failure.
- **Three GPT-4o passes:** measures one model's self-consistency rather than
  correctness under independent family biases.
- **Ask for a label and rationale in one modified prompt:** breaks byte-level
  comparability with the benchmark evaluator.
- **Majority vote without adjudication:** silently converts disagreement into
  a scoring rule not present in either protocol.
- **Treat H3/H4 as generic disagreement triggers:** changes locked trigger
  definitions after the external instrument is known.

## Exclusions

- No rater or reference field may reach retrieval or reader context assembly.
- No answer-based subset filtering.
- No change to LongMemEval's task-specific correctness language, including
  temporal off-by-one tolerance, knowledge-update handling, preference
  rubrics, or abstention wording.
