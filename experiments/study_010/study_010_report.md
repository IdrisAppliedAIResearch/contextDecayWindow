# Study 010 Report: Endurance Study Stopped at Scale Gate

**Study 009 dependency merge:** `8520bfe`
**Initial artifact lock:** `52f05e7`
**Final status:** STOPPED AT G2 BEFORE LIVE INFERENCE

## Result

Study 010 reached its offline scale gates but did not reach rehearsal or the
two 1,000-turn live runs. The accepted topic-assignment/consolidation layer
cannot represent the locked 12-domain script without either mass merging or
fragmentation.

This is a binding feasibility result, not an STM-versus-LTM score. No Bar 1
verdict can be made.

## Repairs

Amendment 001 repaired the inherited protocol: Study 009 supplied its decisive
LTM-value verdict; digest carry resolved false; Arm L remained the accepted
Study 007 treatment; architecture-aware parity replaced impossible cross-arm
byte identity; and checkpoint/restore plus blinded agent scoring were defined.

The script/rubric/key triple then locked at 1,000 turns, 12 domains, 36 plants,
nine interim probes, and fourteen terminal probes.

The first G2 replay exposed a script defect: eight generic filler templates
were repeated across domains. Amendment 002 replaced only filler wording with
domain-specific, non-scored facets and explicit thread boundaries. Plants,
plant turns, probes, rubric, and architecture remained unchanged. Failed gate
attempts are preserved under `gates/attempt_001/` and `gates/attempt_002/`.

## Gate Results

| Gate | Result |
|---|---|
| G1 retrieval at scale | PASS |
| G2 consolidation at scale | **FAIL - binding STOP** |
| G3 digest at scale | NOT APPLICABLE |
| G4 checkpoint/restore | PASS |
| Leakage audit | PASS |
| G5 200-turn rehearsal | NOT RUN |

G1 scanned 986 synthetic episodes. Every terminal targeted query recovered its
domain's early and middle plant sources, peak projected K context was 7,696
tokens, and mean/max scan latency was 52.25/58.60 ms.

G2 swept eight assignment/merge threshold pairs. Topic counts ranged from 2
to 135; no pair produced 10-18 topics with zero mixed-domain topics. The
closest count was 14 topics at 0.55/0.75, but eight were mixed. Full results
are in `gates/gate_results.json`.

## Consequence

The rehearsal, live arms, blinded scoring, degradation curves, and Bars 1-3
are not evaluable. Running them would knowingly violate the pre-registered
scale gate.

The next study must be a topic-architecture construction study against this
frozen 1,000-turn replay. Candidate changes such as supervised boundary
signals, adaptive assignment, or a different clustering objective must be
registered as treatments rather than silently inserted into Study 010.
