# PS-001 - Pattern-Separated Engram Formation Report

**Date:** August 11, 2026
**Design anchor:** `e20d0c0035fc96d0c9181df67d0a0c8eebd5c368`
**Pre-registration SHA-256:** `B525452743673BEC8FBD45E80E81AE2A6342872B2BB58D858F2C544CA315FC6A`
**Initial authorization:** `90e88f86`
**Final-design anchor:** `56442f70269390bed4aa7129e385122fb07f6f5d`
**Final-design authorization:** `df4718f1`
**Implementation anchors:** `9712a5b4`, `4809d84a`, `7469cde9`
**Historical reproduction:** `ea6a9a20`
**Part 1 artifact commit:** `2c755034`
**Two-process determinism:** `04ff100`
**Part 2 Preflight:** `d7776d7f`
**Disposition:** `SPARSE_ENGRAM_CANDIDATE_CHARACTERIZED`
**Outcome ceiling:** `CHARACTERIZED`
**Calls:** zero embedding requests; zero model-generation calls

## Outcome

PS-001 asked whether one deterministic sparse component could form 119 unique
fixed-cardinality episode codes, store all of them as recurrent fixed points,
and recover each source after one deterministic active/inactive swap.

One of the nine registered cells passed all ordered construct gates:

```text
(D_CODE, K_ACTIVE) = (4096, 41)
```

It formed `119/119` unique exact-sparsity codes, stored `119/119` as fixed
points, and recovered `119/119` source codes after one swap. It also recovered
`119/119` at each descriptive 10%, 30%, and 50% swap level. The same complete
exploration in a second process reproduced every deterministic artifact and the
canonical mechanism digest
`0D45DDD45980DBF3989A543136BAD52D4F743F650F3C0AF76E370F049B6C80CC`.

This is exact code-space completion on the registered same-store population. It
is not natural-language cue completion, retrieval improvement, an answer
result, generalization, perturbation robustness beyond the registered cues, or
biological replication.

## Integrity sequence

The design was committed without implementation. Standalone authorization was
then bound to its commit and SHA-256. Three prospective amendments resolved
numerical identity before affected output:

- Amendment 006 fixed population-center order, SHA-256 projection mapping,
  projection accumulation, field tolerance, array identity, and the
  tie-sensitive-margin residual.
- Amendment 007 fixed the descriptive quadratic score, corruption permutation,
  and seven degenerate-cue identities.
- Amendment 008 corrected Amendment 006's normalization path before output. It
  restored the immutable Rev 4 normalized matrix digest
  `2ED0CC29B0DE9B54BF80BBD800123938ECAAC2353B3E01ECE37E397B6844E27B`.

The implementation and tests were committed before real output. Rev 4 was then
reproduced from a detached LF worktree at `0d98be79` using the retained database
bound to SHA-256
`5DA47EA3FC2C8E3DCC50FA380FF65202D82557905D9976117E9E5D82E55C1C41`.
It reproduced `119/119` converged traces, `0/119` stored fixed points, six
terminal states with basin sizes `5, 13, 15, 20, 29, 37`, and exact result
SHA-256
`1942950078E0A7EB30619F66356E0373208372415B401B61A49DAE6FE8CDAA78`.

The first complete PS-001 process was committed before its result was opened.
The second process then reproduced its deterministic artifacts byte-for-byte.
Only after the comparison passed was the mechanical selection opened and the
prospective final design committed.

## Grid result

All cells passed G1 input/encoder integrity and G2 recurrent identity. Eight
failed G3 and stopped before degraded cues.

| Cell `(D_CODE, K_ACTIVE)` | G3 fixed points | G4 one-swap | G5 | Cell disposition |
|---|---:|---:|---|---|
| `(2048, 20)` | 117/119 | NOT REACHED | NOT REACHED | `SPARSE_CODES_NOT_STORED` |
| `(2048, 41)` | 109/119 | NOT REACHED | NOT REACHED | `SPARSE_CODES_NOT_STORED` |
| `(2048, 102)` | 103/119 | NOT REACHED | NOT REACHED | `SPARSE_CODES_NOT_STORED` |
| `(4096, 41)` | **119/119** | **119/119** | **PASS** | `SPARSE_ENGRAM_CANDIDATE_CHARACTERIZED` |
| `(4096, 82)` | 110/119 | NOT REACHED | NOT REACHED | `SPARSE_CODES_NOT_STORED` |
| `(4096, 205)` | 101/119 | NOT REACHED | NOT REACHED | `SPARSE_CODES_NOT_STORED` |
| `(8192, 82)` | 118/119 | NOT REACHED | NOT REACHED | `SPARSE_CODES_NOT_STORED` |
| `(8192, 164)` | 111/119 | NOT REACHED | NOT REACHED | `SPARSE_CODES_NOT_STORED` |
| `(8192, 410)` | 92/119 | NOT REACHED | NOT REACHED | `SPARSE_CODES_NOT_STORED` |

Dimension alone did not determine storage. The 8,192-unit cells did not pass,
and increasing activity within a dimension generally reduced fixed-point count
on this one grid. The protocol permits no interpolation, seed sweep, or causal
claim about that pattern.

## Selected-cell formation

Every selected code has exactly 41 active units. Across all 7,021 episode
pairs, code overlap ranges from 0 to 25 with median 0; Hamming distance ranges
from 32 to 82 with median 82. Input cosine ranges from -0.0578 to 0.8907 with
median 0.1636. Thus even the closest dense-input pairs remain separately
identified, but the same-store distribution is not a generalization estimate.

The projection's active/inactive boundary margin ranges from `2.13e-6` to
`0.001110`, median `0.000206`, with zero registered tie-sensitive formation
margins. Unit use is uneven: per-unit population count ranges from 0 to 8 with
median 1, and 1,351 of 4,096 units are unused. Unique sparse codes therefore do
not imply uniform code-space use.

The independently chunked real-field implementation matches the production
operator exactly at observed precision; maximum absolute field error is 0. The
stored-state competition margin ranges from `0.03527` to `0.86887`, median
`0.78565`, with zero tie-sensitive stored states. The conceptual zero-diagonal
matrix has 11,029,500 negative entries, 5,743,620 positive entries, and 4,096
zeros. Its nonzero density is 0.999755859375. Sparse codes therefore do not make
the learned conceptual recurrent matrix sparse; deployability here comes from
the implicit low-rank operator.

## Recall and basins

All uncorrupted sources verify as fixed points in one sweep. Every registered
degraded source returns to its exact code on the first changing sweep and
verifies the fixed point on the second:

| Cue | Exact source | Spurious | Cycles | Runtime guards | Sweeps |
|---|---:|---:|---:|---:|---:|
| One swap | 119/119 | 0 | 0 | 0 | 2 for all |
| 10% swaps (4) | 119/119 | 0 | 0 | 0 | 2 for all |
| 30% swaps (12) | 119/119 | 0 | 0 | 0 | 2 for all |
| 50% swaps (20) | 119/119 | 0 | 0 | 0 | 2 for all |

The minimum competition margin over these registered corruptions is `0.02582`.
No corrupted-source sweep is tie-sensitive.

The degenerate audit exposes the boundary. Lowest-index, highest-index, and all
four hash-seeded random states converge to stored codes in 3-5 sweeps. The
union-biased state enters a two-cycle with a spurious terminal state. All seven
degenerate traces contain a zero competition margin, totaling 13 tie-sensitive
sweeps. Exact registered recovery therefore coexists with cycle behavior and
index-tie dependence outside the source-centered corruption family. No claim of
a globally clean attractor landscape is permitted.

## Resources and determinism

The complete first process took 26.76 seconds. The slowest cell took 5.92
seconds. Maximum observed process RSS across cells was 157,241,344 bytes, and
the largest estimated live NumPy-array footprint including audit chunks was
58,590,136 bytes, both below the registered 536,870,912-byte live-array ceiling.
No cell approached its 600-second ceiling or the grid's 3,600-second ceiling.

Projection, code, operator, conceptual-weight, trace, terminal-sequence, and
artifact digests reproduce across two separate processes. Thread counts were
fixed before NumPy import. No server or model process existed.

## Preflight Part 2

PF1-PF10 all pass in the committed artifact-bound Preflight. It verifies 602
selected-cell traces: 119 each for uncorrupted, one-swap, 10%, 30%, and 50%
cues, plus seven degenerates. Every trace terminates at a fixed point, cycle, or
runtime guard; the selected set contains one cycle and no runtime exits.

Part 2 reruns no selected real-population evidence. It verifies committed
identities, manifests, schema, gate and commit order, planted G1-G4
short-circuits, synthetic gate/disposition reachability, stable content/code/
state hashes, historical reproduction, resource ceilings, and all registered
surrogate residuals.

## Construct and surrogate disposition

Demonstrated on this fixed store:

- deterministic 1,024-to-4,096 sparse expansion;
- 119 unique 41-active internal codes with complete pairwise separation data;
- independently reconstructed centered learned recurrence;
- exact fixed-point storage and registered code-space completion;
- deterministic fixed-cardinality competition and registered basin traces.

Still false or untested despite a pass:

- a single seed can be fortuitous and same-store cell selection can overfit;
- bit-swap completion need not survive natural embedding or language cues;
- unused units, dense conceptual weights, zero-margin degenerates, a spurious
  terminal, and a two-cycle remain;
- registered cues do not enumerate multiple unrelated memories;
- offline code recovery need not improve retrieval or answer correctness;
- the component does not replicate dentate gyrus, CA3, or the hippocampus.

## Stop and advancement

PS-001 stops at `CHARACTERIZED`, as registered. No Q11 import, fact count,
retrieval rank, packing, answer generation, live inference, promotion,
adoption, or production change was reached. The only permitted next question is
a separately pre-registered natural-language cue-binding study, followed by a
separately registered live evaluation if cue binding first succeeds.

## Verification

- Focused PS-001 suite before Part 1: 28 passed after the retained-control and
  Windows RSS fixes.
- Focused PS-001 suite after Part 2 implementation: 31 passed.
- Full repository suite at the implementation anchor: 1,466 passed.
- Final closeout verification: 31 focused tests and 1,470 full-repository tests
  passed. `git diff --check`, conflict-marker checks, and the 369-character
  AGENTS digest cap also pass. See
  `artifacts/ps001_closeout/verification.json`.

## Artifacts

- `artifacts/ps001_exploration/rev4_reproduction.json`
- `artifacts/ps001_exploration/part1_process_1/exploration.json`
- `artifacts/ps001_exploration/part1_process_1/cell_summary.csv`
- `artifacts/ps001_exploration/part1_process_1/artifact_manifest.json`
- `artifacts/ps001_exploration/two_process_determinism.json`
- `artifacts/ps001_preflight/preflight.json`
- `artifacts/ps001_closeout/verification.json`

`ERRATA.md` is unchanged because PS-001 changes no published prior number.
