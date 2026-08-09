# Discarded, not deleted

`study_011_noise_band_d_01` here is a **complete, valid 121-turn Arm D run**. It is
not part of the five-replicate band and was never scored.

**Why it was set aside.** The Phase 2 driver crashed after this replicate finished,
decoding the child process's output in the Windows console codepage rather than
UTF-8. The run itself succeeded — `status: COMPLETE`, 121 turns, completeness PASS —
but the server process it ran in was torn down with the driver.

§4.1 replicates the deployed configuration, and Study 011's four arms all ran back to
back in **one** server process (PID 13088). Carrying this replicate forward would have
put one of the five in its own process and the other four in another, mixing
across-process variation into a band that is supposed to measure run-to-run variation
under identical conditions. Phase 1 makes that worse rather than better: the one
recorded divergence in the whole record came from a long-lived server process, so
process identity is the variable most under suspicion and the last one to smuggle in.

**It is preserved rather than deleted** so the decision is auditable. Nothing here was
scored, no score was seen before the decision, and the ground — one process for all
five — was stated in the driver's docstring before the first replicate ran.

The harness bug is fixed in `scripts/run_amendment_001_phase_2_runs.py`.
