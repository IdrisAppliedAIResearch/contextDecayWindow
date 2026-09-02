# HH-005 Findings - semantic plus DA aspect-v2

**Status:** `COMPLETE - NO_ASPECT_V2_IMPROVEMENT`

## Result

| Arm | Correct | Score | F1 | Exact match |
|---|---:|---:|---:|---:|
| Semantic + DA-v2, 16k | 649/842 | 77.08% | .4435 | .0119 |
| Semantic + DA-v2, 32k | 654/842 | 77.67% | .4469 | .0059 |
| Semantic + ASPECT-v1, 32k | 670/842 | 79.57% | .4500 | .0143 |

The corrected DA-v2 architecture did not improve ASPECT-v1. At 16k it gained
26 items and lost 47 versus v1 (net -21, two-sided p=.0186). At 32k it gained
32 and lost 48 (net -16, p=.0929). Increasing DA-v2 from 16k to 32k produced
27 gains and 22 losses, only net +5 (p=.568).

## Reading

This corrects HH-004's composition error. Preserving the semantic half restored
most of the lost performance: 32k rose from HH-004's 71.97% DA-only score to
77.67%. That confirms the semantic channel was essential.

DA-v2 nevertheless remains weaker than ASPECT-v1. Its derivative half finds
real complementary evidence, demonstrated by 32 rescues, but substitutes a
different set of useful contexts and causes 48 losses. More capacity does not
solve that selection problem: doubling the retrieval allowance changes 49
answers but yields only five net gains.

The practical conclusion is not that linked derivative context is useless. It
is that the current DA order is not yet a better aspect allocator. Availability
and exact codec capacity are largely solved; selecting derivative carriers that
remain useful to the reader is the unresolved mechanism.

## Operations

Both arms completed 842 answers and 842 judgements with zero malformed labels
and zero failed items. Median contexts were 28,208 characters at 16k retrieval
and 44,226 at 32k because the recent window is additive. Median answer latency
was .956 and 1.050 seconds. Four watchdog restarts recovered by stable key.

## Disposition

`NO_ASPECT_V2_IMPROVEMENT`. Do not replace ASPECT-v1 with this DA-v2 allocator.
Any successor should preserve the frozen semantic half and directly target the
32 DA rescues without incurring the 48 v1 losses. No result here supports
compact-wire interpretation, fresh transfer, or production adoption.
