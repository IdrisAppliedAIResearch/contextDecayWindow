# contextDecayWindow Research Context

## Current state

Study 005 is complete with a PARTIAL result. The accepted treatment is
`experiments/study_005/runs/study_005_full_001/condition_c`; the seeded
promotion control is
`experiments/study_005/controls/promotion_seeded/promotion_seeded_001/condition_c`.
Treatment scored 11.0/13.0 with Q14 = 0.5; control scored 12.0/13.0 with
Q14 = 0.0. Bar 1 failed, Bar 2 was not evaluable, and Bar 3 failed. The
pre-registration lock is `20aa7707e780543ccbe462efadf3bb1263b3813e`, and the
score/structural lock is `1bbfad7`.

## Architecture after Study 005

- Iterative STM retrieval with soft N cap and K similarity retrieval
- User-message embeddings for topic assignment and centroids
- Topic consolidation at 0.45 every 10 episodes, with a probe-bridge guard
- Pinned rule store with deterministic UUIDv5 model-visible rule identifiers
- Permissive append-only raw conversation store; every user/assistant turn is
  retained and marked for dreaming
- Extractive dreaming at topic transitions and the turn-111 flush
- Salience `named_entities + 2 * numeric_tokens`, cosine dedup at 0.95,
  per-topic cap 3, and salience floor 2
- Verbatim distilled records with source IDs/turns, salience, event, and
  collapsed-source provenance
- Asynchronous STM/distilled-LTM retrieval, tier-neutral arbitration,
  episode-ID deduplication, and XML-tagged context tiers
- Fixed seed 5005, single-slot llama.cpp serving, deterministic IDs, and no
  speculative decoding
- Formation, faithfulness, non-content, conditional breadth, and comparative
  non-regression evaluators

## Study 004 result

- V4 scored 7.0/13.0 and Q14 0.0; same-settings v3 control scored 11.0/13.0
- Active LTM contributed on every eligible turn but promotion omitted all
  later-domain rubric plants
- Consolidation purity passed with five final topics and no cross-domain merges
- Binding failure was selective promotion, which motivated Study 005 dreaming

## Study 005 result

- Both arms completed 121 turns on Qwen3.6 27B UD-Q6_K_XL at 50k context,
  2,048 response tokens, and seed 5005
- Same-seed prefix: 30/30 prompts and 30/30 responses byte-identical
- Treatment rubric: Cat 1 3.0, Cat 2 2.5, Cat 3 1.5, Cat 4 2.0, Cat 5 2.0;
  total 11.0/13.0; Q14 0.5
- Control rubric: Cat 1 3.0, Cat 2 3.0, Cat 3 2.0, Cat 4 2.0, Cat 5 2.0;
  total 12.0/13.0; Q14 0.0
- Dreaming wrote 12 content records from turns 4/17/20, 31/40/41,
  61/69/84, and 92/105/108
- Faithfulness was 12/12; non-content, marker, inference-call, and dedup counts
  were all zero
- Locked formation coverage was 2/4 domains: civil and monetary present; art
  and marine absent
- Art plant ranks were 18, 28, and 19; marine plant ranks were 11, 16, and 17
  under the top-three policy
- Q11 and Q14 each received five distilled records, but Bar 2 was not evaluable
  because the store-content precondition failed
- Final topics: 5; no cross-domain purity event; full-run bridge guard not
  exercised
- Active LTM retrieval remains mechanically sound but not functionally
  validated

## Next research target

- Keep dreaming extractive and change selection granularity from whole
  conversation episodes to atomic factual source spans
- Separate or weight user-provided facts against generated answer text, and
  test length-normalized factual salience
- Add an adversarial synthetic fixture where verbose numeric answers compete
  with concise planted facts
- Preserve fixed-seed, single-slot, deterministic-ID, score-before-log protocol
- Do not build retrieval diversity yet; its registered trigger requires
  successful formation followed by breadth failure
- Defer abstractive dreaming until extractive selection passes, since
  abstraction would introduce a new faithfulness problem prematurely

## Key files

- Study 005 final report: `experiments/study_005/study_005_report.md`
- Machine-readable results:
  `experiments/study_005/evaluation/study_005_results.json`
- Score and structural lock: `experiments/study_005/evaluation/score_lock.md`
- Treatment mechanism analysis:
  `experiments/study_005/runs/study_005_full_001/condition_c/ltm_analysis/analysis_report.md`
- Treatment scores:
  `experiments/study_005/runs/study_005_full_001/condition_c/rubric/scores.md`
- Seeded control scores:
  `experiments/study_005/controls/promotion_seeded/promotion_seeded_001/condition_c/rubric/scores.md`
- Runtime verification:
  `experiments/study_005/runtime/s5_001_runtime_verification.md`
- Synthetic verification:
  `experiments/study_005/tests/synthetic_verification_report.md`
- Ablation report: `experiments/study_005/ablation/ablation_report.md`

**Last updated:** July 22, 2026
