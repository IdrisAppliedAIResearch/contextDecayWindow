> **CORRECTION (2026-07-26):** L remains 12.0; S corrects 10.5 -> **9.0**. The null-test gap is 3.0 and remains decisive; digest bars remain not evaluable. Original claims remain below. See `../audits/scoring_integrity/audit_report.md`.

# Study 009 Report: Pure-STM Null Test

**Registration anchor:** `37fff74`
**Pre-registration SHA-256:** `533ec1c1e51497d1c77b2ab187f72f507f2c2f6e92a6b67b2b1021aeec7483bb`
**Protocol amendment:** `5fa1700` (`AMENDMENT_001_protocol_repair.md`)
**Blinded score commit:** `0e676d2`
**Final status:** PARTIAL; NULL TEST DECISIVE, DIGEST REJECTED

## Result

The accepted Study 007 LTM arm (L) scored **12.0/13.0** on Q1-Q13 and
**0.5** on Q14. The new structurally pure STM arm (S) scored **10.5/13.0**
and **0.0** on Q14.

Arm S trails Arm L by **1.5 points** on Q1-Q13. This meets the locked
`S < L by >= 1.0` rule: Study 009 provides direct evidence of LTM value at
the 120-turn scale, and LTM retirement is cancelled. Prediction P1 (`S >= L`)
is refuted.

| Question | Arm L | Arm S | Difference |
|---|---:|---:|---:|
| Q1 | 1.0 | 1.0 | 0.0 |
| Q2 | 1.0 | 1.0 | 0.0 |
| Q3 | 1.0 | 1.0 | 0.0 |
| Q4 | 1.0 | 1.0 | 0.0 |
| Q5 | 1.0 | 0.0 | +1.0 L |
| Q6 | 1.0 | 1.0 | 0.0 |
| Q7 | 1.0 | 1.0 | 0.0 |
| Q8 | 1.0 | 0.5 | +0.5 L |
| Q9 | 1.0 | 1.0 | 0.0 |
| Q10 | 1.0 | 1.0 | 0.0 |
| Q11 | 0.0 | 0.0 | 0.0 |
| Q12 | 1.0 | 1.0 | 0.0 |
| Q13 | 1.0 | 1.0 | 0.0 |
| **Q1-Q13** | **12.0** | **10.5** | **+1.5 L** |
| Q14 | 0.5 | 0.0 | +0.5 L |

Primary and strict scores are identical. The complete rationales are in
`evaluation/rubric_scores.json`.

## Mechanism

At Q5, Arm L's prompt delivered both `lead white ground` and
`ultramarine glaze`; Arm S's prompt delivered neither. This accounts for one
full point of the gap.

At Q8, Arm L received relevant photophore context, although not the exact
`mantle margin` phrase, and answered both parts correctly. Arm S received
neither term and supplied the wrong location. This half-point is compatible
with useful contextual support but is not exact-fact delivery attribution.

The 17-item breadth matrix reinforces the delivery account:

| Arm | Probe | Delivered | Recalled | Unused | Absent |
|---|---|---:|---:|---:|---:|
| L | Q11 | 10/17 | 10 | 0 | 7 |
| S | Q11 | 6/17 | 6 | 0 | 11 |
| L | Q14 | 14/17 | 6 | 8 | 3 |
| S | Q14 | 6/17 | 3 | 3 | 11 |

No locked item was counted as invented in either breadth answer. The item-level
matrix and method are in `evaluation/fact_delivery_matrix.csv` and
`evaluation/mechanism_analysis.md`.

## Cost

Arm S was substantially leaner:

| Arm | Turn 120 estimated tokens | Turn 121 estimated tokens |
|---|---:|---:|
| L | 15,079 | 15,448 |
| S | 5,233 | 5,408 |

The lower context cost did not preserve accuracy: S used roughly one third of
L's prompt tokens at the breadth probes and trailed by 1.5 points overall.

## Digest

The topic digest failed G1. At registered `d = 2`, `B_digest = 2,500`, its
2,332-character frame contained no complete rubric-critical fact in any
domain. Calibration through `d = 50`, `B_digest = 50,000` never reached 4/4.
The registered contingency dropped S+D before the live run.

Digest Bars 1 and 2 are therefore **NOT EVALUABLE**, and the digest is not
carried to Study 010.

## Integrity

| Check | Result |
|---|---|
| G2 accepted Arm L byte fidelity | PASS |
| G3 Arm S N + K fixture/import closure | PASS |
| Arm S 121-turn completion | PASS |
| Arm S forbidden modules loaded | PASS (zero) |
| Arm S fresh-lifecycle determinism | PASS (35/35 prompts and responses byte-identical) |
| Blinded scores committed before mapping/log analysis | PASS (`f41d133` then `0e676d2`) |
| Leakage audit | PASS |
| Digest Bars 1-2 | NOT EVALUABLE |
| Protocol-integrity Bar 3 | PASS under Amendment 001 |

The study is PARTIAL under the original all-bars definition because the digest
bars are not evaluable. The primary S-versus-L null test is complete and
decisive.

## Amendment and Limitations

The original protocol stopped at ablation because it simultaneously required
structural absence of LTM in S and byte-identical S/L prompts. Amendment 001,
authorized before the full run and scoring, replaced that impossible parity
unit with same-script/runtime/shared-component parity plus within-arm
determinism. It also authorized reuse of the byte-verified Study 007 artifact
as L and blinded agent scoring. The original stop record remains in
`decisions/DECISION_protocol_stop_study009.md`.

This is one seed, one script, one model, one score pass, and one run per arm.
The 1.5-point threshold makes the outcome binding for this program, not a
population estimate. Arm L is also a preserved earlier run rather than a
concurrent rerun, with fidelity established by G2.

## Study 010 Inputs

- `digest carry = false`
- `LTM configuration = accepted Study 007 treatment`
- `Study 009 null-test verdict = LTM value at 120 turns; S trails L by 1.5`
- `scale question = still open at 1,000 turns`
