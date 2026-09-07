# LoCoMo live-reader transfer of the relevance timeline

Status: **DRAFT implementation design; not registered or runnable.** User requested this document. No corpus inference, new retrieval implementation, threshold tuning or deployment is authorized by drafting it. Proposed next experiment: one retrieval/reader arm over the repository's complete LoCoMo corpus.

## Question and interpretation

How accurately does the current deterministic relevance timeline answer natural-conversation questions when used by the live reader? How often can its existing temporal-anchor rule actually apply outside the synthetic corpus?

The starting configuration is raw query cosine >=0.48, full records, protected identified anchors, chronological presentation, no retrieval character/count cap, no additive last32 block, and—for a uniquely resolved before-event question—removal of records after its anchor. Reader thinking stays off.

Study E's before endpoint reached126/128 across two sequential diagnostic batches, versus106/128 with the full timeline. These results motivate this transfer evaluation; they do not predict LoCoMo accuracy. LoCoMo has also been used extensively in this repository, including live-reader evaluation. This is a naturalistic corpus transfer test for this configuration, **not an untouched benchmark or independent confirmation**.

One arm estimates correctness and characterizes errors. It cannot establish improvement over another architecture, isolate the contribution of the cutoff, or establish superiority to Mem0 or the historical DA arc. Prior reader scores may be contextual references only unless their exact populations, prompts, readers and scoring are reconciled; no historical-control significance test is planned.

## Population and identities

Use the existing frozen LoCoMo source, not a newly downloaded version:

- Source SHA256: `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`;2,805,274 bytes, as recorded by LV-009.
- All10 conversations; all1,986 raw question occurrences. Preserve duplicate occurrences with deterministic occurrence ordinals; do not deduplicate into another denominator.
- Primary scored population:1,540 category1–4 questions. Report categories separately:282,321,96,841 respectively, subject to exact source-inventory verification.
- Category5:446 adversarial questions, answered but evaluated separately with the carried exact-abstention measure. Do not add them to the primary correctness denominator.
- Report each conversation. Historical four-development/six-other splits remain descriptive provenance labels, not newly sealed holdouts.

The mechanism receives only conversation text, source-order/date metadata and the literal question. Answers, evidence labels, category, historical scores and splits cannot affect selection or anchor resolution. Stable keys combine canonical conversation content, question content and duplicate occurrence ordinal; human-friendly dialogue ids are retained as metadata and evidence links.

## One arm: RELEVANCE_TIMELINE

### Source adapter and vectors

Reuse the established LoCoMo pair candidate boundaries and exact embedding texts from the prior pipeline. Freeze the adapter in a separate reproduction checkout. Preserve speaker identity, complete text, dialogue ids and available session dates; do not turn natural dialogue into invented user/assistant facts or discard image captions already included by the adapter. Part1 must enumerate precisely what this adapter retains and omits.

Use the protected development and NF-004 caches referenced by `src/analysis/lv009_exploration.py`, with their file/content manifests and carried embedding model. Compute raw cosine from normalized cached query and candidate vectors. Do not reuse CC80 scores as cosine, use BM25 fusion, or substitute session scores. Missing cache entries are an input gate failure, not a reason to drop questions. Any cache completion requires an explicit pre-run plan with fixed model/text and a new manifest; no silent population changes.

The candidate unit differs in provenance from synthetic E episodes: it is the repository's existing LoCoMo pair unit. The document must report this adapter boundary rather than claiming byte-identical corpus representation across E and LoCoMo.

### Selection and temporal boundary

1. Consider every source candidate in that conversation. Admit all whose raw cosine is >=0.48.
2. Apply the carried label-free temporal parser to the literal question and original candidate text. Its present grammar requires two quoted names plus a before/after clause, and a unique anchor carrier containing meeting/event wording. Preserve its ambiguity/missing/unsupported outcomes; do not normalize LoCoMo questions into that grammar using answers or evidence.
3. Protect an anchor only when the existing route reports a uniquely resolved anchored relation. For resolved before questions, union that anchor and remove selected records after its source position. Retain the anchor record itself, exactly as in E. Other questions retain the chronological relevance selection; no speculative after-event cutoff or latest-state pruning is introduced.
4. Sort by canonical conversation source order (session order, within-session order, stable content identity), preserving available dates in the rendered evidence. No score-order presentation, filler replacement, summarization, refill, top-k or recency add-on.
5. Empty selection is valid: render the carried empty-memory interface and let the reader abstain. Never force one candidate merely to avoid an empty prompt.

**Critical applicability limit:** source order is not necessarily event time in natural dialogue. A later utterance may describe an earlier event or retrospectively correct it. Even an exactly named anchor does not certify that dropping subsequent utterances is semantically safe. Paired utterances can also contain statements on both sides of an event; the whole anchor candidate remains. These are transfer questions to measure, not properties certified by a unique text match.

This draft carries the existing parser unchanged. It does not promise broad natural-language anchor resolution. If Part1 finds no applicable LoCoMo anchors, the run would test the unbounded relevance timeline but not the prefix component. That distinction must be published before reader inference. A new semantic/date-based resolver would be a separately documented component, not a quiet repair inside this arm.

## Reader and capacity

Use the exact HH001 brief-fact/abstention payload from the latest E prefix runs, with necessary LoCoMo evidence metadata in the memory block. No extra temporal reasoning instructions or query rewriting. Pin model/binary/template manifests from `prefix_106_reader`; Qwen3.8-27B UD-Q4_K_XL, verified native thinking off, reasoning budget0, template enable_thinking=false, seed5005, batched parallel9 (conditional on the fit gate below), cachefalse, temperature.6,top_p.95,top_k20,min_p0,repeat_penalty1,presence_penalty0. Output allowance4096.

Batching is explicitly required by the user. The [GPU capacity probe](BATCH_CAPACITY_REPORT.md) validated nine concurrent requests at32768 tokens per slot with2282 MiB minimum free VRAM; ten slots left938 MiB at startup and failed the1536 MiB reserve. Use total `--ctx-size 294912 --parallel 9`, preserving32768 per request. Keep token batch2048/microbatch512 as tested. Nine is a short-load capacity result, not a guaranteed speedup or long-output endurance result. Client scheduling must actually maintain concurrent independent requests and record slot identities. Calibrate the batched native-off interface and check repeated seeded responses before measurement; do not assume serial/batched answer identity.

Initial per-request reader context32768 matches E. Before registration, tokenize **all** complete prompts and report their distribution and maximum. Never truncate evidence to fit. If any prompt plus4096 exceeds the window, the full run cannot start under this runtime. Resolve capacity explicitly before registration with a common sufficiently large supported window and repeated calibration, or retain a documented input-capacity block. No threshold increase, question exclusion, fallback character cap or per-question output reduction is allowed to hide overflow. This is a fit gate, not a resource-limit sweep.

Schedule1,986 reader calls in deterministic content-key/occurrence submission order, up to nine in flight, one answer each. Completion order is asynchronous and must not determine scoring identities. On an uncertain failure, stop new submissions and persist all in-flight results. Persist pending-request metadata before sending and raw response immediately after return. Commit a completeness manifest before scoring. Transport uncertainty, missing/empty output or length termination stops the batch for an explicit repair decision; preserve every captured answer and never silently retry or change the output cap. Native thinking must be checked through server properties, rendered template and two identical seeded arithmetic calibration responses before measurement.

## Scoring and endpoints

Primary: number and percentage of correct final answers over all1,540 standard questions, using the existing HH001 semantic correctness rubric and frozen LV-009 judge parser. Report per category and conversation, plus a10-conversation cluster bootstrap interval (10,000 resamples,seed93002), clearly identified as descriptive uncertainty on a small fixed corpus.

Proposal for scale-appropriate scoring: three blind local judge passes per standard answer, seeds9100/9101/9102, temperature.2,top_p.9,top_k20,min_p0,repeat_penalty1,4096output allowance, verified native thinking off. Majority gives the proposed verdict. This adds4,620 judge calls; it is still one retrieval/reader arm. Calibrate on answerless, correct paraphrase, wrong entity/date and contradiction fixtures; require parseable verdicts. Commit the exact rubric, calibration cases, parser and adjudication triggers before measurement. Never score reasoning-only content or silently discard an unparseable judgment.

LoCoMo prose does not fit E's eight-location canonical scorer. Carrying E's exact-string scoring would be an invalid instrument. Record whether the owner-authorized single-agent adjudication exception extends to disputed LoCoMo judgments before locking; if used, disclose it rather than calling it an independent human audit. Until then the scoring protocol is proposed, not finalized.

Secondary diagnostics after scores are committed: complete/partial/no annotated evidence delivered, answer correctness within those groups, unsupported or ambiguous anchors, active-cutoff counts, cutoff evidence losses, empty selection, abstention, and actual output-token/runtime distributions. Evidence labels are incomplete benchmark annotations, not a universal sufficiency oracle. Report any unresolved evidence ids rather than calling them misses silently.

No invented WORKS threshold or weaker success bar: this single-arm transfer design is descriptive. It succeeds operationally only when its frozen population is completely captured and scored; that is not an efficacy verdict. An architecture decision would require a separately justified benchmark target or comparison.

## Preflight and implementation sequence

Part1 is required before registration: inventory and hashes; source-adapter fidelity; cached-vector coverage; raw-cosine/selected-count distributions; empty/full cases; anchor activation and reason distributions; full-prompt tokenization; source-order versus event-time examples selected without gold. Record what the named components actually do. This draft does not substitute code reading for those executed findings.

| Gate | Executed artifact required before the full run |
|---|---|
| PF1 inputs | Source hash/count/category inventory, vector/model manifests, no missing candidates or questions |
| PF2 identity | Raw-cosine boundary fixtures; no cap; chronology and exact-prefix checks; natural anchor applicability report |
| PF3 ordering | Fault-injected missing/failed input and calibration gates make zero measurement requests; commit-order assertions |
| PF4 reachability | Empty/full selection, unique/missing/ambiguous anchors, supported/unsupported routes and both judge outcomes exercised |
| PF5 keys | Deterministic repeated-question occurrence keys and reversible dialogue/source mappings |
| PF6 reproduction | All128 E prefix selections/payloads reproduce from their frozen inputs; LoCoMo adapter/vector texts reproduce committed prior identities, not TC-014 selected sets |
| PF7 state | One-pass stateless selector; no cross-question context cache or feedback; per-request state isolation verified |
| PF8 coverage | Full-population offline preflight; a fixed20-question calibration sample, two per conversation chosen by hash before scores, runs before the remainder. Include its captured answers in the population, never tune on them |
| PF9 surrogate | Unique anchor does not establish event time; annotated evidence does not certify sufficient context; parseable judge does not certify accuracy. Report these residuals |
| PF10 live endpoint | All1,986 reader answers,1,540 semantic correctness decisions and446 separate abstention outcomes required |

Also enforce a clean pinned reproduction checkout, adapter import-path checks, labels/answer-key leakage sentinel, serialized prompt hashes, no unexpected context shift, and all source statements retained for selected records. Offline independent shards may use available CPU workers; the newly registered batched runtime must be pinned, including separate reader/judge calibration; earlier serial studies remain unchanged. Estimate total reader **and judge** time from calibration before launch, and use quiet completion/error hooks.

Deliverables in order: Part1 report and sealed adapter/selection/prompt manifests; standalone locked registration; implementation and executable gates; calibration; raw answers and completeness; blind scores and adjudications; results and error atlas; README/AGENTS/handoff and a separate LoCoMo draft PR. Existing E and PR96 artifacts remain unchanged. No production merge or adoption is part of this design.

## Items to resolve before registration

1. Run label-blind Part1 and establish whether the carried anchor grammar activates enough to test temporal-prefix transfer at all. If inactive, name the narrower test honestly or explicitly design a new resolver before inference.
2. Verify the precise candidate/date/speaker adapter and complete cache coverage; freeze all file and code hashes.
3. Verify full uncapped prompt fit and freeze the common reader context accordingly.
4. Lock judge calibration, disagreement handling and any authorized adjudication deviation for LoCoMo prose.

Reference implementations and evidence: `src/analysis/lv009_exploration.py`, `src/analysis/hh001_prompt.py`, `experiments/study_D/temporal.py`, `PREFIX_106_REPORT.md`, `relevance.py`, and `prefix_106_reader.py`. Historical corpus/scoring inventory: `experiments/components/live_validation_009/LV_009_PRE_REGISTRATION.md`. These identify local sources; they do not import old study authorizations or claim official benchmark equivalence.
