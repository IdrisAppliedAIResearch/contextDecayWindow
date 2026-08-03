# EC-001 Amendment 003 — Incomplete turn-level evidence labels

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Adaptation-record anchor:** `a65c2566e55a2063bd1904065032f86c5d0e23a9`  
**Amendment 001 anchor:** `a1dc736cece4e1aa95412c661dec94da48feaf25`  
**Amendment 002 anchor:** `befa2c41659031496127d8b2a180e3c616801d02`  
**Status:** AUTHORIZED BEFORE SUBSET LOCK, RETRIEVAL, OR INFERENCE  
**Authorization:** Program author, August 3, 2026: “Go ahead. You are
authorized to make amendments.”

## Trigger and evidence

The full-500 pre-lock instrument audit found 45 raw session ids named by
`answer_session_ids` whose source sessions contain no turn marked
`has_answer`. They occur in 32 answerable questions: 20 temporal-reasoning,
10 multi-session, and 2 knowledge-update. Every affected question has at
least one marked evidence turn in another named evidence session.

This is label incompleteness, not missing or post-probe source material. All
45 named sessions exist in the haystack and are presented before the query in
file/prompt order.

The seed-5005, seven-by-20 selection was derived only from question id, type,
and abstention suffix. Before it was locked, the audit found two selected
multi-session questions with one unmarked named session each:

- `gpt4_194be4b3`, `answer_3826dc55_5`: distinguishes instruments belonging
  to the niece or only being considered for purchase from instruments the
  user currently owns.
- `1a8a66a6`, `answer_2bd23659_4`: distinguishes a purchased magazine issue
  from a current subscription.

The source sessions therefore contribute exclusion evidence to the count
questions even though no constituent turn carries `has_answer`.

## Change

- Keep the deterministic subset unchanged. Never replace, omit, or resample
  an affected question.
- Continue to compute the registered carried metric exactly as written: all
  source turns marked `has_answer` must be present verbatim in delivered
  episodes. Name it `marker_availability` in new artifacts; retain the legacy
  `availability_*` fields only as compatibility aliases.
- Add `turn_label_complete`, false when any named evidence session lacks a
  marked turn.
- Do not claim that marker availability certifies complete factual
  availability when `turn_label_complete` is false. Report the affected count
  and results separately.
- The exact Tier 1 minus Tier 2 fact-availability gap is `NOT_EVALUABLE` for
  affected questions. Exclude them only from that exact-gap denominator, not
  from retrieval, generation, benchmark accuracy, session recall, rank
  distributions, raw subset aggregates, or per-stratum results.
- Preserve and report the benchmark session-recall metric for all named
  evidence sessions. It is a session-identity measurement, not a substitute
  for exact fact presence.
- The subset pre-lock gate fails only when an answerable question has no named
  evidence session, no marked evidence turn at all, or a named evidence
  session absent from the source history. A partially missing turn annotation
  is recorded as an instrument limitation and does not assert that source
  evidence is absent.
- Commit the complete list of affected questions and sessions as a generated
  instrument-audit artifact before Tier 1. The artifact may contain reference
  metadata and is measurement-only; retrieval code must not read it.

## Rationale

Treating a named-but-unmarked evidence session as absent would be false: the
source material exists before the query. Treating the remaining marked turns
as a complete factual key would also be false: the two selected count
questions demonstrate relevant exclusion evidence outside those markers.

This amendment narrows a metric rather than making a bar easier. It preserves
all benchmark items and all registered outputs while preventing the recurring
surrogate failure in which a partial marker set passes as complete factual
availability.

## Alternatives rejected

- **Resample the two affected questions:** post-selection instrument filtering
  would contaminate the registered subset.
- **Promote whole-session recall to fact availability:** session identity can
  pass while the relevant exchange is absent from the returned block.
- **Add new per-turn labels by judgment:** that would create a local rubric
  rather than use the benchmark's protocol.
- **Drop all 32 questions:** changes the external benchmark population and
  hides an instrument limitation discovered by the registered audit.

## Exclusions

- No change to `episodic`, ranking, selection, rendering, or the reader.
- No use of answers, `answer_session_ids`, or `has_answer` by mechanism code.
- No change to benchmark end-to-end scoring.
- No inference from timestamps about whether evidence is valid.
