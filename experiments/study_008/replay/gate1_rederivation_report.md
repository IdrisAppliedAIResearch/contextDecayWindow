# Study 008 — Gate 1 Corrected Re-Derivation

**Task:** S8-T-005
**Input:** Study 007 accepted treatment store, read-only
**Plant-key SHA-256:** `9bb20255152370b0444af84e7b6d32268496ca872ee0eb596af60874f179fcfa`
**Verdict:** P1 CONFIRMED

## Locked-budget verdict

At `B_ltm = 32,000`, no swept `k_min` from 0 through 4 reaches genuine fact-aware four-domain coverage at both probes.

## Amendment 002 §6 retro-verdict

The floor-inertness claim is VOID under the corrected criterion: `k_min = 0` does not reach fact-aware four-domain coverage at both probes at 32,000 characters.

## Corrected frontier

| B_ltm | k_min | Q11 domains | Q14 domains | Four-domain both |
|---:|---:|---|---|---|
| 16000 | 0 | art, civil | art, marine, monetary | FAIL |
| 16000 | 1 | civil, monetary | art, marine, monetary | FAIL |
| 16000 | 2 | civil, monetary | art, marine, monetary | FAIL |
| 16000 | 3 | civil, monetary | art, marine, monetary | FAIL |
| 16000 | 4 | civil, monetary | art, marine, monetary | FAIL |
| 20000 | 0 | civil, monetary | civil, marine, monetary | FAIL |
| 20000 | 1 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 20000 | 2 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 20000 | 3 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 20000 | 4 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 24000 | 0 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 24000 | 1 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 24000 | 2 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 24000 | 3 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 24000 | 4 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 28000 | 0 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 28000 | 1 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 28000 | 2 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 28000 | 3 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 28000 | 4 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 32000 | 0 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 32000 | 1 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 32000 | 2 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 32000 | 3 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 32000 | 4 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 36000 | 0 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 36000 | 1 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 36000 | 2 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 36000 | 3 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 36000 | 4 | civil, marine, monetary | civil, marine, monetary | FAIL |
| 40000 | 0 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 40000 | 1 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 40000 | 2 | art, civil, marine, monetary | art, civil, marine, monetary | PASS |
| 40000 | 3 | art, civil, marine, monetary | art, civil, marine, monetary | PASS |
| 40000 | 4 | art, civil, marine, monetary | art, civil, marine, monetary | PASS |
| 48000 | 0 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 48000 | 1 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 48000 | 2 | art, civil, marine, monetary | art, civil, marine, monetary | PASS |
| 48000 | 3 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 48000 | 4 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 64000 | 0 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 64000 | 1 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 64000 | 2 | civil, marine, monetary | art, civil, marine, monetary | FAIL |
| 64000 | 3 | art, civil, marine, monetary | art, civil, marine, monetary | PASS |
| 64000 | 4 | art, civil, marine, monetary | art, civil, marine, monetary | PASS |

## Integrity

- Candidates replayed: 200
- Locked fact rows: 14
- Study 007 files hashed before and after: 271
- Study 007 artifacts unchanged: **True**

Full matched-fact and source-turn details are in
`gate1_rederivation.json`.
