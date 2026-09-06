# Study E draft — temporal ordering before an event

**Status: DESIGN DRAFT FOR REVIEW. Not preregistered, not runnable.**
**Date:** 2026-09-06. **Authorization:** draft the next design document only.
All numbers below are proposed design choices. Part 1 may change the draft; final parameters, corpus/generator hashes, scoring rubric and runtime must be committed in a design-only registration before confirmation implementation or generation. This document does not reopen Study D or authorize a DA fusion, deployment or successor run.

## 1. Question and motivation

Does ordering temporally eligible records from newest to oldest improve the reader's correctness on immediately-before questions compared with Study D's similarity ordering, at the same retrieval allowance?

Study D measured reader answers, not merely availability: its temporal arm scored 203/320 primary answers. Immediately-before scored 43/160. Complete evidence was delivered for only 16/32 before questions; even on those 16 questions, 37/80 reader answers were wrong. A saved-trace replay reproduced every temporal and final selection for all 32 before questions. In all 16 availability misses the anchor was delivered and the required update was eligible, but its whole record did not fit when considered. Target temporal ranks were 20–39; costs 693–703 chars against 292–323 remaining in the temporal allocation. This identifies a joint ordering/packing/budget boundary.

The asymmetry is explicit: Study D's latest route uses descending turn order; its before route filters by time but retains CC80 order. Study E tests changing that ordering. The motivating corpus always placed the required before-update at turn 44 and the meeting at 45; those positions must not carry into the confirmation design as fixed constants.

Sources: ../study_D/REPORT.md; ../probes/study_D_reader_address/TRACE_FINDINGS.md. The short address probe showed correct final answers on clear examples and an inconsistent missing-record response; it does not establish performance in long histories or justify a reasoning-prompt change here.

## 2. Hypothesis and exact intervention

Hypothesis: within the existing before-anchor candidate set, descending event order improves generated-answer correctness by prioritizing records nearer the queried state boundary.

**C0: frozen Study D C1**, including its temporal route. This is the current best tested temporal architecture, not Study D's plain CC80 baseline. Import from an isolated prior checkout pinned to commit 05ef90e2, with the original control dependency at 5ebda1ef4510c1806709039aeb66e6d79cedbbd8. Verify both clean and exact before use.

**C1: the same architecture with one ordering change.** For a query accepted by the existing before-anchor grammar, retain the identical unique anchor and identical eligible subject-record set. Keep the anchor first. Order remaining eligible records by descending turn_number, breaking ties by stable source content identity. Everything after that is unchanged. Unsupported, ambiguous, latest, duration and after queries must reproduce C0 exactly.

The treatment is **nearest-prior-record ordering**, not a state extractor. A qualifying record contains the exact quoted subject and precedes the anchor; it need not update the queried field. Do not add field extraction, validity intervals, supersession interpretation, a new detector, clause parsing, learned scores, or a hardcoded nearest gold carrier. These would be additional mechanisms.

Keep 8,000 serialized characters for temporal admissions; admitted records precede ordinary CC80 fill in the unchanged final 32,000-character retrieval pack. Keep identical additive latest-32 continuity. Preserve full episodes, renderer, deduplication, overflow skip policy, baseline ranking, embeddings and all source bytes. No DA compression or individual-message packing. Costs refer to the actual rendered retrieval block, not compressed wire bytes.

Changing the input ordering can change both selected membership and presentation order. The study attributes effects to this ordering policy as a whole; it does not separately identify presentation and membership effects.

## 3. Development and confirmation populations

**Development only:** all existing Study D sessions and their outcomes are exposed and cannot become confirmation evidence. Use them to establish behavioral identity, characterize admission and displacement distributions, test the new ordering and audit scorer failures. New development fixtures use seeds 93001–93004 and are also excluded. No live development schedule is authorized by this draft; Part 1 execution scope must be approved and frozen before running.

**Proposed confirmation:** 32 new randomized sessions, seeds 94001–94032; 140 source episodes each, snapshot 140; six questions per session. Four are immediately-before questions, one latest-setting guard question, and one absent-field question with a supported before operator. Five reader seeds per question-arm: 5005–5009. Four logical arms yield at most 3,840 answers; primary C0/C1 each has 640 generated answers over 128 questions, with 32 independent session units.

Build four separate subject histories in each session. Each contributes one before question under one condition:

1. **Straight revision:** explicit successive updates, with the final prior update defining the answer.
2. **Later irrelevant mention:** intervening records mention the subject but update a different field or make no update.
3. **Future-effective announcement:** a pre-meeting record announces a change effective after the meeting; the earlier currently effective value remains the answer.
4. **Proposal or quotation:** a nearer record proposes an unaccepted change or quotes an obsolete value while explicitly retaining the current setting.

The latter three test the difference between the nearest mention and the effective state. They are included in the primary population with equal weight, not removed when difficult. All four use supported exact-quoted subject/anchor syntax; this tests temporal ordering, not natural-language detector transfer.

The latest guard refers to a fifth independent subject with explicit revisions only. The absent-field guard concerns a sixth known subject whose source mentions activate the existing before route but never establish the queried field. Its gold answer is canonical abstention. It must genuinely admit temporal candidates; mere fallback cannot certify absence safety. Include only records that explicitly support absence of information, not a hidden positive answer.

Use everyday roles and values (delivery address, room, approved contact, equipment location), assigning values randomly from balanced sets. Avoid ordinal-bearing answers. Vary question wording only inside the frozen supported grammar and balance each wording across conditions. Randomize anchor placement, intervening gaps and distractor locations. Require every source needed for an answer before turn 109, outside continuity; no fixed source turn defines a gold answer. Set the actual placement ranges, template inventory, value vocabulary and randomization algorithm after Part 1 and before confirmation lock. They are OPEN in this draft.

Do not reveal or generate confirmation instances during development. Freeze the generator and measurement code before opening seeds. Confirmation may test prospective, outcome-blind input validity but cannot select sessions based on control errors or treatment gains. Include every valid preregistered question. A malformed instance stops the instrument; it is not silently replaced by a new seed.

This remains synthetic instance-family confirmation. It does not establish naturalistic language transfer. Randomized everyday names improve legibility, not ecological validity.

## 4. Reader conditions and references

C0/C1 share the unchanged Study D HH-001 prompt, empty think suffix, reader and generation settings. No request for reasoning or justification. Inspect and hash actual prompts before inference. The template is not a verified Mem0-paper prompt; no Mem0 comparison is made.

ORACLE receives a gold-only sufficient set in source order, using the carried renderer. For state challenges, the set must include the earlier effective value, the event boundary and the qualification that makes a later mention non-governing where necessary. It is a diagnostic reference, not a ceiling. NULL receives the carried empty-memory section. Reference conditions must also be generated and scored; no NULL-based exclusions.

Reuse the Study D Qwen3.8 reader artifact SHA bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372 and launcher SHA 125e0938a280cba46c803a60178e51826203e030abacce03367a22108720f7ac; verify loaded runtime libraries, CUDA device, server properties and embedding identity separately. One slot, 65,536 context, 8,192 output tokens reserved, no context shifting or speculative decoding; temperature .6, top_p .95, top_k20, min_p0, repeat_penalty1, presence_penalty0. Preserve the proven cache_prompt behavior and record execution state. Hash and replay maximum-prompt prefix before the scored schedule.

Rotate arm order by session index; session seed order and question-condition order fixed at registration. Identical full prompt/seed pairs may share one persisted response with explicit aliases, but different references must retain distinct score identities. Preserve five reader seeds within each session; do not treat them as five independent sessions.

Persist every returned raw response immediately. Any missing, empty, truncated, capped or unfinished-reasoning response stops scoring of the confirmatory population. Preserve an uncertain request journal; no automatic rerun or cap increase. Stop rules and any completion repair must be explicitly registered before inference.

## 5. Scoring settled before lock

Primary measurement is correctness of the generated final answer against the source-established active value at the anchor. Evidence presence is a separate diagnostic and cannot establish success.

Every question has a prospectively written reference, sufficient supporting spans and a falsifiable state rationale. Source gold is produced from an explicit event-state ledger in measurement code, and independently checked against rendered source text. The retrieval mechanism cannot import that ledger or references. Review criterion meaning before affected reader answers are opened.

Mechanical scoring: exact normalized single value from the frozen answer vocabulary or canonical abstention; normalize only the enumerated whitespace, quoting, case and punctuation rules. Never substring-match an explanation. Never infer correctness from fluent justification. Blank is zero and also trips the completeness gate. Noncanonical or contradictory responses remain pending, not zero and not excluded.

**Open decision before registration:** adopt a complete rubric for noncanonical final answers, including explicit self-corrections, extra explanations and competing asserted values. Prefer direct blinded human adjudication of exceptions; if AI judgment is used, freeze three calibrated blind passes, the reasoning-only NO_ANSWER sentinel, disagreement triggers and a deterministic >=20% human audit before inference. The final design must name reviewer responsibility and provide a legible packet. A single-agent waiver is not assumed from Study D's case-specific authorization. Unresolved review blocks a reader disposition; no post-run convenience change is part of this draft.

Commit completeness and reference-presence validation, then all arms' scores and adjudications, before opening mechanism/outcome comparisons. Original score records remain immutable; authorized corrections require additive provenance.

## 6. Proposed analysis and dispositions

Primary contrast is C1 minus C0 final-answer accuracy across the four before conditions. Average five seeds within question, four conditions within session, then 32 sessions equally. Fixed sample; no early efficacy stopping or extension after outcomes. Latest and absent questions are excluded from the primary average and retained as guardrails.

Use paired session sign-flip randomization: 100,000 draws, seed 95001, one-sided improvement, plus-one correction. Report paired session bootstrap 95% interval, 10,000 draws, seed 95002. All resampling keeps each session's questions and reader replicates together. Report per-condition effects descriptively and reverse-direction p descriptively; no separate positive claims from favorable strata. These tests support inference over this randomized generator population only.

Proposed decision precedence, to verify for reachability before lock:

1. INSTRUMENT_FAILURE or PENDING_ADJUDICATION: no mechanism success/failure verdict.
2. REGRESSES if primary mean difference <= -.025, or any of the three challenge-condition differences is < -.05, or absent-field abstention difference is < -.05. These are observed-harm dispositions, not proof of population harm. Latest outputs should be byte-identical aliases; a mismatch is an implementation failure, not statistical regression.
3. D1_WORKS if primary gain >= .10, one-sided p <= .05, and harm guards pass.
4. D2_CARRIES_SIGNAL if primary gain >= .025, p <= .10 and guards pass, but D1 is not met.
5. Otherwise NO_DEMONSTRATED_BENEFIT / CHARACTERIZED. No equivalence claim.

Availability is not an extra success gate: a reader improvement can occur through context organization even if evidence counts tie. Conversely, recovering every carrier cannot pass D1 or D2 without reader improvement. Report any/complete source-span survival at candidate, temporal admission, final pack and actual reader prompt. Report final correct/wrong x complete/incomplete tables, displacement, ranks, exact bytes/tokens and costs. Compare ORACLE on identical complete-evidence subsets; do not causally compare different selected subsets.

Reachability must include positive, signal, negative, all-tie and each harmful challenge fixture. For example, seven session gains of .5 with 25 ties produce mean .109375 and ideal sign p .0078125; four such gains produce .0625 and ideal p .0625. Those positive fixtures must coexist with nonnegative challenge/absence outcomes, rather than being impossible scores for this population. No power guarantee for small effects at N=32; report design limitations before lock.

## 7. Preflight — binding and currently OPEN

### Part 1: observe before confirmation design lock

Use a separately authorized development stage to run the ordering rule on real Study D histories. One falsifiable identity sentence: C1 preserves C0's anchor and eligible set, orders the latter newest-first for accepted before queries, and otherwise produces identical context. Verify that identity against actual traces, not just source code.

Characterize all existing T1 questions, including complete and incomplete controls: candidate order, gold rank (measurement only), admitted ranks, costs, lost/gained identities and prompt ordering. Report distributions and degenerate cases: missing/ambiguous anchor, absent subject, all records too large, all already recent, no prior record, repeated mentions, and future-effective/proposal fixtures. No online feedback exists in this pure function; demonstrate repeated-call equality and untouched sources instead of inventing an endurance claim.

Before confirmation lock, characterize the new development templates for saturation, accidental answer shortcuts, source clarity and whether nearest mention can differ from active update. A state challenge must actually be possible. Do not select confirmation instances by outcome. If development shows the treatment is inert or the instrument cannot represent harms, return the draft for revision rather than run it anyway.

### Part 2: explicit evidence required before scored confirmation

| Check | Required artifact / test | Draft status |
|---|---|---|
| PF1 inputs | Source/generator/runtime hashes, 32 sessions/192 queries/4,480 episodes, gold-before-probe and outside-continuity checks, independently checked ledger, no alternative carriers | OPEN |
| PF2 behavior | Exact eligible-set equality, before-only order difference, unchanged other routes; full distributions from Part 1; loaded runtime identity | OPEN |
| PF3 ordering | Design-only registration SHA; frozen input seal; prompt/gate commit; prefix completeness; full reader completeness; blind scores commit; then unsealing, with out-of-order invocation tests | OPEN |
| PF4 achievable bars | Executed positive/signal/harm/tie fixtures; nonempty supported changed treatment; active absence intervention; no gate on observed confirmation benefit | OPEN |
| PF5 keys | Stable content identities, prompt/seed aliases separate from reference-specific score aliases, duplicate and regeneration audit | OPEN |
| PF6 reproduction | Isolated prior checkout reproduces all 224 saved Study D C1 prompts by digest and existing selected identities; new treatment gated separately | OPEN |
| PF7 state | Repeated pure-call identity, untouched source hashes, no response writeback; no feedback/endurance claim | OPEN |
| PF8 scale | Complete development prompts at intended 140-source scale, maximum-token prefix replay, explicit limit that snapshots do not test evolving conversation | OPEN |
| PF9 surrogate | Reader endpoint, active absent-field treatment, wrong-nearest-mention challenges, source-span survival, no fixed-turn shortcuts, matched renderer costs, complete scoring workflow | OPEN |
| PF10 reader | All arms generated; final-answer scoring and session-level decision enforced; no availability-only success | OPEN |

No checked box counts without an executed artifact and commit. Preflight labels must distinguish instrument defects from mechanism limitations. A first missing control, invariant violation or undefined scoring procedure blocks lock or run at its proper stage.

## 8. Deliverables and interpretation

Produce a final registered design, frozen development record, new source and measurement manifests, prompt seals, full traces and raw reader outputs, blind scoring/audit artifacts, complete report and separate study PR. Update README, <=400-character AGENTS digest and memory; ERRATA only if a prior published number changes. Do not merge or adopt automatically.

A positive finding means ordering prior records closer to the event improved this reader under this generator and prompt. It does not establish state extraction, natural-language anchor resolution, general multi-hop reasoning, DA fusion, or successful continual learning. A negative finding closes this ordering policy under this instrument, not temporal retrieval as a whole.

If temporal ordering helps, DA packing remains a separate hypothesis. If evidence rises without reader gains, report that directly. If challenges regress, do not add a field-aware parser to rescue this study after results. A separately registered successor can address the specific exposed failure.

## 9. Decisions required before moving beyond this draft

- Approve the six-question population and equal-weight primary/challenge structure.
- Complete Part 1 under its own bounded execution authorization.
- Freeze source placement ranges, vocabulary, templates and independent source-state validation.
- Resolve noncanonical-answer adjudication and reviewer responsibility prospectively.
- Verify proposed sample size, numerical bars, harm thresholds and attainable fixtures.
- Pin all implementation and runtime dependencies; commit final registration before confirmation implementation or generation.

No action beyond drafting is authorized by this document.
