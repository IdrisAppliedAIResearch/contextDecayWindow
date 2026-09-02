# DA-079 Optimal-Parse Residual Audit

**Status:** `POSTHOC_OPTIMAL_PARSE_RESIDUALS_CHARACTERIZED`
**Date:** August 31, 2026
**Parent:** DA-078 result commit `f42f699d`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Scope

DA-078 reaches 237 of the 250 frozen one-hop ceiling, leaving 13 reachable
misses. This evidence-aware audit identifies where each required atomic member
loses fit under the exact DA-078 allocation. It cannot authorize a new order.

## Fixed Replay

Freeze DA-078's complete protected sequence, optimal parse, append order,
admissions, skips, costs, and final charge. Join only the 18 sealed DA-039
residual requirements, remove the five delivered by DA-078, and require exactly
13 unresolved rows.

For each required member compute exact optimal-sentinel cost and slack at:

1. the initial state before any DA-078 append;
2. its frozen baseline-order arrival; and
3. the final DA-078 state.

Classify `INITIAL_OPTIMAL_ATOMIC_SIZE` when it does not fit initially,
`PRIOR_OPTIMAL_ATOMIC_CONSUMPTION` when it fits initially but not at arrival,
and `POSTPACK_FIT` when it fits after the completed pack. Stop on an unaccounted
case, charge mismatch, changed action, or protected-order mismatch.

Report blocker counts and cost/slack distributions. Byte-identical replay and
zero model, embedding, and cache calls are required. This is spent causal
anatomy only; no allocation, reader, runtime, transfer, or adoption claim.

## Result

All 13 residuals are accounted for. Nine are
`PRIOR_OPTIMAL_ATOMIC_CONSUMPTION`: each fits in initial optimal slack, then
loses fit to earlier append-only admissions. Four are
`INITIAL_OPTIMAL_ATOMIC_SIZE`; their initial deficits are 23, 98, 143, and
1,391 characters. No required member fits after the completed tail.

For the nine prior-consumption rows, arrival deficits are 28-245 characters
while initial headroom is 60-149 characters beyond required cost. The dominant
remaining boundary is therefore materialization scheduling under immutable
order, not another parse score. Byte-identical replay; zero calls.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/classifications.jsonl.gz`
