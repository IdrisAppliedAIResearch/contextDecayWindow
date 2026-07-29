# Primary Positive Result: Formation-Blind Fact Recovery

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

This is the memory track's first clean positive result on its hardest documented
failure class. Query-blind formation repeatedly missed these rare technical
phrases; the registered Tier 4 extraction gate also records that spaCy found
zero entities in the vampire-squid span. Raw, non-entity-gated delivery reached
the evidence anyway. That supports the program's differentiation claim against
entity-gated construction, while not constituting a direct HippoRAG benchmark.

## Scored Arm Difference

`score_comparison.csv` shows that widened STM and L both scored zero on Q11.
Across Q1-Q13, their only score difference is Q4: L scored 1.0 and widened STM
scored 0.0. At turn 115, L received all four Q4 identity facts (title, artist,
patron, and year), while widened STM received none. The one-point architectural
gap is therefore a Q4 selection failure, not a Q11 threshold effect.

## Q4 Exclusion Trace

The complete Q4 identity bundle was planted at turn 55, 60 turns before the
turn-115 probe. The patron was reiterated at turn 60, 55 turns before the
probe.

At turn 115, the turn-55 episode ranked 27th under widened STM's registered N
ordering, inside the 32-candidate N cap. The 60,595-character payload budget was
exhausted after packing the first 15 N episodes, so turn 55 was never rendered.
Its query cosine was 0.166, below the registered 0.48 K threshold, so K could
not rescue it. The episode was therefore not absent from the raw store or
ranked outside the N candidate cap; it was structurally excluded by N-first
character packing after ranking too late to fit.

This supports a primacy interpretation of the remaining LTM advantage. The
tier's demonstrated benefit is keeping selected durable facts renderable after
their raw episodes fall behind verbose material. No graph, router, or other LTM
behavior has independently been shown to beat matched raw volume.

The derived values and their committed sources are recorded in
`q4_exclusion_trace.json`.
