# Study D — restricted temporal retrieval under the deployed character budget

Status: CONFIRMATORY DESIGN LOCK. The commit introducing this file is the registration anchor. This registration governs over preserved draft Revision 2. No confirmatory source session, reader output or score existed when the design was written. The user's end-to-end delegation and subsequent instruction to continue authorize completing and executing the design through its gates, not production adoption.

## 1. Question and population

Does the fixed deterministic temporal allocation improve reader correctness for immediately-before and latest-setting questions in substantive synthetic revision histories? Characterize complete evidence delivery, conditional reader performance, supersession, duration, multi-hop and absence handling separately.

Generate exactly 32 new sessions using seeds 92001 through 92032 with the frozen `corpus_opaque.make_session` generator. Each has 140 source episodes and seven probes, one each T1/T2/T3/T4/M1/M2/N1, all at source snapshot 140 / probe turn 141. Total: 4,480 source episodes, 224 queries, 32 independent randomized session units. All answerable facts precede the probe and are outside last-32 continuity. No reader answer enters a subsequent snapshot.

The four development seeds 91001-91004 are excluded. This holdout separates names, values and operational details, not template families: it tests transfer across randomized instances of this restricted generator. It does not test naturalistic language, different templates, organic conversations, general temporal competence, conversational endurance or other readers. The originally proposed sparse corpus saturated at 24/24; a substantively revised corpus was developed, then ordinal-bearing answer codes were replaced with opaque codes before this lock. No original development version is a confirmatory arm.

Primary population is the 64 T1/T2 queries, equally weighted by type within session, then equally by session. Other types are prespecified diagnostic or guardrail populations. All 224 queries remain in analysis regardless of NULL success. No outcome-based exclusion, parameter change or successor run is permitted.

## 2. Frozen conditions

C0 is the public CC-007 `build_chat_context` at control commit `5ebda1ef4510c1806709039aeb66e6d79cedbbd8`, imported from the separate clean control worktree. Configuration is the deployed default: last 32 source episodes as additive continuity, CC80 dense/BM25 .8/.2, BM25 k1=1.2 and b=.75, ASPECT off, long-term budget 32,000 serialized characters. Frozen ranking and renderer/payload equality were established across 4,355 prior groups with zero mismatches and zero new model calls.

C1 uses the same sources, vectors, baseline scores, recency exclusion, packer and renderer. The frozen development `temporal.py` attempts interpretation on every query: exact quoted-name matching, strict before/after anchor bounds, latest/current subject order, and two named duration endpoints. It adds the unique anchor to anchored candidates. Multiple temporal clauses, absent subjects, ambiguous anchors and unsupported forms fall back byte-identically to C0. Temporal candidates are packed at 8,000 characters, then admitted temporal records precede baseline CC80 records in a final 32,000-character carried pack. Displacement is permitted. The code hashes in `registration_inputs.json` are authoritative; no learned detector or extra route is introduced.

Both arms retain identical recent continuity. This is a matched-character-allowance comparison, not equal token expenditure. Exact serialized prompt tokens, including instructions and query, are audited against the common 65,536-token reader limit with 8,192 output tokens reserved. Neither arm may shift or truncate context. Oversize records are handled only by the carried packer. No new packer or renderer is introduced.

ORACLE renders only the source episodes in the manifest's sufficient set, in source order, using the same source renderer and reader template. It is a gold-only reference, not a reasoning ceiling or equal-length competitor. NULL uses the same reader template's empty-memory section. N1 ORACLE is empty and identical to NULL. The current manifests contain one sufficient set per answerable query; no alternative carriers are intentionally planted. Check for accidental alternatives before inference and fail the instrument on ambiguity.

Generate all four logical arms for every query and seed. Identical full prompt bytes for the same seed share one persisted response, including identical C0/C1 fallback prompts and N1 ORACLE/NULL. Record aliases explicitly; they are paired common observations, never additional independent samples.

## 3. Runtime and schedule

Reader artifact SHA-256: `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372` (local Qwen3.8-27B-UD-Q4_K_XL). Server launcher hash: `125e0938a280cba46c803a60178e51826203e030abacce03367a22108720f7ac`. Record loaded runtime libraries, `/props`, build information, command, process identity and explicit CUDA0 selection; the launcher hash alone does not identify every dependency. Child CUDA library paths are the development-proven local v13.2 bin/x64 and v12.6 bin directories. One slot, 65,536 context, Q8 K/V, flash attention, no context shift, no speculative decoding.

Reader prompt is the unchanged frozen HH-001 `render_reader_prompt` plus `\n<think>\n</think>\n`. Five seed replicates per query-arm: 5005, 5006, 5007, 5008, 5009. Temperature .6, top_p .95, top_k 20, min_p 0, repetition penalty 1, presence penalty 0, no streaming, cache_prompt true, n_predict 8192, reasoning_format none. Prefix reuse passed three cold/warm development comparisons; it remains an execution-state limitation rather than a claim of arbitrary-state determinism.

Logical maximum: 4,480 reader responses (224 x 4 x 5); physical calls are fewer through exact prompt/seed aliases. Visit sessions in seed order and types T1,T2,T3,T4,M1,M2,N1. Rotate arm order C0,C1,ORACLE,NULL by session index modulo four; run the five seeds consecutively for each unique prompt. Prefix replay gate: execute the maximum-token confirmatory prompt twice at seed 5005 before the full schedule, persist both, require identical complete outputs; those calibration outputs are not scored or reused as schedule outputs. No other extra generation is authorized.

Embedding artifact SHA: `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`. Use carried CPU `PinnedEmbedder`, one text per call, n_ctx512, one thread per worker. Up to eight independent workers; assert identical worker sentinel vectors and persist every text-to-float32 association with file/content hashes. No batch-call substitution or confirmatory cache miss during prompt replay. Record call count, worker count, CPU and elapsed time. Mechanism cannot import corpus authoring or label/scorer modules.

## 4. Evidence and answer measurement

Persist source/probe/measurement manifests separately and seal their hashes before retrieval. Record full ranks and scores, parse/anchor/filter trace, temporal admission, baseline and final delivered IDs, pack rejections, final prompts and hashes, exact tokens and latency. Compute any and complete supporting-span presence separately at candidate, packed and reader-visible stages. Presence is checked against HTML-escaped source text inside the serialized prompt, not merely source IDs. Whole records are emitted by the carried renderer; detect any prompt truncation independently from completeness.

Primary outcome: final-answer factual correctness, averaged over five seed replicates within query, two primary queries within session, and 32 sessions. Completeness is a prior gate: natural eos before the registered cap, nonempty final output, no open reasoning block and no context truncation. A failed/missing/truncated response stops before scoring; persist it and report instrument failure. Network failures without a returned payload also stop; no automatic outcome-dependent retry or cap extension.

All answers concern opaque identifiers, an integer duration, or appropriate absence. Mechanical scoring is allowed only for unambiguous surfaces: a bare quoted/unquoted registered identifier with optional final punctuation; an integer with optional `day`/`days`; or the exact case-insensitive `I don't know` with optional apostrophe normalization and final punctuation. A different bare identifier or integer is incorrect; explicit abstention is incorrect on answerable queries and correct on N1. Blank final text is always zero, never abstention. No substring-only credit or reasoning-block credit. Preserve the parsed value and rationale for every score.

Any other surface is `NEEDS_ADJUDICATION`, not an automatic zero and not a silently excluded item. Create a blinded packet containing query, reference, response and rubric, without arm or retrieval data. If AI judgment is needed, the standing scoring protocol applies: three calibrated blind passes, a planted reasoning-only NO_ANSWER sentinel, disagreement triggers and a deterministic human audit of at least 20% of that judgment-based population. Human adjudication is required for conflicts and ambiguous factual sufficiency; no agent may claim to be the human reviewer. Without required adjudication, the study remains pending and no final positive/negative reader disposition is issued. A fully mechanical population needs no AI-rater calibration or human judgment to interpret bare symbols; this exception does not exempt ambiguous surfaces.

Scores must be committed before mechanism/outcome unsealing. The scoring program reads only sealed blind surfaces and rubric references, not retrieval traces or arm mapping. Duplicate identical query/reference/response surfaces may share a score with aliases retained.

## 5. Analysis and numerical dispositions

Calculate per-session primary correctness difference d_s = C1-C0, averaging the ten primary query-replicate outcomes within that session. Primary directional test is a paired session-level sign-flip randomization of the mean difference, 100,000 draws with RNG seed 93001 and plus-one p correction, one-sided for improvement. Report 95% paired session bootstrap intervals with 10,000 draws, RNG seed 93002. Resample whole sessions with all their queries and seed replicates together. Also report reverse-direction p for descriptive regression characterization, not a second positive hypothesis. Exact zero differences produce p=1. No seed-by-item independence assumption and no equivalence claim from nonsignificance.

Only this reader contrast is confirmatory, so no additional positive hypothesis family is tested. Delivery, type effects, ORACLE and NULL are descriptive with intervals and denominators. For each arm's complete-evidence subset, compare ORACLE on the identical item/replicate set; also report the common C0/C1 complete subset and full-population ORACLE separately. Do not compare different selected subsets as a causal decomposition.

Decision precedence:

1. INSTRUMENT_FAILURE or PENDING_ADJUDICATION if the corresponding gate fails or remains unresolved; no mechanism verdict.
2. REGRESSES if primary mean difference is <= -.025, or observed T3/T4/M1/M2 accuracy difference is below -.05, or observed N1 abstention difference is below -.05. Report intervals; this disposition is the registered observed-harm rule, not proof of population harm.
3. D1 WORKS if primary mean difference >= .10 and one-sided p <= .05, primary complete-evidence difference >= 0, and both above harm guardrails pass.
4. D2 CARRIES_SIGNAL if primary mean difference >= .025 and p <= .10, primary complete-evidence difference >= 0, and guardrails pass, but D1 does not.
5. Otherwise NO_DEMONSTRATED_BENEFIT / CHARACTERIZED, with uncertainty. This is not equivalence or evidence that temporal retrieval cannot work.

The .10 practical bar means one extra correct primary answer per ten; .025 means one per forty and warrants at most a separately authorized successor. N=32 session units can resolve large consistent effects; it is not promised to detect every .025 or .10 effect. Reachability fixtures must prove both positive tiers and negative outcomes: seven session gains of .5 with 25 ties yield mean .109375 with ideal sign p .0078125; four such gains yield .0625 and ideal p .0625. Both pass their respective tiers under zero guardrail harm. Negative fixtures reverse signs; all ties cannot pass. Report actual Monte Carlo outputs for these fixtures before confirmatory inference.

## 6. Preflight and enforced ordering

Part 1 evidence is committed: frozen input inventory and 4,355-group parity; six pure public-function fixtures through 1,000 sources; original and repaired development populations; cross-worker embedding identity; 12 short CPU/GPU probes; 37 long-prompt completeness/prefix checks; six cold/warm prefix checks. Runtime outputs were not scored. Ten development invariants pass. These establish feasibility, not confirmatory outcomes.

Part 2 gates, implemented after this registration and before full inference:

- PF1: verify every registered hash, count 32 sessions/224 queries/4,480 unique source episodes, required source spans and chronology, no future or assistant-only answers, opaque values and unique latest/before targets. Seal inputs and vectors.
- PF2: verify clean frozen control import paths, registered config, route decision table, explicit GPU/device/slot/speculation properties, and tokenized actual prompt lengths. Record full candidate/packing distributions without exposing correctness to human outcome reviewers.
- PF3: registration ancestor and unchanged hash checks; input seal then prompt/gate commit then two-call prefix gate then full reader completeness then blind scores commit then mapping/mechanism unseal. Prove out-of-order invocation fails. Registration commit contains no new implementation files.
- PF4: execute the numerical reachability fixtures above, positive/negative evidence-presence fixtures and real nonempty supported-treatment population. At least one C0/C1 selected set must differ, not merely order; otherwise instrument failure before live inference. Do not gate on confirmatory treatment benefit or baseline correctness.
- PF5: hash-based source and payload comparisons; aliases explicit and counts stable under ID regeneration.
- PF6: committed frozen 4,355-group parity plus exact current C0 prompt construction from the isolated prior implementation, no flag-disabled control.
- PF7: repeated pure-call equality and new latest-source continuity check; no source mutation or probe writeback. This does not certify historical runner feedback.
- PF8: passing 35-call snapshot ablation plus two maximum-prompt repeats on 140-source development histories, and new maximum confirmatory prefix gate. No evolving 120-turn conversation is run or claimed.
- PF9: audit false passes/failures for source presence versus span survival, easy-subset conditioning, saturated availability, exact-name grammar, templated holdout, alias independence, short completion versus correctness, char/token mismatch and rare harms missed by observed guardrails. Accepted residuals remain in the report.
- PF10: all four live reader/reference conditions and registered scoring/analysis required for a reader verdict; no availability-only adoption.

Required safeguards: hash and count assertions, tested corpus/rubric import prohibition and intentional leakage sentinel, no carried code diffs, deterministic prompt reconstruction, exact budget and nontruncation checks, immediate output persistence, NO_ANSWER score sentinel, and explicit pending-adjudication behavior. Failures stop the gated stage and are reported as instrument or mechanism failures specifically. Any correction to this locked design requires a standalone amendment with its trigger, exclusions and authorization; no silent edits.

## 7. Deliverables and limits

Commit sources, vector manifests/cache, prompt/mapping seals, gates, all persisted responses, blind scores/rationales, pending packets if any, per-session and per-type metrics, complete-evidence and displacement traces, costs, and final report carrying the registration commit. Update README, AGENTS digest (under 400 characters), memory, and ERRATA only if a published prior number changes. Open a study PR; do not merge or adopt automatically.

Interpret failures narrowly. A gold-only success with a delivered-context failure is consistent with context sensitivity, not proof of a particular reasoning defect. Missing evidence and wrong answers may coexist with reader limitations. Low multi-hop recall is not guaranteed by hidden bridge names; in development those probes were fully covered. Positive results here would establish only this restricted synthetic instance-family result with this local reader and deployed character budget.
