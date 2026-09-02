# DA-041 Report

## Verdict

`FRONTIER_HEAD_SIGNAL`

A single constant-cost head reference makes 17 of DA-038's 18 residual
dependency sets exactly reachable through the frozen external resolver. The
complete DA-038 payload pack remains immutable.

| Residuals | Newly reachable | Still unreachable |
|---:|---:|---:|
| 18 | **17** | 1 |

The blind allocation admits heads on 436/465 questions and resolves 7,551
absent source members. Marker cost is three or five characters depending on
sentinel length. It reaches 16/17 prior-consumption residuals, the sole
initial-size residual, and all four multi-session residuals.

DA-040 spent five characters per member and reached 7/18. DA-041 spends one
constant marker per frontier and reaches 17/18. The gain comes from representing
the deterministic dependency list as a linked structure rather than a flat set
of individual addresses.

The final miss has insufficient rendered slack for even the three-character
head. This isolates an architectural boundary: dependency navigation belongs
in context control-plane metadata, not inside the same evidence-character
budget it is meant to relieve.

The head is not delivered evidence. Reader/tool dereference, materialization,
runtime and fresh transfer remain unvalidated.

Blind head SHA-256 is
`dff352250a1f969caa7c1f1545d919bbd43cad61b09580ece0b7a8b1382a8e18`;
reachability replays byte-identically at
`e91e2e4c40a52477354b0fd4290adf778f4ce2944be2fceb33a794117d782d9b`.
Model, embedding and cache calls: zero.
