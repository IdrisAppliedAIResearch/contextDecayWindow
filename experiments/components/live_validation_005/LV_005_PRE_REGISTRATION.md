# LV-005 — frozen TC-014 context-organization probe

**Type:** registered rendering-only live reader ablation  
**Status:** pre-registered; not yet runnable  
**Date:** 2026-08-26  
**Authorization:** program owner approved probes of grouping, chronology and
downstream temporal organization after LV-004

## 1. Question and claim boundary

Can a fixed reader use TC-014's frozen opportunity evidence more reliably when
the same selected episodes are organized into related parent–child groups,
ordered chronologically within those groups, or additionally given explicit
earlier/later guidance?

This is a rendering-only LoCoMo development probe over LV-004's selected
availability-discordant population. It does not change retrieval, selection,
budget allocation, episode text or evidence identities. It is not an overall
benchmark score, a fresh-corpus confirmation, inferred entity resolution,
natural contradiction detection, production adoption or an optimal renderer.

## 2. Frozen inputs and population

- Part 1 artifact SHA-256:
  `aaa11a967d5bad65e07996b4040df340bbf29880002c8c370a58008f35c9ba03`;
  commit `e1f454e8`.
- TC-014 selection SHA-256:
  `32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7`.
- LV-002 prompt seal SHA-256:
  `c01cf11a5e2750c2ed8c03e90c813af7263de8a7fd2c4b78bacb72aa1207d5d8`.
- LV-004 answers SHA-256:
  `639f789396807c89f3242bf9d4e2c05cbf5f349e444d5c1e38b54164c658aebe`.
  Those answers are a reproduction anchor only; all LV-005 arms are generated
  afresh under one common output cap.
- Same 17 questions as LV-004: 16 answerable primary items and one category-5
  refusal secondary. Primary strata remain 9 targeted, 5 breadth and 2 other.
- Every arm receives the exact TC-014 32k opportunity `selected_ids` set for
  its question. Across the 17 rows this is 1,686 episodes: 1,069 semantic and
  617 spread. All 617 spread episodes have one selected semantic parent.

Stable keys are canonical question and episode content hashes. Generated ids,
paths and timestamps are forbidden as comparison keys.

## 3. Arms and exact organization

Every arm preserves each selected episode's compact `<episode turn="…">`,
`<user>` and `<assistant>` element byte-for-byte. Only ordering, deterministic
wrapper labels and the treatment-specific memory preamble may differ.

### C0 `FLAT`

Exact TC-014 opportunity payload and ordering used by LV-004. It must reproduce
all 17 frozen block digests. This is regenerated, not copied from LV-004.

### T1 `GROUPED`

Visit selected non-spread episodes in their frozen opportunity order. Emit one
`<evidence_group rank="r">` per episode. The selected semantic parent is emitted
first with `role="query_anchor"`; if its frozen TC-014 spread child is selected,
emit that child second with `role="related_spread"`. Close the group. No inferred
entity name is printed. The memory preamble says groups contain related
conversation evidence and that group rank follows direct query relevance.

### T2 `GROUPED_CHRONO`

Use T1's groups and group order. Within every two-episode group, sort by the
existing numeric LoCoMo conversation turn ascending, with content identity as
an unreachable tie-break. Preserve `query_anchor` and `related_spread` roles.
The memory preamble says items within each group are in conversation order.

### T3 `TEMPORAL_GUIDANCE`

Use T2's exact group and episode order. A singleton receives
`temporal_role="only_retrieved_item"`. In a pair, the first receives
`temporal_role="earlier_in_conversation"` and the second
`temporal_role="later_in_conversation"`. The preamble tells the reader that
later means later in this conversation, not automatically a correction; use
later evidence for current/latest questions only when the text supports an
update, and retain all items for historical questions.

No arm labels an item `current` or `superseded`. Part 1 showed that natural
LoCoMo records lack SUP-001's explicit memory key and supersession edge, so
those claims are not identifiable.

## 4. Reader runtime and schedule

- Ollama `0.33.0`, `http://127.0.0.1:11434/api/generate`.
- Model `qwen-custom:latest`, manifest id `3516cd593f43`, Qwen 3.5 27.3B Q6_K,
  `num_ctx=65536`, fully resident on NVIDIA GeForce RTX 5090.
- Raw prompt mode, thinking disabled, streaming disabled, `num_predict=2048`,
  temperature `.6`, top-p `.95`, top-k `20`, min-p `0`, repeat penalty `1.0`.
- Five reader replicates per item and arm; seeds `5005` through `5009`.
- Arm order per item-replicate is the ascending SHA-256 order of
  `comparison_key || replicate || arm`, fixed before output.
- One request at a time, `keep_alive=30m`. Responses are append-flushed and
  fsynced before the next request. Mechanical transport failures are preserved
  and may be retried once; any retry qualifies the result.

The 2,048-token cap is common to all four arms because LV-003/LV-004 proved the
512-token cap can truncate this exact population. Any response ending by length
still stops the probe before judging.

## 5. Blinded scoring

All 340 answers are committed before blind judging. Arm, replicate, renderer,
context and offline direction are hidden behind deterministic content-derived
blind ids. The 320 primary answers receive three judge passes each using the
frozen HH-001 rubric, seeds `9005`–`9007`, temperature `.2`, top-p `.9`, top-k
`20`, and `num_predict=128`. Majority of three judges gives the answer verdict;
majority of five answers gives the item-arm verdict. Unparseable or truncated
judge output blocks analysis.

Normalized gold containment is a secondary cross-check. The category-5 item is
scored only for exact refusal. Gold answers and evidence labels are forbidden
from prompt construction and rendering.

## 6. Registered comparisons and dispositions

For T1, T2 and T3 versus C0, report paired semantic-correctness gains, losses,
ties, net and descriptive exact two-sided McNemar p for combined, targeted,
breadth and other strata. Also report T2 versus T1 to isolate chronological
ordering and T3 versus T2 to isolate explicit temporal guidance. Report answer
vote margins, containment direction, adversarial refusal and truncation.

Apply to each comparison independently:

- **`PROMISING`:** combined net at least `+3`, targeted and breadth nets
  nonnegative, and no opposite nonzero containment sign.
- **`WEAK_SIGNAL`:** combined net `+1` or `+2`, targeted and breadth nets
  nonnegative, and no sign reversal.
- **`NO_SIGNAL`:** combined net zero, targeted and breadth nets nonnegative,
  and no sign reversal.
- **`REGRESSES`:** combined net negative or targeted or breadth net negative.
- **`NOT_INTERPRETABLE`:** any validity gate fails or semantic and containment
  have opposite nonzero signs.

The `+3` bar is carried from LV-002/LV-004. P-values are descriptive and no
best-arm selection, renderer adoption, parameter tuning or deployment change
is authorized. Multiple positive arms are reported separately rather than
collapsed into an unregistered combination.

## 7. Preflight — binding before treatment generation

- **PF1 inputs:** hash and count registration, Part 1, TC-014 selections,
  LV-002 prompts, corpus/blind manifest, renderer template, Ollama model and GPU.
- **PF2 mechanism identity:** reproduce all 17 C0 payloads by identity and byte
  digest; verify T1–T3 preserve exactly the same episode identities and exact
  episode elements. Verify every named group, rank, role and temporal label.
- **PF3 ordering:** registration precedes prompt construction; all 68 prompts
  are sealed before answers; answers commit before blind surface; judgments
  commit before mapping is opened. Planted early gold access must fail.
- **PF4 reachability:** synthetic item-majority rows reach every disposition and
  sign guard. Real rows must contain singleton/two-item groups, earlier-child
  and later-child cases, and all three treatment payload orders must differ
  from C0 somewhere.
- **PF5 stable keys:** content hashes only; reject duplicate questions,
  identities, prompt schedule keys and missing parent/child joins.
- **PF6 reproduction:** all 17 C0 blocks reproduce LV-002 exactly; independent
  prompt construction reproduces every T1–T3 digest twice; LV-004's repaired
  batch and result hashes are asserted as the carried failure anchor.
- **PF7 runtime:** one real T3 prompt repeated at seed 5005 must be byte-identical,
  nonempty and naturally stopped. Ollama must report the registered model 100%
  GPU-resident. No cross-request feedback state exists.
- **PF8 adequacy:** five replicates expose reader instability and 16 selected
  items can detect a large conversion on known failures; they cannot estimate
  overall accuracy, small effects, transfer or production behavior.
- **PF9 surrogate audit:** grouping can look coherent while joining unrelated
  evidence; later can be stale or irrelevant; complete evidence can still be
  ignored; judge majority can share reader bias. Exact identity preservation,
  conservative temporal wording, blind scoring and the claim boundary mitigate
  but do not eliminate these residuals.
- **PF10 live requirement:** this is a live reader probe. Rendering structure,
  token counts and containment are not verdicts.

Additional gates:

- **G-FLOOR:** the no-memory prompt at seed 5005 may be semantically correct on
  at most 3/16 items under three blind judge passes.
- **G-CONTENT:** all arms must contain exactly the frozen selected identity set;
  episode text hashes must match C0 and each identity must occur once.
- **G-COMPLETE:** exactly five naturally stopped answers per item-arm and three
  complete judge verdicts per primary answer are required.
- **G-CONTEXT:** Ollama's evaluated prompt tokens must remain below 65,536.

No post-result prompt revision, rerun after a valid score, arm combination,
entity extractor, inferred supersession detector or parameter sweep is allowed.
