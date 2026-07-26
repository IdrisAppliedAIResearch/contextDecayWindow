# Decision: Stop Study 010 at G2 Consolidation-at-Scale

**Status:** BINDING PRE-LIVE STOP
**Initial artifact lock:** `52f05e7`
**Final script SHA-256 (decoded, LF-normalized):**
`2d186e1b7f4c89d7095d01d7ac267d981abb0996c60c922a35f78cf2c6d38521`

## Passed Gates

- G1 passed. All 12 terminal targeted queries recovered their domain's early
  and middle plant source turns. Peak synthetic K context was 7,696 estimated
  tokens; mean/max scan latency was 52.25/58.60 ms over 986 episodes.
- G3 was not applicable because digest carry is false.
- G4 checkpoint/restore passed.
- The structural leakage scan passed.

## Binding Failure

G2 requires the accepted TopicManager to recover approximately 12 coherent
domains without mass cross-domain merging or fragmentation. It cannot do so.

The original generic filler script collapsed to two mixed topics at the
carried 0.45/0.45 thresholds. Amendment 002 replaced repeated generic filler
with domain-specific, non-scored facets and explicit thread boundaries. No
plant, probe, rubric, or arm policy changed.

| Assignment | Merge | Topics | Mixed topics |
|---:|---:|---:|---:|
| 0.45 | 0.45 | 2 | 2 |
| 0.50 | 0.75 | 6 | 4 |
| 0.55 | 0.75 | 14 | 8 |
| 0.60 | 0.75 | 20 | 4 |
| 0.65 | 0.80 | 43 | 7 |
| 0.70 | 0.85 | 83 | 4 |
| 0.75 | 0.90 | 122 | 3 |
| 0.80 | 0.95 | 135 | 1 |

No pair is near the registered 10-18-topic range with zero mixed topics.
Lower thresholds merge unrelated domains; higher thresholds fragment each
domain into prompt/facet clusters.

## Decision

Study 010 stops before the 200-turn rehearsal and live 1,000-turn runs. G2 is
a registered scale-shift gate and permits threshold recalibration, not
replacement of TopicManager. Adding supervised domain IDs, adaptive
thresholds, or a new clustering algorithm would change the accepted
architecture and invalidate the confirmatory scale contrast.

No live inference response, blinded score, fact matrix, degradation curve, or
Bar 1 verdict is produced. Bars 1-3 are not evaluable. A future construction
study must first pass this frozen replay.
