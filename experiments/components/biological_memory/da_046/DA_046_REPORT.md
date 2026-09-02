# DA-046 Report

## Verdict

`ORACLE_SINGLE_REGISTER_SUFFICIENT`

The sealed current/retained-frame contract passes every guard, and explicit
oracle retention reaches the complete frozen one-hop availability ceiling.

| Control | Oracle retained frame | Gains | Losses | Ceiling |
|---:|---:|---:|---:|---:|
| 232 | **250** | **18** | 0 | **250** |

The paired exact p-value is `7.629e-6`. Every question type is nonnegative.
The DA-038 prompt remains immutable.

## Capacity Account

The oracle stops immediately after moving the recognized frame into one
2,048-character retained register:

| Oracle path | p50 | p90 | Max |
|---|---:|---:|---:|
| Peak auxiliary chars | 1,851.5 | 2,037.1 | 2,047 |
| Retained payload chars | 355 | 467.5 | 1,910 |
| Cumulative traversal chars | 5,569 | 17,692.2 | not a peak claim |
| Actions visited | 15 | 21.9 | 30 |

This establishes a clean architectural sufficiency statement: immutable prompt
plus linked stream plus one retained node can hold every residual fact without
displacement. It does not make the traversal free; cumulative processing is
still substantial.

## Boundary

The oracle uses evidence identities to decide when to `KEEP`. Therefore this is
not a selector, deployable stopping rule, reader result, or adoption claim. The
remaining causal question is narrow: can a reader recognize a relevant frame,
retain it, and stop without oracle labels?

Blind contract SHA-256 is
`83290a8bbeacdbc8b6a436dcadb314976c1daee09aa56c570b95096b87879089`;
oracle paths replay byte-identically at
`ec054430acce0d54c9cbbb08f63cc8fa07fb4a58fc20ca2eea68a58dff59f119`.
Model, embedding and cache calls: zero.
