# LV-007 — compact semantic-community rendering probe

**Type:** registered fixed-evidence live reader ablation  
**Status:** pre-registered; not yet runnable  
**Date:** 2026-08-26  
**Authorization:** program owner approved all three proposed organization arms

## 1. Question and claim boundary

On the exact frozen LV-005 selected evidence and reader population, does compact
content-based community organization improve reader correctness over the
pairwise parent-child renderer, and does repeating the question before memory
add an independent signal?

This is a LoCoMo development rendering probe. It changes no retrieval,
selection, evidence identity, episode content or evidence allowance. It cannot
establish an overall benchmark score, a deployable fixed-32k renderer, transfer,
an optimal clustering rule, reader-model generality or production adoption.

## 2. Frozen inputs and population

- Part 1 commit `c088056a`; artifact SHA-256
  `acd6a783a8ffd949b35ebe28788ea88a9b08de3c9b19ba7139da9547d815d78f`.
- Part 1 script SHA-256
  `1b68a34978f858a48299f948471642c9985672ee39a2ea706226157f6881f36f`.
- LV-005 prompt seal SHA-256
  `d0a3ac38e15c1738387c9d3216de532195959dd4c8ac7515a03209bbfebe8b80`.
- TC-014 selection SHA-256
  `32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7`.
- Frozen solo-vector cache file SHA-256
  `2ba617018a1b043bf439bb50e756191d8141fb7ca01a2e4a68c9eb822eba26f8`;
  content SHA-256
  `e103b2933ee9ec7b8e9236f43037797618da524e413b83a9f3973a19d28b1b2a`.
- LV-006 result SHA-256
  `011d0a3cf49d781f99a14327c3189b5260c1eec3e44e206ff84be8ce783f76ee`.
- Same 17 questions as LV-005/LV-006: 16 answerable primary items and one
  category-5 refusal secondary. Primary strata remain 9 targeted, 5 breadth and
  2 other.
- Each arm receives the exact TC-014 32k opportunity selected set for its row:
  1,686 episode occurrences across 17 rows, 1,069 semantic and 617 spread.

Stable comparison keys are canonical question and episode content hashes.
Generated ids, file paths and timestamps are forbidden as mechanism keys.
Gold answers, required-evidence identities and prior reader outcomes are
forbidden during prompt construction.

## 3. Arms

All arms preserve every selected compact `<episode turn="…">`, `<user>` and
`<assistant>` element byte-for-byte and exactly once. Every full prompt ends
with the frozen closed-think suffix used by LV-005.

### C0 `PAIRWISE`

The exact frozen LV-005 `TEMPORAL_GUIDANCE` prompt, including its parent-child
groups, temporal roles, organization note, standard HH-001 reader template and
single question at the bottom. All 17 prompt digests must reproduce the LV-005
seal. Answers are generated afresh under the common LV-007 schedule.

### T1 `COMMUNITY`

Construct a content affinity over the selected episodes:

`affinity(i,j) = .8 * cosine(i,j) + .2 * facet_ochiai(i,j)`.

Cosine uses the frozen float32 solo episode vectors normalized in float64.
`facet_ochiai(i,j)` is the TC-011 deterministic six-family facet overlap,
weighted by IDF calculated over every episode in that conversation, divided by
the square root of the two episodes' total IDF weights. A zero denominator maps
to zero. spaCy is locked to 3.8.14 and `en_core_web_sm`.

Visit selected identities in their frozen TC-014 order. For an identity, score
each open group below eight items by its mean affinity to all current members.
Assign it to the group with greatest mean when that mean is at least `.04`;
otherwise open a new group. Break an exact mean tie by the earlier-created
group. Group rank is creation order. Within each group, sort by numeric
conversation turn ascending and then content hash as an unreachable tie-break.

Render exactly:

```text
<recent_context/>

<retrieved_stm organization="semantic_communities">
<organization_note>Evidence is grouped by content. Groups are ordered by direct relevance. Items within a group are in conversation order.</organization_note>
<g rank="1">
<episode turn="…">
…
</episode>
</g>
…
</retrieved_stm>
```

`<g rank="r">`, `</g>` and each unchanged episode element occupy their own
lines. Rank is one-based decimal creation order. No item wrapper, route label,
topic name, summary, inferred entity, current-state label or supersession label
is printed. Use the unchanged HH-001 reader template, so the question appears
only in its normal bottom position.

### T2 `COMMUNITY_QB`

Use T1's exact block, groups and episode order. Change only the outer reader
template by inserting these two lines immediately after the existing first
line `You are answering a question about a conversation between two people.`:

```text

Question to answer: {exact question}
```

The rest of the HH-001 prompt is byte-identical to T1, including the normal
bottom `Question: {exact question}` and answer instruction. Thus the exact
question is presented once before memory and once after memory. No instruction
about enumeration, completeness, entities, locations or answer type is added.

## 4. Reader runtime and schedule

- Ollama `0.33.0`, `http://127.0.0.1:11434/api/generate`.
- Model `qwen-custom:latest`, manifest id `3516cd593f43`, Qwen 3.5 27.3B Q6_K,
  `num_ctx=65536`, fully resident on NVIDIA GeForce RTX 5090.
- Raw prompt mode, thinking disabled, streaming disabled, `num_predict=2048`,
  temperature `.6`, top-p `.95`, top-k `20`, min-p `0`, repeat penalty `1.0`.
- Five reader replicates per item and arm; seeds `5005` through `5009`.
- Arm order per item-replicate is ascending SHA-256 order of
  `comparison_key || replicate || arm` under domain `lv007-order-v1`.
- One request at a time and `keep_alive=30m`. Append-flush and fsync every
  response before the next request. Preserve a mechanical transport failure;
  one retry is allowed and qualifies the result.

There are 255 reader answers. Any answer ending by length stops the probe before
judging. All evaluated prompt counts must remain below 65,536.

## 5. Blind scoring

All 255 answers are committed before blind scoring. The 240 primary answers are
hidden behind content-derived blind ids. The judge sees only question, gold and
answer. Use the frozen HH-001 judge rubric and LV-006 parse repair: append the
closed-think suffix and then the seven ASCII characters `VERDICT:` with no
intervening text.

Use seeds `9005`–`9007`, temperature `.2`, top-p `.9`, top-k `20`, and
`num_predict=128`. Majority of three judge passes gives the answer verdict;
majority of five reader answers gives the item-arm verdict. Exactly 720
parseable, naturally stopped judgments are required before opening the mapping.
Normalized gold containment is a secondary direction cross-check. The
category-5 item is scored only for exact refusal.

## 6. Comparisons and dispositions

Register three comparisons:

1. `COMMUNITY_vs_PAIRWISE` — content communities plus compact schema versus the
   existing full pairwise renderer.
2. `QUESTION_REPEAT_INCREMENT` — T2 versus T1, isolating question placement.
3. `FULL_vs_PAIRWISE` — T2 versus C0, the proposed combined renderer.

For each, report semantic gains, losses, ties, net and descriptive exact
two-sided McNemar p for combined, targeted, breadth and other strata. Report
containment direction, answer vote margins, refusal, truncation, prompt tokens,
block characters and structural overhead. Apply independently:

- **`PROMISING`:** combined net at least `+3`, targeted and breadth nets
  nonnegative, and no opposite nonzero containment sign.
- **`WEAK_SIGNAL`:** combined net `+1` or `+2`, targeted and breadth nets
  nonnegative, and no sign reversal.
- **`NO_SIGNAL`:** combined net zero, targeted and breadth nets nonnegative,
  and no sign reversal.
- **`REGRESSES`:** combined net negative or targeted or breadth net negative.
- **`NOT_INTERPRETABLE`:** any validity gate fails or semantic and containment
  have opposite nonzero signs.

The bar is carried unchanged from LV-005. There is no best-arm selection,
parameter tuning, post-result prompt revision, rerun after a valid score,
deployment change or winner claim.

## 7. Preflight — binding before treatment generation

- **PF1 inputs:** hash and count this registration, Part 1, LV-005 prompts,
  TC-014 selections, corpus/blind manifest, vector cache, parser, renderer
  source, Ollama model and GPU.
- **PF2 mechanism identity:** reproduce all 17 C0 prompts byte-for-byte. Verify
  T1/T2 preserve the exact selected set and exact episode elements; verify the
  affinity equation, relevance-order assignment, `.04` threshold, cap eight,
  group rank, within-group chronology and exact wrappers on committed data.
- **PF3 gate ordering:** registration commit precedes implementation; all 51
  prompts commit before answers; answers commit before blind surface;
  judgments commit before mapping access. Mechanically reject early gold or
  mapping access.
- **PF4 reachability:** synthetic rows reach every disposition and sign guard.
  Real traces must contain new-group and join decisions, singleton and
  multi-item groups, at least one cap-bound group, semantic/spread mixed groups,
  and a community order differing from C0 on every row.
- **PF5 stable keys:** content hashes only. Reject duplicate questions,
  identities, prompt schedule keys, missing vectors and missing parser rows.
- **PF6 reproduction:** reproduce all 17 exact C0 prompt digests; independently
  rebuild every T1/T2 prompt digest twice; reproduce Part 1 selected structural
  distributions and LV-006 result digest.
- **PF7 absorbing-state/runtime:** demonstrate all-singleton and
  capacity-partition regimes on a real selected trace. Repeat one real T2 reader
  prompt at seed 5005 byte-identically, nonempty and naturally stopped. Require
  the registered model to be 100% GPU-resident. Rendering has no cross-request
  feedback state.
- **PF8 adequacy:** five replicates expose reader instability and 16 selected
  items can detect a large conversion on known failures. They cannot estimate
  overall accuracy, small effects, transfer, production behavior or a globally
  optimal grouping rule.
- **PF9 surrogate audit:** affinity can group unrelated passages; shared facets
  can be generic; compactness can improve without correctness; repeating a
  question can change verbosity instead of retrieval use; judge majorities can
  share reader bias. Exact evidence preservation, no generated summaries and
  live blind scoring mitigate but do not eliminate these residuals.
- **PF10 live requirement:** this is a live reader probe. Group coherence,
  markup savings, containment and evidence availability are not verdicts.

Additional gates:

- **G-CONTENT:** every arm contains exactly the frozen selected identities,
  every identity once, with episode element hashes matching C0.
- **G-COMPACT:** T1 and T2 block characters must each be lower than C0 on 17/17
  rows. This certifies only compactness, not reader value.
- **G-COMPLETE:** exactly five naturally stopped answers per item-arm and three
  parseable, naturally stopped judgments per primary answer.
- **G-CONTEXT:** every reader prompt evaluates below 65,536 tokens.
- **G-REFUSAL:** report but do not use the category-5 refusal as an adoption bar.

No required-evidence labels may enter the renderer. No new embedding, parser or
LLM-derived summary may be created during prompt construction.
