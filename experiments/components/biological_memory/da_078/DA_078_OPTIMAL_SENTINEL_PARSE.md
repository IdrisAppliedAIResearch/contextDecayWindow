# DA-078 Protected Optimal Sentinel Parse

**Status:** `COMPLETE; PROTECTED_OPTIMAL_PARSE_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-077 result commit `c7f14336`
**Control:** complete sealed DA-038 allocation and order
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can a globally shortest parse under DA-038's exact sentinel-pointer language
recover additional capacity while preserving every member and the complete
strongest order?

## Protected Control

Use all 465 LongMem questions at 16,000 characters. Freeze DA-038's complete
decoded identity/member sequence, order, role pattern, and delivery 232. No
control member may be removed, replaced, reordered, or displaced.

## Fixed Treatment

Retain DA-038's sentinel, backward-member span-reference syntax, reference
cost, and exact decoder. Replace only the greedy longest-match parser with
backward dynamic programming that minimizes encoded characters for each member
against prior decoded members. Literal characters cost one. References retain
DA-038's exact variable-length code. Resolve equal-cost parses by literal first,
then source member, source offset, and longer span.

Select the optimal parse only when strictly shorter than DA-038's complete
charge. Then traverse DA-038's frozen baseline edge/member order and append
absent members independently on exact fit, continuing after overflow. Never
retry. No outcome, evidence marker, score, threshold, sweep, or new codec enters
allocation.

## Gates And Disposition

Before outcomes require 465 exact joins; exact decode; byte-identical protected
identity/member order; optimal charge never above the greedy charge for the
same sequence; positive strict savings, admissions, and overflows; <=16,000;
byte-identical replay; zero calls. Stop unopened on failure.

Report `PROTECTED_OPTIMAL_PARSE_SIGNAL` for >=5 complete-delivery gains, zero
losses, and every question type nonnegative. Report `WEAK_PROTECTED_OPTIMAL_PARSE_SIGNAL`
for 2-4 gains under the same guards. Otherwise report
`NO_PROTECTED_OPTIMAL_PARSE_SIGNAL`. This is availability only; reader/runtime,
fresh transfer, and adoption remain unvalidated.

## Result

The blind gate passes on 465/465. The globally shortest parse preserves the
complete DA-038 member sequence and order, recovers median 273 characters
(p10 198.8, p90 359.6), and admits 618 additional members after the immutable
control. Replay is byte-identical and final charge never exceeds 16,000.

Complete evidence rises 232->237: 5 gains, 0 losses, two-sided exact p=.0625.
Every question type is nonnegative. All five gains resolve
`PRIOR_SENTINEL_ATOMIC_CONSUMPTION`, matching the registered capacity mechanism.

The exact double replay took roughly 25 minutes and peaked near 1.2 GB in this
environment. Range-min acceleration is exact against a brute-force oracle, but
production runtime remains unvalidated. Zero model, embedding, and cache calls.

Artifacts:

- `artifacts/preflight/blind_allocations.jsonl.gz`
- `artifacts/preflight/preflight.json`
- `artifacts/result/outcomes.jsonl.gz`
- `artifacts/result/result.json`
