# contextDecayWindow Research Context

## Current state

Study 004 is complete with a PARTIAL result. The accepted v4 run is `experiments/study_004/runs/study_004_full_002/condition_c`; the same-settings v3 control is `experiments/study_004/controls/v3_same_settings/v3_control_002/iterative`. V4 scored 7.0/13.0 with Q14 = 0.0 and passed 1 of 3 bars; the control scored 11.0/13.0 with Q14 = 0.0. The pre-registration commit is `1b9eb204e32b6b7cb32dfce4cb647cfc7f0e4d0f`, and Amendment A005 is locked at `9fbf4f9f95a1fad6205d56664db36b9911650d41`.

## Architecture after Study 004

- Iterative STM retrieval with soft N cap and K similarity retrieval
- User-message embeddings for topic assignment and centroids
- Topic assignment and consolidation thresholds at 0.45
- Consolidation every 10 episodes with propagation into the in-memory topic mapping
- Pinned rule store with model metadata detection and a conservative explicit-rule fallback
- STM-to-LTM promotion using novelty, repetition, per-topic association, and emotional-valence filters
- Promotion at canonical topic transitions plus a turn-111 final-domain flush, with a three-episode outgoing residence minimum
- LTM episode IDs unique and promotion idempotent
- Asynchronous STM/LTM retrieval, tier-neutral arbitration, episode-ID deduplication, and XML-tagged context tiers
- Ground-truth consolidation-purity logging and probe-topic bridge guards

## Study 003 result

- Rubric: Cat 1 3/3, Cat 2 3/3, Cat 3 2/2, Cat 4 2/3, Cat 5 2/2; overall 12/13
- Failed item: Q11 full enumeration omitted Renaissance art and monetary policy
- Topics: 1 at turn 120; passing count bar with a documented final over-merge
- LTM: 90 evaluated, 21 promoted, 23.33% promotion rate, 17.50% STM-to-LTM store ratio
- Routes: 12 weighted-threshold and 9 all-or-nothing promotions
- All-or-nothing filters: novelty 7, repetition 2
- Transition events: exactly turns 31, 61, and 91
- Accepted runtime: Qwen3.6 27B NVFP4, local llama.cpp server, 262,144-token context

## Study 004 result

- Same-settings v3 control: 11.0/13.0; Q14 0.0; breadth failed, so A005 permitted the fresh v4 run
- V4 rubric: Cat 1 3/3, Cat 2 0/3, Cat 3 1/2, Cat 4 1/3, Cat 5 2/2; overall 7/13; Q14 0.0
- Bars: breadth failed, targeted non-regression failed, consolidation purity passed; PARTIAL 1/3
- LTM contributed on 90/90 eligible turns with 450 placements, one deduplication, and zero STM-displacement events
- Final LTM: 12 episodes — nine early civil-engineering episodes and one generic art, monetary-policy, and marine-biology episode
- Promotion events: turns 31, 61, 91, and turn 111; five final topics and zero cross-domain merges
- Binding failure: promotion omitted every later-domain rubric plant, so active retrieval could not recover them
- The v4 bundle regressed against the control, but A005 bundles read path and XML tagging; causal attribution requires a tagged/read-off arm

## Next research target

- Improve memory formation with dream-cleaning/distillation, factual-salience selection, and per-domain diversity constraints
- Add a tagged/read-off control before attributing regression to retrieval versus context presentation
- Instrument context-construction latency and use deterministic or repeated generation seeds

## Key files

- Final report: `experiments/study_003/README.md`
- LTM analysis: `experiments/study_003/runs/run_001/ltm_analysis/analysis_report.md`
- Rubric scores: `experiments/study_003/runs/run_001/condition_c/rubric/scores.md`
- Consolidation decision: `experiments/study_003/decisions/DECISION_consolidation_threshold_study003.md`
- Study 004 final report: `experiments/study_004/study_004_report.md`
- Study 004 LTM/arbitration analysis: `experiments/study_004/runs/study_004_full_002/condition_c/ltm_analysis/analysis_report.md`
- Study 004 v4 scores: `experiments/study_004/runs/study_004_full_002/condition_c/rubric/scores.md`
- Study 004 v3 control scores: `experiments/study_004/controls/v3_same_settings/v3_control_002/iterative/rubric/scores.md`

**Last updated:** July 21, 2026
