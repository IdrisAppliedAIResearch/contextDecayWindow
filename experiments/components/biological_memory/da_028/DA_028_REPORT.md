# DA-028 Shortest Exact Codec Report

**Status:** `PARTIAL_SHORTEST_EXACT_CODEC_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `7c90b67b`
**Blind allocation commit:** `24ff3df1`
**Standing:** spent cross-corpus exact-availability result

## Result

Evidence-blind shortest-codec selection preserves every DA-023 payload and
adds six protected LongMem completions, but only one NF completion.

| Corpus | DA-023 | DA-028 | Gains | Losses | Exact p |
|---|---:|---:|---:|---:|---:|
| NF-004 | 976 | **977** | 1 | 0 | 1.0 |
| LongMemEval | 202 | **208** | 6 | 0 | .03125 |

LongMem independently clears the registered +5/zero-loss bar. The joint strong
bar fails because NF is below its partial +2 threshold, yielding the registered
`PARTIAL_SHORTEST_EXACT_CODEC_SIGNAL` disposition. Every conversation and
question type is nonnegative.

## Representation Mechanism

Compact relative pointers are selected on all 1,098 NF questions and 461/465
LongMem questions. Four LongMem rows retain DA-023 because compact encoding is
not strictly shorter. Median immutable savings are 591 characters on NF and
556 on LongMem, with no question-wise expansion.

Those savings fund 2,599 NF and 548 LongMem frozen-order additions. LongMem's
six gains contain five DA-024 prior-consumption rescues and one wrong-member
rescue. NF's sole gain is a prior-consumption rescue in conv-49.

This separates capacity from dependency access. More compact representation is
causal on LongMem, where the right carriers occur within the newly affordable
suffix. NF receives more additions yet almost no completion gain. The NF
ceiling is therefore no longer explained by raw byte supply alone; the frozen
traversal is materializing many non-required dependencies before or instead of
the remaining required conjunctions/carriers.

## Boundary

DA-027's universal-codec failure was an instrument failure fixed by exact
fallback, not a failure of relative pointers. DA-028 verifies that a reversible
codec portfolio can add capacity without displacement. It does not establish
reader interpretation, runtime viability or fresh transfer.

NF remains 9 below its one-hop ceiling of 986; LongMem remains 42 below 250. A
new residual audit should determine whether DA-028 changed the remaining class
from prior consumption to wrong member, conjunction, or traversal exclusion.
Another substitution score is not justified by this result.

Blind allocation SHA-256 is
`0ae01f5cdbc4d244c3188778f1b90292211101a56d118e467bd8c9f32b44f21a`;
outcomes replay byte-identically at
`18b77b06e3c9b27b192ba4e0fd9c4c9d89f36111f625914145e8ca8019a41a46`.
There were zero model, embedding and cache calls. No adoption follows.

