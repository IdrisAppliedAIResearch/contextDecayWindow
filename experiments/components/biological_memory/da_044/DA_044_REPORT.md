# DA-044 Report

## Verdict

`WEAK_AUXILIARY_FRONTIER_PAGE_SIGNAL`

A separate 16,000-character first-frontier page raises complete evidence
delivery from 232 to 237: five gains, zero losses, paired p=.0625.

| Control | Treatment | Gains | Losses | Ceiling |
|---:|---:|---:|---:|---:|
| 232 | 237 | 5 | 0 | 250 |

The capacity cost is the central result. Pages consume 14,817 characters at
the median yet contain only seven nodes because large early payloads exhaust
the buffer. Across 465 questions the treatment adds 6,541,247 characters,
about 1,308,249 per gain when charged across the tested population. Gain rows
still use 14,702 characters at the median.

This is the “more tokens flood into context” mechanism, now measured directly.
The linked order is structurally targeted compared with arbitrary context, but
eagerly materializing its prefix remains grossly inefficient and reaches none
of the remaining multi-session or temporal-reasoning residuals.

The page design is closed. DA-043 suggests the better architecture: traverse
one node at a time in a replaceable transient buffer. That keeps peak added
capacity bounded while reporting cumulative processing cost honestly.

Blind page SHA-256 is
`24e58f888d0f262a86af6c2a97e219175628c4d88aa0c56f3e2236c2ee848730`;
outcomes replay byte-identically at
`cb01d3ed2b0519e203c4871cf7dd10e1feb0effc029e7f01f848d750715a3904`.
Model, embedding and cache calls: zero.
