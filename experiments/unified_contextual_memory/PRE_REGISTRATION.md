# Unified contextual memory: exposed-LoCoMo paired development validation

Status: experimental lock on commit containing this document. No benchmark reader or judge outcomes have been generated for this comparison. Executable preflight and then live instrument calibration must pass before benchmark generation.

## Scope and authorization

The user accepted the integrated [architecture design](../designs/unified_contextual_memory/DESIGN.md) at `8927134a` and authorized end-to-end implementation. This registration intentionally tests the combined deterministic bundle, resolving the standing one-component scope rule for this comparison only. Phase A/B development and its revisions were recorded before this experimental lock. No prior registration is edited or reopened. Production adoption and a stronger/reasoning-enabled reader are outside scope.

This is development validation on exposed data, not fresh confirmation or a transfer test. Earlier NF/TC/LV/DA arcs and the recent 30-question probe have exposed LoCoMo questions, labels, or outcomes; LongMemEval was also previously used. The current configuration and captions differ from historical arms, so historical scores are context rather than a causal comparator. Success concerns this frozen bundle under this reader, not individual-component attribution, human-like memory, proven natural event resolution, or generalization.

## Corpus and source contract

Use all 1,986 raw QA occurrences from the ten conversations in `C:/Users/muzaf/Downloads/locomo10.json`, SHA256 `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`. Primary population: 1,540 category 1–4 occurrences. The 446 category-5 adversarial occurrences are separate and never enter the primary correctness endpoint. Preserve duplicates in the primary benchmark-occurrence denominator; report deduplicated `(conversation, question)` sensitivity using the first stable-key occurrence.

Both arms receive identical eligible sources: original speakers/text, chronological session/date/dialogue identity and supplied `blip_caption` annotations with explicit provenance. No generated captions, downloaded image content, question-answer annotations, event summaries, observations or session summaries enter memory. Image URLs/search metadata are not rendered. There are 5,882 source utterances and 3,011 adjacent nonoverlapping pairs. Caption repair recaptured 1,091 pair vectors; 1,920 unchanged historical solo vectors were reused. The prepared manifest records this mixed provenance rather than claiming a single recapture runtime.

Knowledge horizon is the supplied conversation snapshot. Questions are asked after its eligible sources; there is no guessed before-anchor cutoff. Any narrower horizon must rebuild contextual views from eligible sources. The mechanism rejects context membership outside its supplied source universe. This does not prove an upstream caller supplied a truthful horizon.

## Frozen arms

**C0:** independently frozen source-matched direct cosine >= .48, whole-pair materialization, chronological original-source renderer, no recency block and no item/character retrieval cap. The isolated clean control checkout is `946c373d5edfe9d954391bdbafaed6646607659e`. Its selections/payloads are in `artifacts/control`; the historical caption-omitting score/ID/payload replay separately matches all 1,986 groups exactly.

**C1:** preserve all C0 admissions and add contextual access plus fixed extractive reference/context-support traversal under the Phase B v2 max-product rule. Qwen3-Embedding-0.6B Q8_0, SHA256 `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`, contextual last-token pooling at source-pair boundaries, complete session windows greedily split at whole pairs for the 8,192-token encoder limit. No overlapping windows; an oversized pair fails instead of truncating. Exact cached vectors are authoritative during evaluation; no encoder or parser calls occur during the reader run.

Auxiliary operating points came from the independently recorded 99th-percentile mismatch-tail rule, with no answer/evidence optimization: contextual `0.4999267833352672`, support `0.5593376334306865`, reference `0.5278224842431918`. The direct threshold and composed path floor are both `.48`. A seed starts at its original query cosine; each semantic edge multiplies activation by its cosine clamped to [0,1]. Both the route threshold and composed floor must pass. Best activation wins; descending activation and stable IDs determine order. There is no depth/item/character stopping cap.

spaCy 3.8.14 / en_core_web_sm 3.8.0 produces fixed original-sentence reference cues for third-person/demonstrative words and definite noun chunks. Contextual seeds seek non-self source support only inside their actual encoding window. Reference cues can search the same conversation. Candidate links remain unresolved alternatives. The ledger accepts explicit source-grounded exclusions, but LoCoMo supplies none: no automatic natural contradiction, event-identity, or temporal-state resolver is claimed. Rejected links cannot continue through that path; independently supported routes remain eligible. Finite frontier exhaustion is a computational stop, not semantic completeness.

Mechanism code is `src/unified_memory`; frozen prepared/reference vectors, thresholds and v2 selections live in this experiment's `artifacts` directory. The preflight manifest binds their exact file hashes and all evaluation code before generation. Source rendering is common, so changes cannot be attributed to caption repair between C0 and C1. All formation/indexing/retrieval decisions make zero generative calls. There is one final answer request per unique assembled prompt, with explicitly mapped reuse for identical prompts; no answer feeds back into retrieval.

## Part 1 record and readiness

Native-last pooling matched the standalone embedding exactly and repeated captures were exact. Appending text with equal token prefixes changed contextual vectors slightly (cosine .999719); no causal prefix invariance or future-attention attribution is claimed. Full context/target membership keys prevent unsafe prefix-cache reuse.

Initial independently qualifying links caused indiscriminate closure: 1,232/1,986 full conversations, 1,979 at >=90% of source characters, median fraction 1.0. These failed-development outputs are preserved in `characterization_v1`. Before v2 replay, the design added composed decay without changing the three mismatch thresholds. V2 has zero full conversations, 70 at >=90% of source characters and median fraction .37596 versus C0 .20829; all direct IDs survive and all queues terminate. These are known development diagnostics, not preregistered discoveries or reader gains.

The exact token fit has 3,972 arm-occurrence prompts: maximum 40,417 input tokens; medians C0 7,554.5 and C1 13,820.5. Median paired-full ratios are .21356 and .38323. Common context is **45,056**, unchanged output reserve **4,096**. The generation-disabled common-capacity check replays the longest twenty prompts exactly and verifies GPU placement. Its observed free VRAM is 12,764 MiB. This is startup capacity, not a promise that long inference cannot fail.

Freeze the nondegeneracy readiness/interpretation guard at median paired-full token ratio <.75 and fewer than 10% of questions at >=.90. This is selected with known development expansion, not an independent confirmatory result. It does not truncate evidence. Failure blocks the live selective-memory comparison; any later successful answer outcome cannot rescue failed selectivity. Report the whole token/selection distribution and limits.

## Reader, schedule, and instrument gates

Use the pinned Qwen3.8-27B UD-Q4_K_XL llama-server runtime from Study E `restart005/runtime_pins.json`, verified by every file hash at startup. Same HH-001 reader template (`src/analysis/hh001_prompt.py`) in both arms, not asserted to be the Mem0 paper prompt. One native user message, template `enable_thinking=false`, server `--reasoning off --reasoning-budget 0`, one slot, serial orchestration, CUDA0/all layers offloaded, flash attention, q8_0 K/V and no context shift. Log verbosity 4 exposes actual placement and `thinking = 0` in this build.

Reader settings: seed5005, temperature .6, top_p .95, top_k20, min_p0, repeat penalty1, presence penalty0, prompt caching false, native output at most4,096. Verify the closed native thinking suffix, runtime thinking state, and two identical brief arithmetic responses (`17+28` -> `45`) before benchmark calls. Calibration never changes retrieval.

Execute the first two stable-key questions per conversation first (twenty total), followed by all other stable keys. Alternate arm-first order by schedule index. Exact native-prompt SHA reuse within/across arms and duplicate occurrences is intentional; persist every mapping. This reduces redundant calls and makes identical interventions share the same realized answer; it is not replication or evidence of reader determinism. No batch9 execution. The first twenty exercise the real run but are not a separately tuned/selected score endpoint.

Scoring calibration is five fixed positive/negative fixtures at seeds9100/9101/9102: empty answer incorrect; red-bicycle paraphrase correct; wrong city incorrect; wrong year incorrect; `Rome, not Paris` incorrect. All fifteen votes must match; malformed, capped, empty, or reasoning-exposing outputs stop the instrument. This tests basic scoring behavior, not broad judge validity.

## Scoring and sealed order

Persist each request before its call and each raw response immediately, including failed responses. Commit complete reader outputs and alias mapping before constructing an arm-blind judge surface. Only question, gold and generated answer go to the HH-001 judge; no arm name, retrieval trace, source availability or comparative result. Identical judge text is deduplicated with mappings. Use the same pinned model in native-off mode, temperature.2/top_p.9, seeds9100/9101/9102; all other settings and common output limit unchanged.

Parse the **last complete VERDICT line with its following nonempty REASON**, covering corrections in both directions. A final verdict lacking its reason fails, even if an earlier verdict was valid. No correctness defaults, online scorer repair or silent excluded rows. Commit all complete judgments before aggregation; commit blind majority votes before opening paired outcomes and evidence diagnostics. Majority >=2/3 is the primary score. Report disagreement counts and retain all explanations. There is no human audit or claim of independent judges: the three seeds use one model, which also produced the answers. Any later audit is separately labelled and cannot silently rewrite this endpoint.

Category5 reports exact `I don't know.` abstention counts separately; it is not ordinary gold correctness and does not affect the main disposition. After score sealing, report annotated-all/any evidence delivery and correct/incorrect cross-tabs for C0/C1. An annotation hit is not proof of sufficient context; missing annotations are not proof no alternate support was delivered. Preserve questions, gold answers, generated answers and source IDs for later qualitative diagnosis.

## Primary estimand and prospective dispositions

Primary effect is C1 minus C0 correct-answer fraction over the 1,540 raw category1–4 occurrences. Compute paired 95% percentile intervals by resampling the ten conversation clusters with replacement 20,000 times, seed70107; each resample uses occurrence-weighted totals. Report counts, gains/losses, absolute percentage points, interval and per-category/per-conversation results. Ten clusters give limited precision and no independence/transfer guarantee. Deduplicated sensitivity uses the same method; it cannot replace the primary.

- **WORKS_ON_EXPOSED_LOCOMO:** gain >=2 percentage points, lower95% interval >0, nondegeneracy guard passes, and no category1–4 absolute point-estimate regression greater than3 percentage points.
- **WEAK_SIGNAL_ON_EXPOSED_LOCOMO:** primary gain >=1 percentage point, nondegeneracy passes and the same category guardrail holds, but the stronger bar is unmet. Statistical separation is not required; describe it explicitly as weak.
- **NO_QUALIFYING_GAIN:** neither bar passes. Report effect/direction, whether lack of gain or a guardrail caused disposition, and exact surviving mechanism evidence. Do not infer the deterministic thesis failed.

Both tiers and the negative branch are checked on synthetic paired outcomes before inference. These thresholds are practical development choices rather than power guarantees or prior evidence. There is no parameter sweep, outcome-based stopping, or promotion by availability alone.

## Failures and monitoring

Every request has a durable unique pending artifact. Uncertain requests are never automatically retried. Any startup/capacity/calibration failure, missing/malformed/capped response, model exit, hash drift or gate failure halts the evaluation and preserves partial work. No incomplete full-population score is substituted. Repairs require a standalone documented amendment before further affected measurement; deterministic offline instrument bugs may be corrected before any generation and re-preflighted with the original failed gate retained. Do not change a threshold, reader mode or output cap to rescue observed accuracy.

The local health thread records state every15seconds without an LLM call. A call exceeding120seconds creates a slowdown event; HTTP timeout600seconds fails the call. Two consecutive samples with free VRAM below1,024MiB or an exited owned server create a failure; only the owned server can be terminated. Startup requires1,536MiB free. Completion/failure records are durable. Native Codex follow-up is activated only once this long run begins; it reads compact status/events, avoids repeated verbose polling, continues closeout when ready, and is paused after completion. Hardware monitoring is instrumentation, not selection.

## Preflight and residuals

`preflight.py` must produce committed `artifacts/preflight.json` before `run.py` can start. Live calibration is an additional gate before any benchmark answer. A PASS here does not assert future completion.

| ID | Executed evidence required and accepted residual |
|---|---|
| PF1 | Hash every consumed source/vector/selection/prompt/code manifest, count1,986 paired keys, validate corpus and capacities. Hashes certify identity, not truth of source annotations. |
| PF2 | Route/self-support/conflict/caption fixtures; exact cached versus uncached real traces. Semantic antecedent correctness is not certified. |
| PF3 | Missing-registration/preflight and token-only generation negatives; pending-before-call and no-retry fixture; calibration/reader/judge/vote commit barriers in runner. Durable files do not establish judge validity. |
| PF4 | Synthetic strong gain, weak gain, loss and selectivity-failure outcomes; operating points have real qualifying candidates. Reachability is not adequate power. |
| PF5 | Content IDs and exact rendered/native hashes on every arm occurrence. Corpus manifests additionally bind dates/metadata. |
| PF6 | Historical scores/IDs/payloads exact for1,986; independently frozen C0 source/IDs/payloads, never flag-disabled treatment. |
| PF7 | Every real queue within finite bound; query-varying outputs in every conversation; preserved full-corpus v1 positive degeneracy control, v2 replay and weak-chain/cycle fixtures. Finite does not mean relevant or complete. |
| PF8 | Full intended source universe/all1,986 questions plus30-link weak chain. Does not test online appends, unbounded endurance, unseen schemas or future tasks. |
| PF9 | Self-support/unavailable-context negatives, unresolved support, v1 full expansion and explicit limitations above. Annotation availability, provenance, frozen embeddings and zero generative calls remain separate properties. |
| PF10 | This paired live reader comparison supplies end-to-end disposition. Offline availability never does. |
