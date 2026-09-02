# DA-024 Backreference Residual Blocker Audit Report

**Status:** corpus-specific residual mechanisms; no shared successor
**Date:** August 30, 2026
**Protocol commit:** `7d18c15e`
**Standing:** spent evidence-aware causal audit

## Result

All 58 one-hop-reachable DA-023 residual misses are classified with no
unaccounted item.

| Blocker | NF-004 (n=10) | LongMem (n=48) |
|---|---:|---:|
| Prior additive consumption | **7** | 17 |
| Wrong frozen singleton member | 2 | **20** |
| Initial backreference size | 0 | 6 |
| Multi-pair conjunction | 1 | 5 |

NF meets the registered 60% dominance rule for
`DOMINANT_PRIOR_ADDITIVE_CONSUMPTION` at 70%. LongMem is
`MIXED_RESIDUAL_BLOCKERS`; wrong member is its largest class but only 41.7%.
There is no shared successor signal.

## Mechanism

NF begins additive traversal with median 1,015 characters of recovered slack,
against median required cost 123, but carriers arrive with only 88 characters.
The codec has already made the evidence affordable; earlier additive links use
the space first.

LongMem begins with median 611 characters of slack against cost 272 and arrives
with 247. Its main residual is different: 20 items have evidence in the other
member of an exposed pair while the frozen lexical singleton omits it. Seventeen
more are prior-consumption cases, six remain too large initially and five need
multiple pairs.

## Direction

The next branches should be corpus-specific:

- LongMem: immutable-baseline additive atomic-member fallback addresses the
  largest named class without risking control evidence.
- NF: additive allocation among recovered-capacity links is the dominant issue.
  Any successor must preserve the strongest baseline and compare whole additive
  packs; another local substitution guard is already closed by DA-020.

Classification artifact SHA-256 is
`22225c9563bf82b12a9a9804d75e227722242148f9f7454420afc0619046d771`.
Replay is byte-identical with zero model, embedding and cache calls. Diagnostics
use evidence identities and are not deployable rules or reader validation.

