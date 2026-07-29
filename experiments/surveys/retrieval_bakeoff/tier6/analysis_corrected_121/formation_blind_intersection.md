# Formation-Blind Plant Intersection

This audit distinguishes the six plants previously described as
unreachable-by-formation from the 17 atomic Q11 rubric items. They are not the
same denominator. The Tier 6 answer's 13/17 therefore cannot be interpreted as
the formation ceiling's 11 plus two of these six plants.

## Relevant-Probe Delivery And Use

| Plant | Plain STM delivery | LTM delivery | Widened STM delivery | Widened STM answer |
|---|---:|---:|---:|---|
| lead white | no | yes | yes | correct on Q5 |
| ultramarine glaze | no | yes | yes | correct on Q5 |
| marine snow | yes | yes | yes | correct on Q7 |
| photophores | no | yes | yes | correct on Q8 |
| mantle margin | no | yes, semantic wording | yes | correct on Q8 |
| dual mandate | no at Q11 | yes at Q11 | yes at Q11 | omitted from Q11 |

The exact-string delivery audit is
`analysis_corrected_121/targeted_fact_delivery.csv`. It records all targeted
facts except dual mandate. The latter was checked directly in each committed
turn-120 constructed prompt. Study 007 L and widened STM contained dual mandate;
Study 009 S did not. The L prompt expressed the mantle location semantically,
which explains the exact-string audit's false negative even though the L answer
earned full Q8 credit.

Widened STM thus made all six formation-blind plants available at their
relevant probes and correctly used five. This supports a formation-specific
blindness interpretation: raw delivery solved availability for this set. It
did not solve breadth utilization, because dual mandate was available but
omitted from Q11.

## Scored Arm Difference

`score_comparison.csv` shows that widened STM and L both scored zero on Q11.
Across Q1-Q13, their only score difference is Q4: L scored 1.0 and widened STM
scored 0.0. At turn 115, L received all four Q4 identity facts (title, artist,
patron, and year), while widened STM received none. The one-point architectural
gap is therefore a Q4 selection failure, not a Q11 threshold effect.

