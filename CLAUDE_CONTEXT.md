# contextDecayWindow Research Context

## Current state

Study 003 is complete with a PARTIAL result. The accepted run is `experiments/study_003/runs/study_003_full_002/iterative`. It scored 12.0/13.0 and passed 2 of 3 pre-registered bars. The pre-registration commit is `4c9003176d0130540ae1f257d5140c9daa919415`.

## Architecture after Study 003

- Iterative STM retrieval with soft N cap and K similarity retrieval
- User-message embeddings for topic assignment and centroids
- Topic assignment and consolidation thresholds at 0.45
- Consolidation every 10 episodes with propagation into the in-memory topic mapping
- Pinned rule store with model metadata detection and a conservative explicit-rule fallback
- Write-only STM-to-LTM promotion using novelty, repetition, association, and emotional-valence filters
- Promotion at canonical topic transitions through turn 111, with a three-episode outgoing residence minimum
- LTM episode IDs unique and promotion idempotent

## Study 003 result

- Rubric: Cat 1 3/3, Cat 2 3/3, Cat 3 2/2, Cat 4 2/3, Cat 5 2/2; overall 12/13
- Failed item: Q11 full enumeration omitted Renaissance art and monetary policy
- Topics: 1 at turn 120; passing count bar with a documented final over-merge
- LTM: 90 evaluated, 21 promoted, 23.33% promotion rate, 17.50% STM-to-LTM store ratio
- Routes: 12 weighted-threshold and 9 all-or-nothing promotions
- All-or-nothing filters: novelty 7, repetition 2
- Transition events: exactly turns 31, 61, and 91
- Accepted runtime: Qwen3.6 27B NVFP4, local llama.cpp server, 262,144-token context

## Study 004 — Planned

New component: LTM retrieval read path. Fixes from Study 003: broad-query domain coverage, STM/LTM deduplication, topic purity measurement, final-topic promotion, and positive merge-relabel guard coverage. Pre-registration not yet committed.

## Key files

- Final report: `experiments/study_003/study_003_report.md`
- LTM analysis: `experiments/study_003/runs/study_003_full_002/iterative/ltm_analysis/analysis_report.md`
- Rubric scores: `experiments/study_003/runs/study_003_full_002/iterative/rubric/scores.md`
- Consolidation decision: `experiments/study_003/decisions/DECISION_consolidation_threshold_study003.md`

**Last updated:** July 19, 2026
