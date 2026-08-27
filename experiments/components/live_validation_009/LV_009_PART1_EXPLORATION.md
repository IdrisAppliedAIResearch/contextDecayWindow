# LV-009 Part 1 Exploration

Date: 2026-08-27

Status: `PREFLIGHT_ELIGIBLE`

## Purpose

This label-blind exploration applies the frozen TC-014 opportunity pipeline
and LV-008 renderers to all raw LoCoMo QA occurrences before registration. It
does not inspect new reader answers, gold, evidence labels or prior correctness
outcomes and makes no answer-quality claim.

## Population and seals

- Corpus: 2,805,274 bytes; SHA-256
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- Raw rows: 1,986 across ten conversations.
- Categories 1-4: 1,540; category 5: 446.
- Category counts: 282, 321, 96, 841 and 446.
- Development/transfer primary rows: 692/848.
- Four-arm prompts: 7,944.
- Selection seal SHA-256:
  `35ab1fd17299163dfd11b1b6d84f583203982f9325e2e56bc38ed08129802315`.
- Prompt seal SHA-256:
  `98a0d0a3e00f78dfa222bd6d2cb6c49093dd7ae5f5f005b2a8de1412d14fc454`.
- A ten-process conversation-sharded rebuild reproduced both gzip seals
  byte-for-byte. The first serial pass took about 40 minutes; the parallel
  rebuild took about four minutes.

The two protected vector caches supplied every required pair and question
vector with zero misses, zero embedding calls and zero generative calls.

## Reproduction

All 871 overlapping TC-014 development selections reproduced by selected-id
order and payload digest. All 51 LV-008 prompt strings reproduced byte-for-byte.
Every arm contains the same selected identity set, emits each compact episode
element once, and preserves its bytes.

## Mechanism identity

Part 1 found a binding name-to-behavior mismatch in the carried community
renderer. LV-008's `cosine` term normalizes embedding rows but then indexes
selected episode indices into embedding-coordinate columns. It is not pairwise
episode cosine. A mathematically corrected implementation failed the first
LV-008 prompt reproduction and drove groups toward the cap-eight state. LV-009
carries the exact implemented coordinate lookup and the draft now names it.

All 1,540 primary rows contain at least two communities, so `COMMUNITY_QEACH`
differs from `COMMUNITY_QB` on 100% of the primary population. The registered
half-population treatment floor is reachable.

## Prompt and runtime distribution

The direct llama.cpp server used binary SHA-256
`125e0938a280cba46c803a60178e51826203e030abacce03367a22108720f7ac`
with the frozen Qwen3.8 27B UD-Q4_K_XL source. It ran one 65,536-token slot,
Q8 K/V cache, flash attention and no context shift. `/props` reported
`speculative.types=none`; MTP and the vision projector were absent.

Across 7,944 prompts, characters were min/median/p95/max
33,011/34,758.5/43,582/46,618. Evaluated tokens were
8,231/9,364/11,964/13,420. Every prompt plus the 8,192 output allowance remains
below 65,536. A 32-client tokenizer audit completed in 9.508 seconds.

Three label-blind 8,192-token reader probes covered the maximum-token prompt,
maximum-community T3 prompt and LV-008's prior capped reader surface. They
stopped naturally after 6, 8 and 2 tokens with nonempty outputs. The seven
previously capped LV-008 judge surfaces all stopped naturally after 28-49
tokens and all seven parsed under the frozen verdict parser at a 4,096 ceiling.

## Degenerate and absorbing states

Real rows include singleton and multi-item communities, cap-bound groups,
join/new decisions and order changes. The carried coordinate-index affinity is
itself a residual: it can reproduce LV-008 while failing the ordinary meaning
of cosine. Exact prompt reproduction prevents silently replacing it here.

`COMMUNITY_QEACH` has no one-group primary rows on this population, although
the renderer mechanically preserves T2 byte identity for a synthetic one-group
row. Repeated questions can still alter verbosity without improving
correctness. Context safety, compactness and prompt identity remain availability
surrogates; only the complete reader and blind-judge schedule can yield a
verdict.

## Consequence

The label-blind population, mechanism transfer, renderer treatment population,
context ceiling and prior cap risks are viable. LV-009 may now be locked and
implemented. Registration must carry the exact coordinate-index behavior and
the direct llama.cpp runtime recorded here; it must not restore pairwise cosine
under the old name.
