# TC-009 Preflight — dynamic session exposure penalty

**Status:** `PREFLIGHT PART 1 AND PF1-PF10 PASS — REGISTRATION MAY PROCEED`
**Date:** August 23, 2026
**Artifacts:** `artifacts/tc009/preflight/`

## Behavioral identity

Each source session competes through its highest-cosine remaining candidate.
After one candidate wins, every remaining candidate in that session receives an
additional `0.03` penalty and all sessions compete again. The winning session
is not excluded and can win consecutive slots. The adjusted score is:

`raw dense cosine - 0.03 * candidates already selected from that session`

Ties use source session/pair order and content identity. The selector emits a
complete permutation; TC-007's unchanged 50/50 allocator consumes it.

## What the real traces did

- All 5,226 committed TC-008 dense/A3/session question-budget selections and
  payload digests reproduced exactly.
- `lambda=0` reduces exactly to dense order on all 871 questions.
- A repeat session wins before all sessions are represented on 871/871 real
  questions. This is not a hard one-per-session floor.
- The complete dynamic order contains consecutive same-session wins on 606/871
  questions; the median is one consecutive transition and the maximum is five.
- At 16k the selected context represents a median 29 sessions and takes a
  median maximum of four candidates from one session. At 32k those values are
  30 sessions and six candidates. Sessions continue contributing repeatedly.
- The maximum prior-session count among admitted spread candidates has median
  two at 16k and four at 32k. The corresponding median maximum penalties are
  `0.06` and `0.12`. Outliers reach `0.45` and `0.54`, so a minor per-pick
  penalty can accumulate substantially and is reported rather than renamed.
- The treatment differs from dense and TC-008 session novelty on 871/871
  questions at both budgets. Both protected halves bind on every question.
- At 16k, dynamic-only candidates have median dense rank 71 while displaced
  dense-only candidates have median rank 44. At 32k those medians are 133 and
  90. The treatment therefore creates a real semantic-displacement risk before
  evidence outcomes are opened.
- No payload exceeds 16k or 32k. Median payload sizes are 15,975 and 31,974
  characters.

The 296,166-row full-order trace records every within-query state transition.
The 69,961-row admission trace records the dynamic candidates the protected
spread phase actually admits at each budget. Neither contains treatment
evidence or outcomes.

## Controls and degeneracies

- A constructed trace reproduces the agreed example: a session's `.86`
  candidate remains ahead of another session's `.82` after one `.03` penalty.
- A second trace shows accumulated exposure eventually lets another session
  overtake.
- With one source session, every remaining candidate receives the same penalty
  and dense order is unchanged.
- With `lambda=0`, all real orders are byte-identical to dense.
- Every real trace terminates after a complete candidate permutation. There is
  no cross-query state; within-query counts are monotone and bounded by store
  size.

## Frozen bands and PF4

The dense route, population, budgets and packer are unchanged from TC-008, so
its hash-verified dense-only one-percent shams reproduce the practical bands:

| Budget | Breadth share questions | Breadth identities | Breadth complete | Combined complete | Targeted complete |
|---:|---:|---:|---:|---:|---:|
| 16,000 | 0 | 0 | 0 | 2 | 2 |
| 32,000 | 0 | 0 | 0 | 1 | 0 |

There are six directional inferential cells. Works alpha is `0.01/6`; signal
alpha is `0.10/6`. Ten all-favourable breadth discordances clear works and six
clear signal. PF4 demonstrates dynamic-works, dense-works, both signal
directions, guardrail failure and neutral branches are reachable.

## PF1-PF10

- **PF1:** Corpus SHA-256 is
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`;
  cache SHA-256 is
  `2ba617018a1b043bf439bb50e756191d8141fb7ca01a2e4a68c9eb822eba26f8`.
  The artifact hash-identifies TC-008 selections, allocator and selector.
- **PF2:** All 296,166 state transitions expose raw cosine, prior count,
  accumulated penalty, adjusted score, selected candidate and source session.
- **PF3:** The registered worker must freeze selections before importing or
  joining evidence. A clean committed G0 gates the run.
- **PF4:** `tc009_preflight_pf4_reachability.json` makes every benefit, harm,
  guardrail, noninferiority and neutral branch achievable.
- **PF5:** Candidates use content identities. Questions use the committed
  label-blind key during selection and content SHA plus duplicate ordinal after
  measurement; paths and timestamps are not comparison keys.
- **PF6:** All 5,226 TC-008 predecessor payloads reproduce by ordered identity
  and byte digest.
- **PF7:** The within-query feedback state is fully traced. Counts increase by
  one only for the selected session, never decrease, and all 871 selectors end
  at full permutations.
- **PF8:** The full 871-question replay detects availability changes, not reader
  use, optimal lambda or enterprise transfer.
- **PF9:** More represented sessions and lower concentration can pass while
  required evidence falls. TC-008 demonstrated that residual directly; only
  evidence endpoints plus guardrails decide TC-009.
- **PF10:** No answer generation or adoption is authorized. Reader validation
  remains separately registered work.

The evidence-blind source audit passed and detected its planted
`evidence_key/q_facts_key` import. Preflight used 2,236 cache hits, zero misses,
zero embedding calls and zero LLM/generative calls. The `0.03` penalty was
fixed before this exploration and was not tuned.
