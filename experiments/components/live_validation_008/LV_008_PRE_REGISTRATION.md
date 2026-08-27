# LV-008 — Qwen3.8 compact-community reader replication

**Type:** registered fixed-prompt live reader replication  
**Status:** pre-registered; not yet runnable  
**Date:** 2026-08-26  
**Authorization:** program owner directed continuation after launching the Qwen3.8 reader

## 1. Question and claim boundary

On the exact three frozen LV-007 prompt arms, does compact semantic-community
organization improve live answer correctness over pairwise parent-child
organization under the Qwen3.8 27B Q4 reader, and does repeating the question
before memory add an independent signal?

LV-007 stopped before judging and has no result. LV-008 regenerates the complete
schedule under one reader and one larger common output ceiling. It is a LoCoMo
development rendering probe. It changes no retrieval, selection, evidence
identity, episode bytes, grouping, ordering, prompt wording or evidence
allowance. It cannot establish an overall benchmark score, transfer, reader
generality, deployment fitness, an optimal renderer or production adoption.

## 2. Frozen inputs and population

- Corrected Part 1 commit `4a5e9340`; document SHA-256
  `31209fc4fc0dd89332c9dd681c628270076f837c2a2d7194664e3684c81ecddc`.
- Part 1 artifact SHA-256
  `6092121c1459be2516f3e7a2fde1557541c00d93c7fce199e65ef4def65e77e1`.
- Part 1 script SHA-256
  `1a947cfe58519e64a142f7ba622cc405d6b87e45b3cf0ebe5239518236b86e6a`.
- LV-007 frozen prompt seal SHA-256
  `dc40d134e0e281fd0a064371620ce2a9a99f8f4a39855d3f32072ca9a844e9d9`.
- LV-007 stop record SHA-256
  `d1497d7aadc47f6f4afb67361d5f3face895dc6d07142dffefbfbb9412b74957`.
- LV-007 reader-identity erratum records that its `qwen35` architecture label
  was incorrectly reported as Qwen3.5. LV-008 makes no comparison to LV-007
  answers.
- Same 17 questions: 16 answerable primary items and one category-5 refusal
  secondary. Primary strata are 9 targeted, 5 breadth and 2 other.
- Each prompt contains the exact TC-014 opportunity selection for its row: 1,686
  episode occurrences, 1,069 semantic and 617 spread.

Stable comparison keys are canonical question and episode-content hashes.
Generated ids, file paths and timestamps are forbidden as mechanism keys. Gold
answers, required-evidence identities and all prior reader outcomes are
forbidden until the complete new answer schedule is sealed.

## 3. Frozen arms

The 51 prompt strings are read directly from the LV-007 prompt seal; LV-008 does
not rebuild or reinterpret them.

### C0 `PAIRWISE`

Exact LV-007 `PAIRWISE`: LV-005's full pairwise parent-child renderer, standard
HH-001 reader template and question at the bottom.

### T1 `COMMUNITY`

Exact LV-007 `COMMUNITY`: the frozen `.8*cosine + .2*facet_ochiai`, threshold
`.04`, maximum-eight semantic communities rendered with compact `<g>` wrappers,
creation-order groups, chronological items and question at the bottom.

### T2 `COMMUNITY_QB`

Exact LV-007 `COMMUNITY_QB`: T1's identical memory block with the exact question
also printed before memory. Only question placement differs from T1.

Every arm preserves each selected compact episode element byte-for-byte and
exactly once. Every prompt ends in the same frozen closed-think suffix.

## 4. Reader runtime and schedule

- Ollama `0.33.0`, `http://127.0.0.1:11434/api/generate`.
- Model alias `lv008-qwen38-q4:latest`, manifest SHA-256
  `281d02f0ad1a4b4928fcf1450e6bd1bb88e0d57c0051df03a993265ec6662adc`.
- Source `Qwen3.8-27B-UD-Q4_K_XL.gguf`, SHA-256
  `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372`,
  17,923,394,624 bytes. Ollama reports 27.3B, Q4_K_S runtime metadata.
- `num_ctx=65536`; all 21,558,366,042 runtime bytes must remain GPU-resident on
  the NVIDIA GeForce RTX 5090 before and after generation.
- Raw prompt mode, thinking disabled, streaming disabled, no speculative
  decoding, `num_predict=4096`, temperature `.6`, top-p `.95`, top-k `20`,
  min-p `0`, repeat penalty `1.0`.
- Five reader replicates per item and arm; seeds `5005` through `5009`.
- Arm order per item-replicate is ascending SHA-256 order of
  `comparison_key || replicate || arm` under domain `lv008-order-v1`.
- One request at a time and `keep_alive=30m`. Append, flush and fsync every
  response before the next request. Preserve a mechanical transport failure;
  one retry is allowed and qualifies the result.

There are 255 entirely new reader answers. Any answer ending by length stops
LV-008 before judging. All evaluated prompt counts must remain below 65,536.
The 4,096 ceiling is common to all arms and is only a validity safeguard; Part
1's formerly capped prompt naturally stopped at 12 tokens under both ceilings.

## 5. Blind scoring

All 255 answers are committed before blind scoring. The 240 primary answers are
hidden behind content-derived blind ids under domain `lv008-blind-v1`. The judge
sees only question, gold and answer. Use the frozen HH-001 rubric and LV-006
parse repair: append the closed-think suffix and then `VERDICT:` with no
intervening text.

Use the same registered Qwen3.8 alias, seeds `9005`–`9007`, temperature `.2`,
top-p `.9`, top-k `20`, min-p `0`, repeat penalty `1.0`, and
`num_predict=128`. Majority of three judge passes gives the answer verdict;
majority of five reader answers gives the item-arm verdict. Exactly 720
parseable, naturally stopped judgments are required before opening the mapping.
Normalized gold containment is a secondary direction cross-check. The
category-5 item is scored only for exact refusal.

## 6. Comparisons and dispositions

Register three comparisons:

1. `COMMUNITY_vs_PAIRWISE` — compact communities versus full pairwise rendering.
2. `QUESTION_REPEAT_INCREMENT` — T2 versus T1, isolating question placement.
3. `FULL_vs_PAIRWISE` — T2 versus C0, the combined renderer.

For each, report semantic gains, losses, ties, net and descriptive exact
two-sided McNemar p for combined, targeted, breadth and other strata. Report
containment direction, vote margins, refusal, truncation, prompt tokens, block
characters and structural overhead. Apply independently:

- **`PROMISING`:** combined net at least `+3`, targeted and breadth nets
  nonnegative, and no opposite nonzero containment sign.
- **`WEAK_SIGNAL`:** combined net `+1` or `+2`, targeted and breadth nets
  nonnegative, and no sign reversal.
- **`NO_SIGNAL`:** combined net zero, targeted and breadth nets nonnegative, and
  no sign reversal.
- **`REGRESSES`:** combined net negative or targeted or breadth net negative.
- **`NOT_INTERPRETABLE`:** any validity gate fails or semantic and containment
  have opposite nonzero signs.

The bar is carried unchanged from LV-005/LV-007. There is no best-arm selection,
parameter tuning, post-result prompt revision, rerun after a valid score,
deployment change or winner claim.

## 7. Preflight — binding before treatment generation

- **PF1 inputs:** hash and count this registration, corrected Part 1, LV-007
  prompt seal and stop, corpus/blind manifest, TC-014 selections, Qwen3.8 source
  file and Ollama manifest, model process and GPU residency.
- **PF2 mechanism identity:** reproduce all 51 frozen prompt strings and their
  per-arm digests. Verify names against behavior: PAIRWISE is pairwise grouped,
  COMMUNITY uses the frozen semantic groups, and COMMUNITY_QB differs from
  COMMUNITY only by the one top-question insertion.
- **PF3 gate ordering:** registration commit precedes implementation; prompts
  seal before answers; answers commit before blind surface; judgments commit
  before mapping access. Mechanically reject early gold or mapping access.
- **PF4 reachability:** synthetic rows reach every disposition and sign guard.
  Real prompts include all 17 rows per arm; Part 1 proves a natural 4,096 stop.
  The output-cap stop remains reachable by a deterministic synthetic max-token
  call and is a validity failure, not evidence about rendering.
- **PF5 stable keys:** content hashes only. Reject duplicate questions,
  identities and schedule keys, missing rows, arms, prompts or gold after the
  answer seal.
- **PF6 reproduction:** reproduce the LV-007 51-prompt seal byte-for-byte and
  digest-for-digest. Repeat Part 1's exact Qwen3.8 prompt and seed byte-identically
  with 12 output tokens and its registered response hash.
- **PF7 absorbing-state/runtime:** demonstrate the cap stop before any scheduled
  answer; repeat one real T2 prompt at seed 5005 byte-identically, nonempty and
  naturally stopped; require 100% model GPU residency before and after. The
  reader has no cross-request feedback state beyond prompt caching.
- **PF8 adequacy:** five replicates expose reader instability and 16 selected
  items can detect a large conversion on known failures. They cannot estimate
  overall accuracy, small effects, transfer, production behavior or an optimal
  renderer.
- **PF9 surrogate audit:** compactness can improve without correctness;
  question repetition can change verbosity; exact evidence preservation can
  coexist with reader failure; judge majorities can share bias. Exact frozen
  prompts and live blind scoring mitigate but do not eliminate these residuals.
- **PF10 live requirement:** this is a live reader probe. Prompt size,
  determinism, containment and evidence availability are not verdicts.

Additional gates:

- **G-PROMPTS:** all 51 strings and digests exactly match the LV-007 seal.
- **G-COMPLETE:** exactly five naturally stopped answers per item-arm and three
  parseable, naturally stopped judgments per primary answer.
- **G-CONTEXT:** every reader and judge prompt evaluates below 65,536 tokens.
- **G-GPU:** the exact registered alias remains 100% GPU-resident throughout.
- **G-REFUSAL:** report but do not use the category-5 refusal as an adoption bar.

No required-evidence labels may enter any prompt mechanism. No new embedding,
parser, grouping, summary or retrieval operation is permitted.
