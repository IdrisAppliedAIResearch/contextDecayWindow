# Study 010 Exploratory Mechanism Analysis

Generated after commit `32ffed4a` sealed the blinded scores and the anonymous
mapping was opened. Evidence produced under Amendment 004 is post-stop
exploratory and does not reverse the original G2 failure.

**Post-publication boundary:** Study 010 was outside the scoring-integrity
audit, so 21.5/23 and 16.5/23 are unaudited. Arm L's Q13/Q14 LTM blocks also
violated `B_ltm = 32,000` by 67.9%/68.2%. Scores describe the oversized prompts
the model received; they are not a compliant architecture comparison.

## Score Result

| Arm | Anonymous label | Interim / 9 | Terminal / 14 | All probes / 23 |
|---|---|---:|---:|---:|
| L | arm_A | 7.5 | 14.0 | 21.5 |
| S | arm_B | 4.5 | 12.0 | 16.5 |

L exceeds S by 2.0 terminal points, clearing the registered 1.5-point Bar 1
threshold numerically. The original exploratory `RETAIN LTM` consequence is
not a compliant architecture verdict because Arm L exceeded its LTM budget.

All 12 terminal targeted questions scored 1.0 in both arms. The terminal gap
is exactly the two breadth questions: L scored 1.0 on Q13 and Q14; S scored
0.0 on both.

## Fact Delivery

| Arm | Probe | Required | In prompt | Recalled | Unused | Absent |
|---|---|---:|---:|---:|---:|---:|
| L | Q13 | 12 | 12 | 12 | 0 | 0 |
| L | Q14 | 12 | 12 | 12 | 0 | 0 |
| S | Q13 | 12 | 2 | 1 | 1 | 10 |
| S | Q14 | 12 | 1 | 1 | 0 | 11 |

Every required L breadth pair appeared in `<retrieved_ltm>` at both terminal
probes. None appeared in L's `<retrieved_stm>` block. S had no LTM block and
its sparse delivered pairs came from recency. This directly attributes the
terminal score gap to unique LTM delivery rather than unsupported recall.

The interim breadth separation is already visible at turns 250, 500, and 750:
L scores 1.0 on every breadth probe and S scores 0.0 on every breadth probe.
The aggregate interim fractions must not be interpreted as degradation.
I2, I5, and I8 each ask for two facts that are not planted until after the
probe, imposing a maximum score of 0.5. See
`targeted_and_curve_validity_audit.md`.

## Retrieval And Topic Failure

Arm S logged 203 K retrieval events across Q1-Q12. Every one of the 60
required targeted facts appeared in `<retrieved_stm>` and was recalled. Only
Q1 also received three required facts through recency; Q2-Q12 received none
of their required facts there. Arm S's perfect targeted score is therefore
genuine long-range STM retrieval, not ten-episode recency recall.

An earlier version of this analysis incorrectly reported zero K hits because
its rubric parser misclassified the domain column. The parser and generated
K artifact were corrected before merge.

Both arms ended with two topics, reproducing the mass-merging side of the
binding G2 failure. The continuation therefore cannot validate the topic
subsystem or support a confirmatory Study 010 claim. It does show that the
accepted LTM tier preserved cross-domain breadth despite that known failure.

## Cost And Integrity

| Arm | Peak estimated tokens | Mean estimated tokens | Turn 1000 |
|---|---:|---:|---:|
| L | 27,154 | 13,495.9 | 14,798 |
| S | 17,541 | 5,103.5 | 1,588 |

Both peaks remained below the 40,000-token monitor. Arm L formed 290
offset-verbatim content records across 63 dream events, with zero offset
mismatches, zero non-content records, and zero dream inference calls. Arm S
formed no LTM records, as designed. Both arms persisted zero rules, completed
1,000 turns, and wrote all ten checkpoints.

Arm L required a logged resume from turn 500 after its detached process was
reaped during turn 597. Arm S completed in one process. G4 checkpoint/restore
tests passed before execution.

## Evidence Boundary

The original confirmatory outcome remains **STOPPED AT G2**. Under Amendment
004, the exploratory continuation passes Bar 2 and applies Bar 1 unchanged,
yielding exploratory retention of LTM. Bar 3 is `NOT EVALUABLE` because three
construct-invalid probes prevent delivery of the registered degradation
curves. The continuation cannot convert the stopped confirmatory study into
VALIDATED.
