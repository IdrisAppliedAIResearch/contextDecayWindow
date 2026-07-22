# Study 005 Seeded Promotion Control Plan

Status: locked for execution after the committed Study 005 ablation GO decision in
commit `35dcfb6`.

## Control implementation

- Accepted Study 004 base: `994a490155bcb32a388222abfa3b8f2946d62fe4`
- Seeded control adapter: `a8a29aa65e55088a9dbf273deec482df9bb6c4dc`
- Control worktree: `C:\Users\muzaf\PycharmProjects\contextDecayWindow-study005-v4-control`
- Architecture: the accepted Study 004 promotion and retrieval implementation,
  executed as an actual v4 control rather than through a Study 005 feature flag.

The adapter differs from the accepted Study 004 base in exactly these files:

1. `scripts/run_study_005_seeded_v4_control.py`
2. `src/db/rule_store.py`
3. `tests/test_rule_store.py`

The rule-store change replaces random model-visible rule identifiers with stable
UUIDv5 identifiers. This is nonsemantic instrumentation needed to preserve the
locked same-seed prefix comparison. The launcher adds provenance and strict
context/capped-response monitors without changing prompts or responses.

## Locked execution settings

- Seed: `5005`
- Study script SHA-256:
  `d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01`
- Output: `experiments/study_005/controls/promotion_seeded/promotion_seeded_001/condition_c`
- Model: `Qwen3.6-27B-UD-Q6_K_XL.gguf`
- Context: 50,000 tokens, parallel 1, KV cache Q8_0, flash attention on
- Sampling: temperature 1, top-p 0.95, top-k 20, min-p 0, presence penalty 0,
  repeat penalty 1, server seed 5005
- Response budget: 2,048 tokens
- Speculative decoding: disabled

The launcher must reject a dirty control worktree, an unexpected adapter diff,
an unexpected Study 005 script hash, or any imported Study 005 dream engine.
It records the complete command, process ID, server properties, commits, and
resolved module paths before the first inference call.

## Evaluation order

1. Complete the seeded Study 004 control.
2. Complete the full Study 005 treatment on a fresh identical server.
3. Verify the locked same-seed prefix and basic run completeness.
4. Score both rubric response files and commit both score sets plus the two
   preregistered pre-scoring structural checks.
5. Only then open treatment dream/arbitration logs and evaluate the remaining
   preregistered bars and mechanism analyses.
