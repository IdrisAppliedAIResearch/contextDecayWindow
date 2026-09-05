# DA-040 Report

## Verdict

`COMPACT_DEPENDENCY_FRONTIER_SIGNAL`

After preserving the complete DA-038 pack, five-character source-member
references make seven of its 18 remaining dependency sets exactly reachable
through the frozen external resolver. DA-038 has zero mutations.

| Residuals | Newly reachable | Still unreachable |
|---:|---:|---:|
| 18 | **7** | 11 |

The blind allocation admits 3,325 references and overflows 4,730. The seven
reachable cases include six prior-consumption blockers and the sole initial-
size blocker. Exact reference positions have median 7 among reached rows.

This supports separating dependency reachability from payload materialization.
It does not yet solve the linear metadata cost: each member still consumes five
characters, so eleven residuals remain beyond the final-slack frontier. The
next structural step is a single range or head reference to the deterministic
ordered dependency list, making metadata cost independent of member count.

References are not counted as delivered facts. Reader/tool dereference,
payload scheduling, runtime and fresh transfer remain untested.

Blind frontier SHA-256 is
`fb88b0276b20dadd084c0c1080de5c6532711addcb42488e909b5c2f8458c1c3`;
reachability replays byte-identically at
`8cb6dac337f4224724791fa6fecb31fef26ac467143ad5c22a18efe13cb6cef4`.
Model, embedding and cache calls: zero.
