# Study 009 Mechanism Analysis

Generated after blinded scores were committed and the mapping was unsealed.

## Score and null-test result

| Arm | Anonymous label | Q1-Q13 | Q14 |
|---|---|---:|---:|
| L | arm_A | 12.0 | 0.5 |
| S | arm_B | 10.5 | 0.0 |

Arm S trails Arm L by 1.5 points on Q1-Q13. Under the locked null-test rule, this is evidence of LTM value at the 120-turn scale and cancels retirement. Prediction P1 (S >= L) is refuted.

## Atomic delivery

| Arm | Probe | Delivered / 17 | Recalled | Unused | Invented | Absent |
|---|---|---:|---:|---:|---:|---:|
| L | Q11 | 10 | 10 | 0 | 0 | 7 |
| L | Q14 | 14 | 6 | 8 | 0 | 3 |
| S | Q11 | 6 | 6 | 0 | 0 | 11 |
| S | Q14 | 6 | 3 | 3 | 0 | 11 |

The complete item-level matrix is `fact_delivery_matrix.csv`. A delivered item appears anywhere in the constructed prompt; a recalled item appears in the assistant-only answer. `unused` means delivered but not recalled, and `invented` means recalled without delivery in that turn's prompt.

## Score-gap anatomy

- Q5 accounts for 1.0 point. Arm L's turn-116 prompt contains both `lead white ground` and `ultramarine glaze`; Arm S's contains neither. L recalls both and S recalls neither.
- Q8 accounts for 0.5 point. Arm L's turn-119 prompt contains photophore context but not the exact `mantle margin` phrase; it answers both parts correctly. Arm S receives neither term and gives the wrong location. This is compatible with contextual support but is not clean exact-fact delivery attribution.
- Q14 adds a separate 0.5-point breadth difference: L names all four domains with one named-only lapse, while S explicitly omits two domains.

## Context cost

| Arm | Turn 120 estimated tokens | Turn 121 estimated tokens |
|---|---:|---:|
| L | 15,079 | 15,448 |
| S | 5,233 | 5,408 |

Arm S used roughly one third of L's estimated prompt tokens at the breadth probes, but the lower cost came with fewer delivered facts and a 1.5-point Q1-Q13 deficit.

## Integrity

- Arm L is the byte-verified accepted Study 007 artifact.
- Arm S completed 121 turns with no forbidden LTM or digest module loaded.
- The Arm S ablation and full run matched byte-for-byte for all first 35 constructed prompts and responses across fresh server lifecycles.
- Git order is pre-score artifact commit `f41d133`, blinded score commit `0e676d2`, then this mechanism analysis.
- The digest failed G1 and was dropped, so digest Bars 1 and 2 are not evaluable.
