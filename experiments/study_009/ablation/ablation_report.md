# Study 009 Arm S Ablation Report

**Run:** `study_009_ablation_001`
**Arm:** S (structurally minimal N + K)
**Turns:** 35
**Registration anchor:** `37fff74`
**Implementation and gate commit:** `f901bda`
**Outcome:** Runtime checks pass; cross-arm prefix contract fails

## Runtime

| Check | Result |
|---|---:|
| Completed turns | 35 / 35 |
| Duration | 530.84 s |
| Minimum generation speed | 33.70 tok/s |
| Mean generation speed | 41.19 tok/s |
| Maximum generation speed | 46.37 tok/s |
| Peak estimated context | 9,960 tokens |
| 80% context ceiling | 40,000 tokens |
| Empty or budget-exhausted streak abort | none |

The live server reported the registered seed 5005, one slot, 50,176 context
tokens, Q8_0 K/V cache, flash attention, and no speculative decoding. The
post-decode script hash matched
`d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01`.

## Structural Arm S Checks

- Runtime import audit: no LTM, dreaming, promotion, or digest module loaded.
- All 35 constructed prompts omit `<retrieved_ltm>` and `<topic_digest>`.
- N, K, context-window, turn, rule, topic, and consolidation logs are populated.
- The carried structural leakage audit passes.
- No digest rebuild occurred at turn 31, as required after G1 dropped S+D.

## Prefix Audit

The pre-registration contains two requirements that cannot both hold:

1. Arm S must omit the LTM tier structurally, including an absent
   `<retrieved_ltm>` block.
2. Arms must be byte-identical through the empty-store prefix.

Compared with the preserved Study 007 35-turn ablation:

| Measure over turns 1-30 | Result |
|---|---:|
| Raw prompts byte-identical | 0 / 30 |
| First raw prompt difference | turn 1 |
| Prompts identical after deleting Study 007's empty `<retrieved_ltm/>` | 3 / 30 |
| First normalized prompt difference | turn 4 |
| Responses byte-identical | 2 / 30 |
| First response difference | turn 3 |

The empty LTM tag is the only structural prompt difference through turn 3.
That difference changes the seeded response at turn 3, after which stored
assistant text causes legitimate downstream state and prompt divergence.

## Verdict

The Arm S implementation and runtime are healthy, but the registered cross-arm
prefix equality condition fails by construction. The sprint contract says to
stop and flag on any divergence. A post-result normalization rule would be an
unregistered reinterpretation, and adding the empty LTM tag would violate G3
and the structural subtraction requirement.

**NO-GO.** No 121-turn run or scoring is authorized.
