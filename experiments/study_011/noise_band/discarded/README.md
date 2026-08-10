# Discarded, not deleted

Two **complete, valid 121-turn Arm D runs** live here. Neither is part of the
five-replicate band and neither was ever scored.

| | Run | Status | Server PID | Why it is here |
|---|---|---|---:|---|
| `attempt_1/` | `study_011_noise_band_d_01` | COMPLETE, 121 turns, completeness PASS | 13088-era driver, torn down | driver crashed *after* the run, decoding the child's output in the Windows console codepage |
| `attempt_2/` | `study_011_noise_band_d_01` | COMPLETE, 121 turns | 11876 | driver crashed *after* the run, encoding that same output back out to a redirected stream |

## Why complete runs were set aside

§4.1 replicates the deployed configuration, and Study 011's four arms all ran back to
back in **one** server process (PID 13088). Carrying either of these forward would have
put one replicate in its own process and the other four in another, mixing
across-process variation into a band that is meant to measure run-to-run variation
under identical conditions.

Phase 1 makes that worse rather than better. The single recorded divergence in the whole
record came from a long-lived server process; 820 generations across fresh and warm
processes reproduced exactly. Process identity is therefore the variable most under
suspicion and the last one to smuggle into this measurement.

## Why this is not data selection

- **Nothing here was scored.** No packet was built, no rater ran, no total exists for
  either run.
- **No score was seen before the decision.** The decision is about which process a run
  sat in, which is visible in a manifest and has nothing to do with how it scored.
- **The ground was stated first.** "One server process for all five" is in the driver's
  docstring, committed at `9c451eb9`, before the first replicate ran.
- **Both runs are preserved**, so the decision is auditable rather than asserted.

## The bug, and why it took two goes

The first fix named UTF-8 for decoding the child's output. That was the correct fix for
the first failure and did nothing about the second: the parent still had to *write*
those characters to a stdout redirected to a file in the console codepage. Both failures
were the same mistake — moving text across a boundary without controlling the codec —
and the patch only addressed one direction of it.

The driver now writes the child's output straight to a UTF-8 file and never routes it
through its own stdout. A pipe the text does not cross cannot fail that way.
