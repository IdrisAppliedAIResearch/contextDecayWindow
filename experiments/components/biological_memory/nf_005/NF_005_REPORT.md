# NF-005 Report - Source-Turn Candidate Information Dilution

**Status:** `INFORMATION_DILUTION_SUPPORTED - CHARACTERIZED`
**Pre-registration:** `04d3713880419a970d71c098a03b4df0965b18f0`
**Corpus:** the same 465 LongMemEval items used by NF-003
**Budget:** 32,000 candidate-text characters
**Model calls:** 0
**Embedding calls during measurement:** 0
**Date:** August 13, 2026

## Result

NF-005 supports its registered candidate information-dilution prediction on the
exhausted LongMemEval corpus. With source-turn packing held fixed, ranking each
turn by its own query cosine raises any exact evidence-turn delivery from
**361/465** under inherited parent-episode scores to **461/465**. The paired
result is **100 gains, 0 losses, 365 ties**, net +100, with one-sided exact
binomial p = **7.89e-31**.

The upper registered tier required gains at least twice losses and p <= .05.
Both conditions pass, giving `INFORMATION_DILUTION_SUPPORTED`. The result is
capped at `CHARACTERIZED`: LongMemEval and the motivating NF-003 outcome were
already observed before this registration.

| Arm | Any exact evidence | All exact evidence |
|---|---:|---:|
| Episode rank, episode pack | 351/465 | 201/465 |
| Episode rank, turn pack | 361/465 | 208/465 |
| **Turn rank, turn pack** | **461/465** | **454/465** |
| Source order, turn pack | 64/465 | 7/465 |

The source-order control remains far below either ranked arm, and all stores
bind at 32k. The result is therefore neither a source-order artifact nor a
slack-budget ceiling. Turn ranking moves median best evidence rank from 5 to 1
and p90 from 131 to 7 while delivering a median 109 turns rather than 46.

## Mechanism

The exploration localized the scale difference before vectors were captured.
LongMemEval evidence episodes have median 2,550 characters, while their exact
flagged source turns have median 298; LoCoMo adjacent pairs have median 241.
Of 881 LongMemEval evidence flags, 831 are on user turns. Longer parent episodes
also have worse normalized own-cosine evidence rank overall (Spearman rho
0.484) and within every question class.

Together with NF-003 and NF-004, the supported design rule is conditional rather
than corpus-specific: **rank at the finest unit whose embedding remains
informative; pack at the finest affordable unit.** LongMemEval episodes were too
broad for their own cosine, so session pooling rescued them; splitting those
episodes to evidence-scale turns restores the fine-ranking advantage. LoCoMo's
already short pairs showed the same fine-ranking direction prospectively.

This test does not isolate raw character count. Source-turn splitting shortens
the candidate and localizes its semantics simultaneously. A controlled padding
or aggregation study on an untouched corpus would be required to identify
length separately.

## Gates and integrity

| Gate | Result | Evidence |
|---|---|---|
| G0 registration identity | PASS | first commit and LF SHA match |
| G1 inputs and population | PASS | 465 items, 106,412 episodes, 212,824 turns, 881 flags |
| G2 leakage | PASS | evidence-blind mechanism; planted import and field rejected |
| G3 anchor/control | PASS | 351/361/208 and full row digest reproduced |
| G4 implementation | PASS | 319,236 unique candidate identities; exact parent links and costs |
| G5 vector seal | PASS | 167,918 hits, zero misses; file/content/model/call-shape sealed |
| G6 determinism | PASS | two evidence-blind selections byte-identical |
| G7 outcome | PASS | sealed before diagnostics at commit `c5c7e8d7` |
| G8 integrity | PASS | outcome replay byte-identical; registered disposition applied once |

The exact-solo capture made 167,919 calls: one registered sentinel plus 167,918
unique source-turn texts. It ran sequentially with one thread as registered.
The cache writes transactions incrementally but deliberately cannot resume an
interrupted unsealed file; one early foreground attempt was discarded and the
successful detached run started from an empty path. AC sleep and hibernation
were disabled for the run. The final cache is 1,289,318,400 bytes, file SHA-256
`9c3321a524a7e92b928ff9eb4da241d1081b09ec3ee962a0b89189f5315dbf47`,
and canonical content SHA-256
`1a616a9a95da31eea0592d4fdec7af7f73d23d57f4e6d0f745c7145aa318c527`.

## Boundaries

This is evidence availability, not reader correctness. It authorizes no live
run, promotion, or adoption. The exact evidence labels may still be incomplete,
and delivering them need not produce a correct answer. The result also does not
make LongMemEval a fresh confirmation corpus or establish a universal character
threshold.

## Integrity trail

| Artifact | Commit | SHA-256 |
|---|---|---|
| registration | `04d37138` | LF `69ba2e52753a2c` |
| vector manifest | `b918d996` | `8b85f45df3bdd28e` |
| G0-G6 preflight | `d6b16c31` | `1c217a6c2bbffc4b` |
| G7 sealed outcomes | `c5c7e8d7` | `06e4cbeacc2952b5` |
| G8 integrity | `f09544ae` | `17cbdbad274c1863` |

The G8 outcome and replay SHA-256 values are both
`06e4cbeacc2952b5ec0fd93cebf9bfc3483166f6a1f72da232e5f371d7b7b322`.

