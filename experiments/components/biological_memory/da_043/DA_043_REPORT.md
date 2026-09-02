# DA-043 Report

## Verdict

`SHALLOW_SINGLETON_DEREFERENCE`

Every one of DA-042's 18 residual dependency sets resolves to exactly one
frontier node. No conjunction requires multiple fetches.

| Measure | p50 | p90 | Max |
|---|---:|---:|---:|
| Sequential frontier depth | 15 | 21.9 | 30 |
| Rendered payload chars | 351 | 463.5 | 1,906 |

One target is the head node, four occur at positions 2-8, and thirteen occur at
positions 9-32. Sixteen payloads fit within 512 rendered characters, 17 within
1,024, and all 18 within 2,048.

This changes the downstream picture. The control-plane graph does not require
an unbounded search or multi-node evidence assembly on these residuals. A fixed
first-32 traversal is sufficient, and payloads are generally small enough for
transient fetches. The next test can therefore materialize a deterministic
first page in auxiliary capacity without scoring or modifying DA-038.

This audit does not establish reader use or delivery. Its burden artifact
replays byte-identically at
`40f38cbe15251d7ce93502f8ccdbfd3b69346c07ded8aaa3c30d446457871540`.
Model, embedding and cache calls: zero.
