# SUP-001 35-Turn Ablation Run Lock

**Locked:** 2026-08-11  
**Authorization:** SUP-001 offline disposition `SUPERSESSION_OFFLINE_ELIGIBLE`
at commit `125d65b1`.  
**Scope:** The conditional Section 7 reader ablation only. This is not a
120-turn or production authorization.

## Script

The committed mechanism script has exactly 35 user turns:

- turns 1-4: initial versions for four explicit memory keys;
- turns 5-8: four unchanged facts;
- turns 9-12: unrelated fillers;
- turns 13-16: first update wave;
- turns 17-20: unrelated fillers;
- turns 21-24: second update wave;
- turns 25-26: unrelated fillers;
- turns 27-30: four current-value probes;
- turns 31-34: four unchanged-value probes;
- turn 35: one deliberate three-version history probe.

Every answer-bearing fact is planted strictly before its probe. Encoding and
filler turns use the fixed assistant text `Recorded.` and make no generation
call. Probe answers are appended to the store after retrieval and decoding, so
later probes see the same causal conversation history within each arm.

The mechanism reads `ablation_script.json`. The runner and retrieval mechanism
must not read `SEALED_ABLATION_KEY.json`; only post-run scoring may open it.

## Runtime

- Reader: `Qwen3.6-27B-UD-Q6_K_XL.gguf`, SHA-256
  `f3b4a622e06e8ade06ec5c0eb9b40ed7c9bd707b5fada46c0215f4ab4a6bc32b`.
- Server: llama.cpp build `b9294-0f3cb3fc8`; binary SHA-256
  `3827a6b634a88073dc63b97edf6e0dc575d33ecf58268803ece0ed23216095fa`.
- Seed 5005, temperature 1, top-p 0.95, top-k 20, min-p 0, presence
  penalty 0, repeat penalty 1, one slot, no speculative decoding.
- Reader output cap: 128 tokens. Raw `/completion`, non-streaming,
  `reasoning_format=none`, with a closed think block prefill.
- Embeddings: carried Qwen3-Embedding-0.6B Q8_0, SHA-256
  `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`,
  normalized float32, one text per call, retained read-only cache.
- Retrieval: all prior stored episodes, cosine/hash order, top 8, exact carried
  renderer and skip-overflow packer, 32,000 characters.
- Prompt: the exact template in `ablation_script.json`; no transcript outside
  the retrieved payload is supplied.

## Arms

`C0` runs from a clean separate worktree at the control-only harness commit.
It has no supersession module, ledger, accessibility field, or treatment flag.

`T1` runs from a clean separate worktree at the later treatment commit. It
uses explicit registrations to exclude silent ancestors from natural reads;
the deliberate history probe alone bypasses accessibility.

Both arms use the same script, vectors, reader process, prompt template,
candidate count, top 8, and character ceiling.

## Gates

Before scored decoding:

1. Assert all artifact, source, model, server, script, and cache hashes.
2. Assert one server slot, seed 5005, speculative decoding `none`, and build.
3. Assert the worktree is clean and at its registered arm commit.
4. Assert all nine answer facts are planted before their probes.
5. Run the first two probe prompts twice per arm; outputs must be byte-identical.
6. Assert the runner source SHA again after every decoding sequence.

The ablation passes only if:

- T1 answers all four current and all four unchanged probes exactly;
- T1 returns the exact oldest-to-newest three-value history;
- no T1 current answer or natural payload contains a stale value;
- every C0-correct targeted probe is also correct in T1;
- both arms deliver exactly eight episodes per natural probe and every payload
  is at most 32,000 characters;
- T1 retains 12 lineage records, four accessible leaves, eight silent
  ancestors, reciprocal same-key acyclic links, all stored source identities,
  and pure reads.

Pass disposition: `READY_FOR_SEPARATE_LIVE_DECISION`. Failure disposition:
`ABLATION_INTEGRATION_STOP`. Neither disposition authorizes a 120-turn run.

