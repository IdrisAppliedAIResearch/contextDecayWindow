# DA-094 Prompt Dependency Topology

**Status:** `COMPLETE; FRAGMENTED_PROMPT_DEPENDENCY_TOPOLOGY`
**Date:** August 31, 2026
**Parent:** DA-093 result commit `c260f080`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Do DA-093's exact child encodings depend on a small coherent set of immutable
prompt members, or many scattered spans that behave as compression rather than
a useful dependency graph?

## Frozen Population And Parse

Use all 3,499 DA-093 selected rows and reconstruct the committed deterministic
minimum-character parse against the same immutable DA-078 history. No encoding,
packet, target, order, edge, cost or selection may change.

For every child report pointer count, referenced characters, literal characters,
unique referenced prompt members, pointer distance, and concentration in the
largest source member. Report distributions and route cells.

## Disposition

Report `COHERENT_PROMPT_DEPENDENCY_TOPOLOGY` only if unique referenced members
are p50 <=4 and p90 <=8, pointer count p50 <=16, and largest-source referenced
character share p50 >=.50. Otherwise report
`FRAGMENTED_PROMPT_DEPENDENCY_TOPOLOGY`.

The coherent result authorizes a compact dependency-manifest probe. A fragmented
result instead authorizes an exact constrained node-local codec comparison. No
reader, evidence delivery, runtime, fresh-transfer or adoption claim. Require
exact decode, byte-identical replay and zero calls.

## Result

The exact topology is fragmented. Pointer count is p10/p50/p90 79/123/162 and
unique referenced prompt members are 18/24/29. The largest source accounts for
only p10/p50/p90 14.72%/23.43%/42.16% of referenced characters, while total
reference coverage is 39.34%/54.07%/68.64%.

Median pointer distance is 23 prompt members. Both route cells fail the coherent
bars. Accounting is exact, DA-093 is unchanged, replay is byte-identical and no
calls were made.

DA-093 is therefore strong compression but not a sparse dependency graph. The
authorized successor is an exact node-local codec that retains references from
one representation-dominant prior member and expands all other spans literally.
