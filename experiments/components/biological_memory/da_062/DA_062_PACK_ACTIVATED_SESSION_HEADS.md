# DA-062 Pack-Activated Session Heads

**Status:** `COMPLETE; NO_PACK_ACTIVATED_HEAD_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-061 result commit `5dcc8e7d`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can the strongest immutable pack itself identify a small, useful dependency
frontier without a new relevance score?

## Blind Route

Use the sealed DA-038 allocation and DA-055 directory. For each question,
construct the ordered represented-episode list from DA-038 `direct_ids`, then
append each `neighbor_id` from `da031_control.actions`,
`da033_control.actions`, and `treatment.actions` whose registered `cost` is
positive. Preserve action order and deduplicate episodes by first appearance.

Resolve every represented episode through the DA-055 episode directory. Emit
its session head on first appearance. No query text, lexical key, cosine,
outcome, required-session label, score, threshold, fitted parameter, reranking,
fallback, or cap may affect the route.

Seal all 465 routes before opening required-session outcomes. Require locked
input hashes, complete episode-to-session resolution, deterministic replay,
positive direct and linked represented populations, route deduplication, zero
protected payload mutation, leakage-clean source, and zero model, embedding,
or cache calls.

After sealing, report complete and any required-session coverage, routed count
and fraction, and required-session route positions. `SELECTIVE_PACK_ACTIVATED_HEAD_SIGNAL`
requires complete coverage >=.90 and p50 routed fraction <=.25. Coverage >=.90
without selectivity is `BROAD_PACK_ACTIVATED_HEAD_SIGNAL`; otherwise
`NO_PACK_ACTIVATED_HEAD_SIGNAL`.

This is address coverage only. It authorizes no substitution. A successor may
test protected, residual-only session traversal only if the registered signal
bar passes. Reader use, stopping, runtime, fresh transfer, and adoption remain
untested.

## Result

Pack activation is selective but incomplete: complete required-session
coverage is 350/465 (.753), any coverage 426/465, and routed fraction is p50
.170 with p50 8 heads. Required sessions are early when present (first/last
p50 1/2), but coverage misses the .90 bar. No traversal is authorized.

Posthoc synthesis shows DA-061 repairs 111/142 missing required sessions and
the union reaches 438/465, but simultaneous union routes p50 .509 of sessions.
This motivates replaceable head streaming as descriptive development, not a
late rescue of DA-062.
