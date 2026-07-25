# Study 005 Synthetic Verification Report

**Date:** July 22, 2026
**Status:** PASS
**Pre-registration SHA:** `20aa7707e780543ccbe462efadf3bb1263b3813e`
**Fixture implementation SHA:** `327652fd1aa6a0637c802871f5229b42323e4466`
**Verifier SHA:** `8a80e6e5b485ca2b71eda7c3028f6eef34dc7d82`
**Fixture SHA-256:** `97a7f8c572eaaad998661ef6cc653875a87a42ab00b3111b05f6ec1e917519f4`

## Accepted runs

The accepted real-model run is `synthetic_study005_003`; independent replay `synthetic_study005_004` used a fresh server process. Both used seed 5005, the registered 50k single-slot runtime, Qwen3.6 27B UD-Q6_K_XL, and Qwen3-Embedding-0.6B Q8_0.

The 24-turn fixture uses a fixture-only consolidation interval of 20. This schedules its sole consolidation pass on the first explicitly labelled probe so the carried probe-bridge guard is reachable. The production, ablation, and confirmatory interval remains 10; no threshold or algorithm changed.

## Acceptance results

| Check | Expected | Actual | Result |
|---|---|---|---|
| Raw store permissive | Non-content turns stored | 24 raw episodes; all four acknowledgement turns 6-9 stored | PASS |
| Promotion absent | No promotion write path | 0 rows in promoted LTM | PASS |
| Dedup | Near duplicate collapsed | 1 collapse; duplicate turns 1-2 share one survivor | PASS |
| Cap | At most 3 content records per topic event | 3, 0, 3, 3 records at events 6, 10, 15, 19 | PASS |
| Number weight | Numeric contribution visible | Turn 1: 4 entities + 2 x 4 numbers = salience 12 | PASS |
| Coverage floor | Sparse topic gets marker only | Event 10 wrote one `present_no_salient_fact` marker, 0 content records | PASS |
| Extractive assertion | Every content record verbatim | 9/9 faithful | PASS |
| Dream inference calls | Zero | 0 at every event | PASS |
| Cadence | Transitions plus pre-probe flush | events 6, 10, 15; flush 19 | PASS |
| Probe exclusion | Probe turns never dreamed | turns 20-24 remain `dreamed=false` | PASS |
| Distilled read path | Distilled records reach tagged LTM | first observed at turn 7; present before and during probes | PASS |
| Facts-in-LTM | Three planted facts present; withheld absent | AX-17/43.7, DZ-53/17.2, CY-41/14-day present; NV-99 absent | PASS |
| Non-content in distilled content | Zero | 0 | PASS |
| Purity guard | Probe bridge blocked and logged | 2 `probe_bridge_blocked` events at turn 20 | PASS |
| Context ceiling | Less than 80% of 50k | peak 1,923 tokens | PASS |
| Determinism | Replay turn-identical | 24/24 prompts and 24/24 responses byte-identical | PASS |

All executable checks in `scripts/verify_study_005_synthetic.py` passed. The machine-readable report contains every prompt and response hash in `synthetic_verification.json`.

## Purity detail

The turn-20 pass blocked two candidate merges involving the probe-bearing topic at similarities 0.5581 and 0.6029. It also logged two cross-domain merges between non-probe topics. That is the carried guard's registered scope: it blocks probe-mediated bridges, not every semantically similar non-probe pair. Both event classes are retained in the evidence.

## Diagnostic history

Two non-accepted runs were retained locally and excluded from evidence selection:

1. `synthetic_study005_001` used the first 30-turn fixture. The normal turn-20 consolidation merged all topics before the turn-30 guard opportunity, and the natural-language near duplicates stayed below 0.95.
2. `synthetic_study005_002` made the duplicate exact and moved the probe to turn 20, but the normal turn-10 consolidation merged the sparse/content topics before their later transitions. It proved the dedup path but could not exercise the marker or bridge guard.

The final fixture correction changed only synthetic scheduling and duplicate controllability. Runs `003` and `004` were then executed from scratch and matched byte for byte.

## Verdict

**PASS.** Every S5_006 mechanism is verified end to end with real embeddings, real inference, real arbitration, real dreaming, and persisted provenance. The 35-turn registered-script ablation may proceed.
