# Study E — confirmation registration after amended development

Date: 2026-09-06. **Same Study E; design-only lock before confirmation implementation or generation.** The commit containing only this registration is the integrity anchor. Do not edit after lock. Standalone amendments govern any later authorized change.

User authority: end-to-end implementation, agent scoring and completion, and explicit continuation by amendment within Study E. Prior draft and development amendments remain historical records. This registration is the authoritative confirmation parameter source; referenced generator and mechanism bytes define their exact algorithms.

## 1. Question and scope

Does newest-first ordering within the existing before-anchor eligible set improve generated final-answer correctness relative to Study D's temporal ordering, at identical retrieval and reader budgets?

C0 is frozen Study D C1 (temporal retrieval), not plain CC80. C1 changes only accepted before-anchor ordering: same unique anchor first, same exact-quoted-subject eligible set, then descending source turn with source-identity tie breaking. Preserve 8,000 serialized characters for temporal admissions, unchanged 32,000-character final retrieval packing, full source episodes, CC80 fill, renderer, deduplication and additive latest-32 continuity. All other routes remain C0-identical. The intervention can alter both membership and presentation order; their effects are not separately identified. No DA compression, state parser, learned router or prompt change.

## 2. Development evidence and limits

Initial complete-evidence pilot: C0/C1 final answers 11/12 each. Amendment 002 neutral shared logs still saturated evidence and did not enter its reader stage. Amendment 003 competing-update development: exact primary evidence 4/16 versus 13/16; on the 12 paired reader questions, evidence 3/12 versus 10/12 and correct final answers 3/12 versus 6/12 (4 gains, 1 loss). C1 still missed four complete-evidence cases. Latest 3/4 each with identical responses; absence 4/4 each. Thirteen exceptions were agent-adjudicated without human audit. These are exposed development observations, not confirmation evidence or effect-size guarantees.

Text-only availability was invalid because an older repeated value could match a required sentence. Exact required source identities in the actual final pack govern. Old text-only artifacts remain preserved and are not reused as counts. All required carriers precede continuity. A correct answer without those identities can occur by value coincidence; report that cell without calling it sufficient retrieval.

## 3. Frozen population and units

Use exactly 32 new groups with seeds **94001–94032**. Each group has six independent 140-record histories, one per condition in this order: straight, irrelevant, future, proposal, latest, absent. Total **192 histories, 26,880 source records, 192 questions**. Before conditions supply 128 primary questions. Five reader seeds **5005–5009** per question and arm. Four logical arms yield **3,840 logical answers**, with 640 primary answers per C0/C1 arm. The inference unit is the group: average five seeds within question, then four before conditions within group. Histories within a group share generation randomness; do not treat them or reader seeds as independent groups.

The exact corpus algorithm is `generate(seed)` in `prepare_amendment003.py`, SHA-256 **70eebdd24e6e3a2efc2fb7af963dc63dca69feb062ca310b9882f9a2e602cccf**, using `corpus.py`, SHA-256 **53abd4e029790576e3df09e7d17259d179d32e183bd884c888f010a1017fc7af**. Import these unchanged generation functions; do not call their development main functions. Python **3.13.13**, NumPy **2.4.6**.

Each history keeps its query subject's five original planted records and independent unrelated continuity, replacing other early heads with genuine prior delivery updates or explicit no-change reviews as defined in Amendment 003. Preserve future-effective and unaccepted-proposal qualifications. Values are office, warehouse, studio, depot, workshop, laboratory, annex, hangar; additional values may coincide with the gold. No ordinal-bearing answers, fixed target turn, or prospective C0-error/C1-gain filter. Original anchor feasibility sampling, randomized gaps and source values are defined by the pinned generator. Required sources precede turn 109; each query is at snapshot 140/probe 141. Latest and absent are guards, excluded from primary averaging.

Generate every registered instance exactly once into a new confirmation directory. A malformed source, collision, missing required carrier, mismatch between actual source state and reference, or control identity failure stops the instrument. Do not replace seeds or modify the population after opening it. No requirement for mixed support or treatment benefit is applied to confirmation inclusion; those were development-readiness checks only.

## 4. Four reader arms and runtime

C0/C1 use the unchanged Study D HH-001 prompt plus empty think suffix; no reasoning request. This is not a verified Mem0-paper system prompt. ORACLE receives only its prospectively specified sufficient records, in ascending source turn using the carried renderer. For future/proposal cases include target, qualifier and anchor. NULL uses the carried empty memory. Absent ORACLE is empty and may alias NULL. ORACLE/NULL are diagnostic references, not exclusion or success gates, and must be captured/scored.

Mechanism file `mechanism.py` SHA-256 **cd04f01e35904405bd67fd98f3b1bf4689c00182a767fb297eafe415a2b476c5**. Controls: isolated worktrees at **05ef90e29b849196515cf39f52ba09754656c599** and **5ebda1ef4510c1806709039aeb66e6d79cedbbd8**; verify clean and pinned before preparation and reader start. Reject current-study engine leakage. No carried product changes.

Reader Qwen3.8-27B UD-Q4_K_XL SHA **bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372**; launcher SHA **125e0938a280cba46c803a60178e51826203e030abacce03367a22108720f7ac**. Reuse the full launch command from `artifacts/amendment003/reader/launch.json` with a new process identity and logs: one slot, context 65,536, CUDA0, all GPU layers, q8_0 K/V caches, flash attention, no context shifting, no speculation. Record server properties, PID and loaded runtime paths. Single inference stream.

Generation: temperature .6, top_p .95, top_k 20, min_p 0, repeat_penalty 1, presence_penalty 0, cache_prompt true, reasoning_format none, non-streaming raw completion, **8,192 output-token cap**. Verify each prompt's tokens plus cap fit context before calls. Maximum-prompt identical repeats at seed5005 must match byte-for-byte before the scored schedule; one short ready calibration follows. These three calibration calls are unscored.

Embeddings: same pinned single-text Qwen3-Embedding-0.6B-Q8_0 file SHA **06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439**, `PinnedEmbedder` from the original engine. Eight independent one-thread CPU workers, 512 context, identical per-worker sentinel; persist vectors, text-to-vector mapping, hashes, worker IDs, aggregate CPU and wall time. No batching or model-call shape change. Cached exact vectors may be reused only with verified exact canonical text/hash matching; a missing vector during read-only prompt assembly stops.

## 5. Schedule, aliases and completion

Group ascending, condition order from §3, reader seed ascending, then arm order. Rotate base `[C0,C1,ORACLE,NULL]` left by zero-based group index modulo four. Build and commit all prompt identities, logical rows and physical-call aliases before inference. Deduplicate only byte-identical full prompt plus reader seed; each logical question/arm retains its own reference and score identity. This makes identical latest C0/C1 conditions share a response. Never alias by answer, retrieved set alone or semantic similarity. Physical calls are first encounters in this deterministic logical order, preceded by the three calibration calls. Report logical and physical denominators separately.

Seal the registration SHA, generator/runner hashes, inputs, prompts, source validation, control identity and all call aliases before inference. Persist and fsync each returned response before any next request; save an uncertain-request journal before submitting. Any timeout or uncertain call stops—no automatic retry. Any missing, empty, capped, truncated, non-EOS or unfinished tagged reasoning output stops scoring of the full confirmation population. Preserve outputs and report an instrument stop, not mechanism failure. No automatic cap increase, call replacement or partial-population verdict. A continuation requires a separate authorized amendment.

Do not inspect correctness while the schedule runs. Completion/failure monitoring reads only terminal state, metadata and process/file freshness and stays quiet when unchanged. No repeated healthy polling.

## 6. Prospective scoring responsibility

Endpoint: correctness of the explicit final answer against the source-established reference. Mechanical canonical grammar is the frozen development grammar: trim surrounding whitespace/quotes and final `. ! ?`, normalize case and apostrophe, optionally remove leading `the`, then compare exactly against the eight vocabulary values or `I don't know`. No substring matching. Blank is NO_ANSWER/zero and also a completeness failure.

For noncanonical responses, the user's agent-scoring authorization is implemented prospectively as **one blinded agent adjudicator**. This is a registered agent-only measurement limitation, not human review or independent three-pass validation. Calibrate on the frozen Amendment003 NO_ANSWER/contradiction examples before opening confirmation answers. An explicit final correction supersedes an earlier assertion for final-answer correctness; separately record corrected wrong openings. Explanations cannot provide credit without a final commitment outside tagged reasoning. Unresolved competing final answers score zero. Unambiguous misspelled abstention is semantically correct but marked noncanonical. Judge factual value, not explanation fluency or formatting. A genuinely unresolved rubric application blocks unsealing and is recorded, not silently excluded or repaired.

Make blinded rows with question, reference, response and opaque score identity, excluding arm, group, sources and traces. Commit completeness before mechanical scores. Preserve mechanical pending records; add item-level exception judgments with exact final-answer evidence and rationale, resolved scores and a new gate. Commit **all four arms' resolved scores and rationales before opening arm mapping or confirmation mechanism traces**. No post-outcome human-audit claim. The report must state counts and limitations of agent judgments; do not call this an independently audited benchmark score.

## 7. Analysis and fixed dispositions

For each group compute C1−C0 mean primary correctness, averaging five seeds within each of four before questions and then the questions equally. Mean over 32 groups is the primary contrast. Paired group sign-flip test: 100,000 draws, NumPy default_rng seed **95001**, independent signs ±1, one-sided improvement, plus-one correction; count simulated means >= observed−1e−12. Paired group bootstrap: 10,000 resamples, default_rng seed **95002**, percentile 2.5/97.5 with linear quantiles. Fixed sample, no early efficacy stop, no extension. Report reverse-direction/per-condition effects descriptively without additional success claims.

Disposition precedence:

1. INSTRUMENT_FAILURE or PENDING_ADJUDICATION prevents a mechanism verdict.
2. REGRESSES if primary mean <= −.025, any irrelevant/future/proposal condition's mean difference < −.05, or absent-field correctness difference < −.05. These are observed-harm guardrails, not population-harm proofs. Latest C0/C1 prompt/alias identity is an instrument invariant.
3. D1_WORKS if primary gain >= .10 and one-sided p <= .05, with guards passing.
4. D2_CARRIES_SIGNAL if gain >= .025 and p <= .10 with guards passing, but not D1.
5. Otherwise NO_DEMONSTRATED_BENEFIT / CHARACTERIZED; no equivalence claim.

The original draft's numerical bars are retained. They apply only to this new confirmation population. `artifacts/confirmation_prelock_v2.json` demonstrates attainable positive, signal, tie and each harm branch with five-seed-compatible .2 increments. The older prelock fixture used unattainable .5 per-question differences and is superseded; no criterion changed.

Availability is diagnostic: exact required source identities at candidate, temporal admission, final selection and rendered prompt. Do not score old coincident values as the required carrier. Report complete/incomplete × correct/wrong on the same logical observations; record candidate/packed ranks, displacement, lengths and costs. For absent queries availability is not a positive-evidence metric. Report ORACLE/NULL separately, including incorrect ORACLE answers; no ORACLE-based exclusions or rescue. Conditional comparisons are descriptive, not causal reader-attribution claims. Also report corrected wrong openings and noncanonical abstentions, without changing primary scores.

## 8. Preflight and staged gates

Development Part 1 is complete. The prelock evidence below validates the methods; confirmation-instance checks necessarily follow generation after this design-only lock and must be committed before inference.

| Check | Existing empirical evidence | Confirmation enforcement before calls |
|---|---|---|
| PF1 inputs | Amendment003 source gate: 24 histories/3,360 records, independent text-state checks; pinned runtime and vectors | Hash pins; exactly 192 histories/26,880 records/192 QAs; required carriers before109; source-reference agreement |
| PF2 identity | 224 prior prompts exact; active before/absence routes; latest identical; repeated amended builds | Anchor/set preserved, reverse turn ordering only, latest exact; original controls clean |
| PF3 gate order | Development input→completion→blind scores→resolved commit→analysis; protected pending journal | Design-only SHA required before generation; input seal before runner; complete before scores; all scores before mapping; negative invocation checks |
| PF4 achievable | `confirmation_prelock_v2.json` positive/signal/tie/primary and all guard harms | Replay fixtures; no treatment-gain or mixed-evidence inclusion filter |
| PF5 keys | Stable content IDs, exact carrier correction, latest response identity4/4 | Content/prompt/seed alias identities; separate reference-specific logical scores; duplicate/regeneration audit |
| PF6 replay | `artifacts/part1/replay.json`:224/224 and224 repeats | Frozen control pins and deterministic development identity check before new inputs |
| PF7 feedback | Pure repeated builds; sources unchanged; no response writeback | Assert unchanged source/vector hashes; no stateful/endurance claim |
| PF8 scale |43 calls over140-record histories; maximum12,047 input tokens; allEOS | Full tokenizer accounting for every physical prompt at identical140-record scale; one-slot prefix check |
| PF9 surrogate | Duplicate-value text-only failure repaired by exact source IDs; real reader3/12→6/12 despite evidence3→10 | Exact carriers plus rendered survival, final answers, no answer-string availability shortcut, agent-review disclosure |
| PF10 reader | Paired live development, guards and blind scoring complete | All four arms/5seeds; full completeness and scoring gates; reader-only verdict |

Preflight failures identify the exact instrument or invariant. No box is accepted without its artifact or executed check. Frozen synthetic snapshots do not test a live evolving 140-turn dialogue or endurance; a sequential-dialogue ablation claim is not made.

## 9. Deliverables and interpretation

Commit registration, implementation, full source/vector/prompt manifests, gates, raw responses/logs, logical aliases, blind/resolved scores, analysis and report. Update README, <=400-character AGENTS digest, memory and the same Study E PR95. Update ERRATA only if a prior published number changes. No automatic merge, deployment or adoption.

A positive result establishes an ordering-policy reader benefit under this synthetic competing-update generator and frozen local prompt/model. It does not establish field-aware state inference, naturalistic language transfer, general multihop competence, DA fusion or continual learning. Development-driven corpus changes limit scope and are fully disclosed. A negative result closes this tested policy/population comparison, not temporal memory as a whole.
