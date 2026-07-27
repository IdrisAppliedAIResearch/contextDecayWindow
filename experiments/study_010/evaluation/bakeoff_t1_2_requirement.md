# Forward Bakeoff Requirement T1.2: Breadth Beyond A Compact Store

**Status:** forward design requirement derived from post-score Study 010
analysis. This is not a new Study 010 result and does not amend a locked future
registration.

## Risk

Study 010's first 12-domain breadth success occurred under two conditions that
may make coverage unusually easy:

1. the failed TopicManager exposed only two merged topics, so the registered
   floor selected only two records and did not enforce 12-domain coverage; and
2. the distilled store remained compact relative to the fixed retrieval
   budget, while episode-mode rendering filled that budget almost completely.

The exact final store contains 290 distilled records totaling 18,951 text
characters, with mean 65.35 and median 55 characters. This corrects the rough
43k estimate based on 150 characters per record.

Compact raw text did not mean a small rendered prompt. Episode-mode rendering
expanded selected records to their source episodes:

| Probe | Budget | Rendered LTM chars | Utilization | Records used | Floor records |
|---|---:|---:|---:|---:|---:|
| Q13, turn 999 | 32,000 | 31,991 | 99.97% | 80 | 2 |
| Q14, turn 1000 | 32,000 | 31,847 | 99.52% | 81 | 2 |

L delivered all 12 breadth pairs, but the evidence cannot distinguish a robust
allocation policy from favorable ranking over a still-small candidate store.
At ten times the observed formation volume, raw distilled text alone projects
to about 189,510 characters, 5.9 times the fixed budget, before source-episode
rendering overhead. Coverage would no longer be cheap.

Study 008's offline gates found no count-cap configuration from 1 through 50
that jointly passed breadth and targeted retrieval on its preserved store.
That result increases the prior risk that Study 010's breadth win is a
small-store regime rather than a scalable policy.

## T1.2 Test

**Question:** Does breadth remain above the locked threshold when the eligible
rendered distilled store substantially exceeds `B_ltm`, or does Study 010's
coverage disappear once selection becomes strongly competitive?

Run a sealed offline bakeoff over fixed `B_ltm = 32,000` at minimum rendered
candidate-store ratios of approximately `1x`, `2x`, `5x`, and `10x` budget.
The scale tiers must preserve:

- at least 12 measurement-labeled domains;
- the observed record-length and source-episode rendering distributions;
- early, middle, and late critical facts per domain;
- narrow targeted and all-domain breadth queries; and
- the carried containment dedup and refill behavior.

The mechanism may not read rubric or plant-key labels. Domain labels are used
only by the evaluation harness after selection.

## Required Outputs

For every policy and scale tier, report:

- eligible raw-record and rendered-candidate characters;
- selected characters and budget utilization;
- selected records and unique source episodes;
- domain count and characters per domain after dedup/refill;
- breadth fact delivery and targeted fact delivery;
- floor versus fill contribution;
- containment drops, refills, and duplicate characters; and
- whether the policy passes both breadth and targeted criteria jointly.

## Decision Rule

T1.2 passes only if a single pre-committed policy, without scale-specific
tuning, preserves the registered breadth threshold and does not regress
targeted delivery at every tier through at least `5x` budget. A result that
passes only near `1x`, or requires a different cap/floor at larger tiers,
classifies Study 010's breadth success as compact-store dependent.

The `10x` tier is the endurance stress result. Failure there does not erase a
`5x` pass, but it defines the next scaling boundary explicitly.
