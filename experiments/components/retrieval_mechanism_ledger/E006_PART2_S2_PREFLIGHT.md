# E006 Part 2 S2 Preflight

**Date:** August 10, 2026
**Decision:** **FAIL - STOP BEFORE S3**
**Design anchor commit:** `7fa09c62`
**Design SHA-256:** `84A5EB5B29A01F4027B4E18411F8D0D99D41C7EEA3206E4ED329063D13B35DC1`
**S1 commit:** `1ef754a3`
**Auditor execution commit:** `1dabee2a`
**Machine artifact:** `artifacts/e006_part2_preflight/preflight.json`
**Machine artifact SHA-256:** `AE78582C4116800FCAABB9286AF1AF262C5F34B7F42ED2990FD3F11D51369FA9`
**Calls:** zero model calls; zero embedding calls

## 1. Decision

S2 fails. The registered X1 control is structurally unequal to X0, which is an
explicit S2 stop condition. The committed corpus also lacks the raw probe-query
vectors required to execute E-1, cue blending, reachability, or the PF7 real-trace
cycle sweep without making prohibited embedding calls.

S3 parameter registration did not begin. S4 offline arms did not run. S5 remains
separately gated and unauthorized.

## 2. Exploration

### E-1 - Current cue

The committed store contains 121 episodes spanning turns 1-121. Every episode has
one 4,096-byte float32 vector, or 1,024 dimensions. All 121 stored `text` values
are the full `User: ...\nAssistant: ...` episode pair, matching the runner's
storage path. They are not embeddings of the raw probe query and cannot serve as
`q0`.

The eight registered probe queries are present in `logs/turns.jsonl`. Exact-text
or SHA-256 lookup found **0/8** query vectors in each of the five committed
embedding caches. `logs/context_match.jsonl` supplies committed candidate
identities but no query vectors or complete cosine arrays. Candidate identities
are sufficient to reproduce X0; they are not sufficient to calculate a chained
cue.

Only Q11 has a committed full cosine rank trace. Its first four episodes each
carry 0/17 target facts, reproducing the registered DR-002 observation. The
required all-probe cosine and fact-bearing rank distributions cannot be produced
from committed artifacts.

### E-2 - Component identity

| Component | Falsifiable behavioral identity |
|---|---|
| Seeding path | The live K path embeds the raw current user message; the store embeds the full user/assistant episode pair. |
| K threshold | K scans every eligible episode in store order and returns every cosine at least 0.48; it is not `top_m`. |
| Packer | Candidates are considered N first, then K; each is charged exact compact-XML cost, and an overflow candidate is skipped while iteration continues. |
| Renderer | Two compact XML blocks serialize escaped turn, user, and assistant content: `recent_context` and `retrieved_stm`. |
| Proposed chain | Each inclusive `0..D` iteration retrieves `top_m` unseen episodes and blends their mean episode vector into the next cue. |

The deployed X0 and proposed chain therefore do not share one retrieval
operation: deployed X0 is thresholded K plus rotating N-first packing, while the
chain is `top_m` over an exclusion set.

### E-3 - Feedback inventory

The chain has two state variables. `seen` grows monotonically and never decays.
`c` becomes a normalized blend of its prior value and the mean embedding of the
current hits. At `BETA=0`, `c` remains `q0`; however, `exclude=seen` still changes
the next retrieved set. A real context-vector trace, cycle sweep, and near-fixed
point measurement cannot execute without the missing `q0` vectors.

### E-4 - One-step return distribution

Across all 121 committed turns, K candidate counts have this full distribution:

| K candidates | Turns |
|---:|---:|
| 0 | 74 |
| 1 | 17 |
| 2 | 7 |
| 3 | 8 |
| 4 | 4 |
| 5 | 6 |
| 6 | 5 |

At probe turns 112, 113, 115, 116, 117, 118, 119, and 120, K returned
respectively 5, 6, 1, 4, 3, 0, 0, and 3 candidates. Delivered K counts were 2,
4, 0, 3, 0, 0, 0, and 0. This confirms sparse, thresholded returns and packing
displacement rather than a fixed-count `top_m` path.

## 3. Controls

### X0 reproduction

X0 reproduces exactly through the authoritative renderer and packer loaded from
their committed source files:

| Check | Result |
|---|---:|
| Selected episode content-hash sequence | PASS |
| Selected episodes | 8 |
| Selected source turns | 119, 68, 73, 83, 89, 96, 103, 4 |
| Serialized characters | 31,946 |
| Payload SHA-256 | `64b19b96b44bb4745f4543a7824a18433e49131d1eeb9a9813760f15f8afe478` |

UUIDs are used only to dereference committed source rows. New comparisons use
SHA-256 over canonical episode content.

### X1 contradiction

With `BETA=0`, the context remains `q0`, so each step uses the same ranking. But
the inclusive `0..D` loop and `exclude=seen` retrieve the next `m` episodes every
step. The candidate set before packing is therefore `m * (D + 1)`, not `m`.

The committed Q11 rank trace mechanically demonstrates the mismatch:

| D | m | Steps | One-pass episodes | X1 packed episodes | Equals one-pass digest | Equals deployed X0 digest |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 3 | 2 | 3 | 6 | No | No |
| 2 | 3 | 3 | 3 | 9 | No | No |
| 3 | 3 | 4 | 3 | 11 | No | No |
| 1 | 5 | 2 | 5 | 10 | No | No |
| 2 | 5 | 3 | 5 | 11 | No | No |
| 3 | 5 | 4 | 5 | 11 | No | No |

The 11-episode ceiling in three cells is exact-cost packing, not chain equality.
One real-probe counterexample is sufficient to refute the all-probe digest
assertion. This is a contradiction in the registered control, not an observed
mechanism result.

## 4. Checklist

| Check | Status | Evidence |
|---|---|---|
| PF1 Inputs exist | **FAIL** | Store and identities exist, but 0/8 raw probe-query vectors exist in committed caches. Two named companion paths are also absent. |
| PF2 Mechanism identity | **FAIL** | Deployed X0 is thresholded K plus rotating N-first packing; the chain is `top_m`. |
| PF3 Gate ordering | PASS | `7fa09c62` is an ancestor of `1ef754a3`, which is an ancestor of execution commit `1dabee2a`. |
| PF4 Threshold achievability | **FAIL** | Capacity is established, but maximum seed reachability by depth cannot be computed without `q0`. |
| PF5 Stable keys | PASS | New comparisons use canonical content SHA-256 values. |
| PF6 Reproduction anchor | **FAIL** | X0 reproduces, but mandatory X1=X0 fails for all six registered `(D,m)` cells on Q11. |
| PF7 Absorbing-state proof | **FAIL** | The required real chained trace and context-vector sweep cannot run without `q0`. |
| PF8 Ablation adequacy | PASS | A 35-turn trace fully exercises depth-local behavior, but not live variance or cross-turn state. |
| PF9 Surrogate audit | PASS | Availability, no-cycle, and aggregate-targeted false positives remain explicit. |
| PF10 Live requirement | PASS | Offline delivery is not an answer verdict; S5 was not run or authorized. |

The spec names `NEUROSCIENCE_LANDSCAPE.md` and
`STANDING_RULE_preflight.md`, neither of which exists. The repository contains
near matches `LITERATURE_LANDSCAPE.md` and root `PREFLIGHT.md`; they were recorded
but not silently substituted.

## 5. Disposition

**STOP BEFORE S3.** Repair requires a new authorized design decision, not an
implementation workaround. At minimum, it would need to resolve the X0 versus
`top_m` identity, define X1 so disabling reinstatement is actually identical to
X0, and authorize a source for exact raw probe-query vectors or embedding calls.
No parameter cell is registered and no offline mechanism outcome is reported.
