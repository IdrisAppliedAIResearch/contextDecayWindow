# DA-040 Scratchpad

## 2026-08-30 - Registration

- Preserve the complete DA-038 pack and charge byte-for-byte.
- Append only compact exact source-member references in final slack.
- Resolve through the frozen edge list and candidate store.
- Measure dependency reachability, not evidence delivery.
- Zero model, embedding and cache calls.

## 2026-08-30 - Result

- Blind gate passes with 3,325 admitted and 4,730 overflowed references. Every
  admitted code costs five chars and resolves exactly; DA-038 is immutable.
- Seven of 18 residual dependency sets become fully resolver-reachable: six
  prior-consumption cases and the one initial-size case.
- Eleven remain unreachable. Per-member reference cost is still linear in the
  frontier length; a single range/head reference is the next structural probe.
- References are external-resolver reachability, not delivered facts.
