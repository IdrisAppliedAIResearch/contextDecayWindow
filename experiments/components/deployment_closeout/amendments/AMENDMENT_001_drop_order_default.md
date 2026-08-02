# AMENDMENT 001 — The drop order keeps skip-on-overflow, not strict rank-prefix

**Component:** `deployment_closeout` · Part 1 (CC-003)
**Pre-registration:** `CC_003_004_005_deployment_closeout.md` at `43588944`
**Section amended:** 1.2, requirement 2 (drop order)
**Type:** deviation from a stated default, with measurement
**Status:** COMMITTED before the CC-003 report

## Trigger

Requirement 1.2.2 has two parts. The binding one is that the drop order be
**specified and deterministic** — "a documented policy, not an artifact of
iteration order". The second is a suggested default:

> **Default: the selector's own marginal-gain order, dropping lowest gain
> first** — it is the objective's own ranking and requires no new heuristic.

The carried code does something adjacent but not identical. At each greedy
step `select()` filters the candidate set to those that still fit and takes
the highest-gain candidate among them. A candidate too expensive to fit is
passed over and the walk continues, rather than terminating the selection.
Call these **skip-on-overflow** (carried) and **strict rank-prefix** (the
literal reading of the registered default).

Implementing the registered default would have changed carried behaviour,
so the deviation is recorded here rather than resolved silently.

## Evidence

Both policies run against the committed Study 010 arm L store, first 400
episodes, A3 primary configuration `A3_l0.1_r0.0_k16`:

| Budget | Skip-on-overflow | Strict rank-prefix | Same selection? |
|---:|---|---|---|
| 1,000 | 2 episodes, 822 chars | 1 episode, 539 chars | no |
| 2,000 | 4 episodes, 1,798 chars | 3 episodes, 1,515 chars | no |
| 4,000 | 8 episodes, 3,955 chars | 8 episodes, 3,955 chars | yes |
| 8,000 | 17 episodes, 7,977 chars | 16 episodes, 7,694 chars | no |
| 16,000 | 37 episodes, 15,974 chars | 36 episodes, 15,723 chars | no |
| 24,000 | 53 episodes, 23,897 chars | 53 episodes, 23,897 chars | yes |
| **32,000** | **72 episodes, 31,849 chars** | **72 episodes, 31,849 chars** | **yes** |
| 48,000 | 104 episodes, 47,896 chars | 103 episodes, 47,579 chars | no |
| 64,000 | 140 episodes, 64,000 chars | 139 episodes, 63,720 chars | no |

Three findings:

1. The policies **agree at the 32,000 operating point**, so E6 — the replay
   gate pinning 12/17 · 4/4 · 16/16 at 31,569 characters — does not
   distinguish them. Neither choice can be justified by the shipped result.
2. They **diverge at 6 of the 9 swept budgets**, so this is a real policy
   choice and not a distinction without a difference.
3. Where they diverge, skip-on-overflow delivers **strictly more** — never
   fewer episodes, never fewer characters. At a 1,000-character budget it
   delivers two episodes where strict rank-prefix delivers one.

## Change

The drop order is named `marginal_gain_order_skip_on_overflow`, exported as
`episodic._packing.DROP_POLICY`, reported on every `ContextReport`, and
documented at its definition including a worked example of how it differs
from strict rank-prefix.

## Rationale

- The binding requirement is met. The policy is specified, documented,
  deterministic — ties break on scaled gain, then cost, then source turn,
  then id — and E5 asserts identical drop order across two processes.
- Strict rank-prefix would leave budget unused for no measured gain. Its
  stated rationale in 1.2.2 is that it "requires no new heuristic", and
  skip-on-overflow requires none either: it is the same ranking, restricted
  at each step to what fits.
- CC-002's T3 certifies 132 committed A3 payload SHA-256 values byte-for-byte
  through this package. Skip-on-overflow is the behaviour those payloads
  were produced under. Changing it would invalidate that certification at
  every budget except the operating point, in exchange for delivering less.

## Exclusions

- No change at the operating point: T3 re-run under CC-003 reports 132/132
  payload SHAs matching and the primary vector unchanged.
- This amendment does not touch requirement 1.2.1 (the ceiling), 1.2.3
  (the truncation signal), 1.2.4 (degradation), or 1.2.5 (report before
  block).
- The comparison is one store, one query, one selector configuration. It
  establishes that the policies differ and in which direction; it is not a
  general optimality claim about either.

## Authorization

Recorded under `AGENTS.md` §5 as a standalone amendment. The locked
pre-registration is unedited.
