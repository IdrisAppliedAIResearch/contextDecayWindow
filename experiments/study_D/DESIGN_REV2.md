# Study D — Temporal Retrieval and Evidence-to-Answer Attribution

**Revision:** 2, 2026-09-05  
**Target:** `IdrisAppliedAIResearch/contextDecayWindow`  
**Status:** DESIGN DRAFT. Not preregistered, not runnable.  
**Source:** `study-D-temporal-multihop-design.md`; that original remains unchanged.  
**Authorization at this stage:** revise the design. This document does not authorize implementation, inference, opening a sealed evaluation set, or adoption.

## 0. Question and scope

Does a deterministic temporal retrieval route improve complete evidence delivery and answer correctness relative to a frozen baseline under the same context budget? Where answers fail, distinguish evidence exclusion from reader failure with sufficient evidence.

The study introduces one component: a temporal retrieval route, including its deterministic query interpretation and budgeted merge. It does not introduce a constraint register, learned detector, supersession index, iterative retrieval, or new memory formation policy. Multi-hop probes characterize existing delivery limitations; they do not test a multi-hop treatment.

Evidence availability and answer correctness are separate outcomes. A gold-only reference helps characterize reader performance but is neither a guaranteed ceiling nor a definitive test of reasoning. Conclusions remain conditional on the corpus, baseline, reader, prompt, budget, and execution settings.

## 1. Conditions and frozen comparison

| ID | Condition | Definition |
|---|---|---|
| C0 | Frozen baseline | Exact prior implementation, configuration, candidate eligibility, packing, and rendering identified before lock. No historical tier name substitutes for behavioral verification. |
| C1 | Temporal allocation | Same store and baseline retrieval computation, plus the deterministic temporal route. Candidates merge under a registered policy and the same total context allowance as C0. Displacement is permitted and measured. |
| ORACLE | Gold-only reference | Reader receives source episodes constituting a registered sufficient evidence set, without answer labels or measurement annotations. Same reader instructions and rendering conventions. |
| NULL | Empty episodic context | Same reader instructions and query, with no episodic evidence. Measures answerability without that evidence, including guessing and prompt cues; it does not uniquely measure pretraining. |

A/B anchors and C3 constraint formation are removed. C2 gating is deferred: a separate detector would require a separate scoped design. C1 attempts deterministic interpretation on every query. Unsupported or ambiguous queries return no temporal candidates and must reproduce C0's final prompt exactly. This fallback is part of the component, not proof that interpretation has been removed from the comparison.

All conditions use the same frozen, pre-probe source snapshot for each item. Probe answers are not written back into later source snapshots. This isolates retrieval and reading from arm-dependent history growth; it does not establish closed-loop conversational endurance. Any stateful carried retrieval policy must have its snapshot and replay history specified identically across arms.

ORACLE runs for every item and every registered reader replicate. For absent-fact items, its evidence set is empty; label this explicitly and exclude these items from evidence-conditioned metrics. Register whether identical ORACLE/NULL prompts share persisted outputs or receive separate scheduled calls; do not count duplicated outputs as independent observations.

## 2. Budget and rendering contract

C0 and C1 receive the same maximum episodic context allowance, measured on the actual serialized prompt using a frozen tokenizer. The budget must account for all evidence wrappers, timestamps, and separators. System instructions, query, any continuity block, and generation reserve are separately counted and held constant. No hidden extra allowance is available to C1.

The exact allowance, temporal allocation, merge order, slack return, oversize-item handling, deduplication key, tie rules, and truncation policy are **OPEN before lock**. They require development evidence and author resolution; this revision supplies no arbitrary values.

The registered policy must expose both admitted and displaced evidence. More candidates do not imply more delivered information, and even retained baseline evidence can become harder for the reader to use. Actual context lengths can differ within the common cap and must be reported.

ORACLE is a diagnostic context intervention, not a budget-matched retrieval competitor. Its source rendering must fit the same maximum allowance; if any sufficient set cannot fit, resolve that instrument defect before lock. Its shorter length remains a limitation of causal interpretation.

## 3. Corpus and probe contract

Use a synthetic-planted corpus with independently auditable evidence. Separate development sessions from sealed confirmatory sessions, including checks for duplicated templates and content that could undermine separation. No confirmatory item may be selected or removed based on reader results.

Each item records, in the measurement-only manifest:

- stable item and session identifiers, content hashes, query, probe position, and eligible source snapshot;
- gold answer with accepted semantic equivalents, required evidence facts, and one or more sufficient evidence sets;
- source spans and their content hashes for every required fact, including explicit temporal support;
- alternative carriers, near-miss distractors, and why each distractor is insufficient or wrong;
- query type, time semantics, and scoring rubric.

All required facts must appear in scripted user content strictly before the probe. Mechanism code cannot access these labels. Preserve raw episodes; derived measurement annotations never replace them. Audit evidence sufficiency and answer uniqueness before lock, including conflicting or alternative valid interpretations.

| Type | Construction and interpretation |
|---|---|
| T1: anchored ordering | Resolve an event or conversational anchor and answer within an explicit before/after relation. Register strict versus inclusive bounds. |
| T2: conversational recency | Find the latest relevant assertion in the eligible conversation. Requires both relevance and ordering; failure does not uniquely identify a broken filter. |
| T3: supersession | Initial assertion and two revisions with unambiguous applicability; query asks current state as of the probe. Ordered revisions may suffice without a supersession schema. |
| T4: duration | Two events with explicit dates or timestamps and a defined interval convention. Requires endpoint evidence and arithmetic. |
| M1: two-hop bridge | Bridge entity absent from query surface, with both links planted. Absence of the name does not guarantee low semantic rank or retrieval impossibility. |
| M2: three-hop bridge | Three required links, with complete-evidence scoring. Characterization only. |
| N1: absent fact | Requested fact absent from the entire eligible source snapshot, with plausible distractors. Score appropriate abstention and unsupported assertions. |

R1 is deferred with the constraint-register study. Exact item counts, session counts, allocation, and probe positions are OPEN. Thirty items per type is not adopted as an automatic power guarantee.

### Time semantics

Conversation order, assertion/write time, and described event time are distinct fields. A later-written episode can describe an earlier event. The manifest states which timeline each query concerns. Event-time treatment may use only fields or text available to the mechanism, never measurement-only gold timestamps.

Ordinals support ordering but not elapsed duration. T4 may use explicit event dates in source text even if per-turn wall-clock was never captured. The Act One transcript alone does not supply per-episode elapsed times. Missing or conflicting anchors must produce the registered failure/fallback behavior, not invented dates.

## 4. Deterministic temporal route

No generative language-model call occurs inside retrieval. Any additional embedding calls, date parsing, and database operations count toward cost and latency.

Before lock, provide one authoritative executable decision table covering:

| Case | Required specification |
|---|---|
| Before/after anchor | Grammar, extracted subject and anchor spans, eligible anchor pool, time field, bound inclusivity, ranking, and ties. |
| Latest/current state | Subject relevance criterion, assertion ordering, and distinction between recency and explicit revision semantics. |
| Duration | Two-anchor parsing and candidate retrieval, handling of missing endpoints; arithmetic remains a reader task. |
| Multiple temporal clauses | Supported combinations and precedence; ambiguous or unsupported forms fall back. |
| Non-temporal/unsupported query | Empty temporal result and byte-identical C0 fallback. |
| Missing/ambiguous anchor | Frozen acceptance criterion and fallback, without consulting gold annotations. |

The grammar, lexicon, normalization, date handling, anchor ranking, acceptance criteria, candidate limits, and merge parameters are OPEN pending Part 1 exploration. There is no optional classifier and no freely extensible lexicon after lock. Specify which cases share behavior and which are deliberately unsupported. Report support coverage alongside accuracy so narrow grammar coverage cannot masquerade as general temporal competence.

## 5. Instrumentation and evidence measures

Persist the complete source snapshot identity, ordered candidate ranks and scores, temporal parse, anchor candidates and selected anchors, filter decisions, merge admissions, displacement, pack rejections, final ordered source spans, full serialized prompt and hash, exact token counts, stage latency, and model-call counts. Log truncation and stop reasons. Preserve raw reader outputs immediately, including reasoning fields and final-answer boundaries.

Gold-aware measurements run separately from mechanism code. Join by stable content identity. For each required fact, record candidate presence, packed presence, and presence in the actual reader-visible payload. An episode identifier alone is not evidence that its relevant span survived.

| Measure | Definition |
|---|---|
| Any evidence | At least one required supporting fact is present. |
| Complete evidence, R_all | At least one registered sufficient evidence set is fully present in the final prompt. |
| Candidate/packing recall | Corresponding any/complete measures before and after packing. |
| Accuracy | Rubric-correct final answer, per item and reader replicate. |
| Accuracy given R_all | Accuracy on the explicitly identified complete-evidence subset; report its denominator. |
| Abstention | Rubric-appropriate abstention on N1, distinct from an empty or truncated response. |
| Displacement | Baseline-delivered source spans and evidence lost in C1, alongside additions. |
| Cost | Actual context size distributions, stage latency distributions, and embedding/generative call counts. |

For missing evidence, report rank in the full eligible baseline scoring universe and exclusion stage. Ineligible evidence gets an exclusion reason rather than a fictitious rank. Report rank and size distributions jointly; distant ranks do not establish structural unreachability or prescribe iterative retrieval.

### Attribution limits

For each arm, compare its complete-evidence items against ORACLE on those exact items and paired replicate identifiers. Report the full-population ORACLE result separately. When contrasting arms' conditional metrics, show membership changes and their common complete-evidence subset; different selected subsets are not exchangeable.

- Incomplete evidence plus wrong answer: evidence delivery is insufficient; reader limitations may coexist.
- Complete evidence plus wrong answer: reader failure with labeled sufficient evidence; inspect rubric/sufficiency validity before attributing it to reasoning.
- Gold-only success plus delivered-context failure on the same item: consistent with sensitivity to context composition, ordering, or distraction; this study does not isolate those factors.
- Incomplete evidence plus correct answer: possible guessing, alternate support, or incomplete labeling; preserve and audit, without deleting the item after results.

These are diagnostic associations. Neither equality with ORACLE nor a conditional accuracy gap proves that retrieval is the sole bottleneck or cannot help further.

## 6. Hypotheses and disposition plan

The following are directional expectations to operationalize before lock, not already registered numerical predictions:

| ID | Expectation | Required evaluation |
|---|---|---|
| H1 | C1 improves T1/T2 complete delivery and answer use. | Paired C1-C0 differences; no gain or regression contradicts the direction. Register the primary aggregation and practical threshold. |
| H2 | Gains differ across T1-T4. | Prespecified between-type contrast if powered; otherwise descriptive. Do not infer an interaction from one significant and one nonsignificant result. |
| H3 | Supersession remains difficult. | Report T3 error rate and treatment effect separately. Improvement weakens the claim that explicit supersession structure is necessary on this corpus. |
| H4 | Multi-hop complete delivery is limited. | Report M1/M2 complete delivery, ranks, and missing links; no arbitrary impossibility claim or inherited 30/50% thresholds. |
| H5 | Temporal allocation may worsen absent-fact handling. | Paired N1 abstention and unsupported-answer differences, with a preregistered harm margin. |

Define two numbered positive dispositions before lock: D1 WORKS and D2 CARRIES_SIGNAL, each with exact effect bars, interval/test requirements, and N1 plus non-temporal regression guardrails. D2 must be explicitly weaker without being invented after results. Also define regression, inconclusive/no-demonstrated-benefit, and instrument-failure outcomes. Numerical values and decision precedence are OPEN.

No positive disposition follows from availability alone. Reader outcomes are required. A mechanism stop closes the tested rule/configuration; an instrument failure means the mechanism was not adequately tested. Neither automatically authorizes a successor, tuning, or adoption.

## 7. Statistical and scoring plan

The confirmatory contrast is C1 versus C0. ORACLE and NULL are diagnostic references. Freeze the primary outcome population and weighting, secondary outcomes, confidence level, multiplicity policy, effect thresholds, sample size justification, and exact estimator before registration. These statistical choices remain OPEN.

Pair conditions within item and reader replicate. Account for dependence among items sharing a session and among repeated outputs for an item. Do not apply ordinary McNemar to all seed-by-item rows as independent pairs. Select and document a session-aware paired analysis during design completion; specify handling of too few independent sessions and zero or empty subsets. A failure to reject a difference is not equivalence.

Use a fixed explicit seed list, identical model artifact and tokenizer hashes, prompt templates, decoding settings, generation cap, and scheduled serial execution. Exact replicate count and schedule are OPEN. Require byte-identical seeded prefix replay, server/build identity, `--parallel 1`, and no speculative decoding. Record run order; matched seeds alone do not establish comparable execution conditions.

Use mechanical grading where semantic equivalence can be registered precisely: units, numeric formatting, dates, negation, and conflicting extra claims must be covered. For judgment-based items, follow the repository scoring protocol: calibrated NO_ANSWER sentinel, three blind passes, per-score rationales, and registered human-adjudication triggers. Freeze human sample size/selection, agreement statistic and acceptance threshold, grader configuration, and adjudication policy before lock. Blank answers score zero, including N1; only content outside reasoning blocks is scoreable.

Persist and validate output completeness before judging. Register the handling of truncation, missing answers, failed calls, retries, and any common-cap continuation; no outcome-driven retries or cap changes. Scores for every arm must be committed before mechanism logs are unsealed to outcome reviewers. Preflight instrumentation tests use development fixtures; they do not open confirmatory mechanisms early.

NULL outcomes never trigger confirmatory item deletion. Investigate guessability on separate development material. Report confirmatory NULL results, including N1's expected abstention, and any label defects transparently under a registered audit policy.

## 8. Mandatory Preflight

Authority: repository `PREFLIGHT.md`, `AGENTS.md`, and `experiments/audits/scoring_integrity/PROTOCOL_scoring_integrity.md`. This section specifies deliverables; it does not claim they have been executed. All checks are PENDING.

### Part 1: empirical exploration before confirmatory lock

A separately scoped exploration plan must be authorized and committed before exploratory execution. Use development data to establish the frozen baseline's falsifiable behavioral identity, checking every named tier against observed behavior. Record distributions of candidate rank, source age, context occupancy, truncation, and delivered evidence. Demonstrate absorbing/degenerate behavior on a real trace at intended scale if a carried mechanism has feedback.

Characterize temporal interpretation coverage, wrong/missing anchors, assertion-versus-event-time errors, and budget contention on development traces. Include no-trigger, ambiguous-trigger, conflicting-date, duplicate, empty-result, oversize, and saturated-budget cases. Show both meaningful admission and possible displacement; an inert route cannot test the benefit question. Record findings with artifact hashes, without selecting parameters using sealed outcomes.

Resolve all OPEN fields using this evidence and explicit author decisions. Commit the completed design alone as the preregistration anchor before study implementation. Part 2 implementation checks must then pass before confirmatory execution; the design must already specify their tests, ordering, and failure consequences.

### Part 2: verification checklist

| Check | Required evidence before execution | Current status |
|---|---|---|
| PF1 Inputs | Hashes/counts/readability of corpus, splits, evidence manifests, model, configurations and prompts; all required facts predate probes. | PENDING |
| PF2 Identity | Committed baseline and route behavior traces; names agree with measured operations. | PENDING |
| PF3 Ordering | Enforced sequence: exploration, design lock, implementation, gates/ablation, inference completeness, blind scoring commit, mechanism unseal. Deliberate ordering violation must fail. | PENDING |
| PF4 Reachability | Both positive tiers and negative branches attainable at fixed counts/budgets; power justification and nonempty tested populations. | PENDING |
| PF5 Keys | Content-hash joins and equality; regenerated IDs cannot change comparison. | PENDING |
| PF6 Replay | Baseline reproduced from a prior checked-out control in a separate worktree by ordered identities and payload digests. | PENDING |
| PF7 Feedback | Real-scale state/absorbing-state proof for carried feedback; explicit evidence-based inapplicability only for stateless portions. | PENDING |
| PF8 Ablation | At least 35 turns before any 120-turn execution, plus scale-appropriate cases; state what short checks cannot detect. | PENDING |
| PF9 Surrogates | Audit every metric/gate for false pass and false failure, with positive/negative fixtures and accepted residuals. | PENDING |
| PF10 Reader | This study's frozen live reader protocol and decision bars; availability alone cannot pass the study. | PENDING |

Additional binding checks: exact serialized-budget assertions; sufficient-evidence span survival; no future-source leakage; gold-label access blocked by text search, import graph and a deliberate violation; unchanged carried subsystems; clean control worktree and recorded module paths; serial deterministic prefix replay; output persistence and completeness; blinded scorer calibration. Every verification report must name the executed test and commit SHA. Failed checks stop the gated stage with an instrument-versus-mechanism explanation.

PF9 must explicitly cover: episode present but supporting span absent; alternate evidence overlooked; high conditional accuracy caused by easy-subset selection; inert treatment counted as safety; tiny samples counted as equivalence; extra context mistaken for route quality; event/write-time confusion; abstention confused with missing output; automated agreement without grading validity; and unavailable or unreachable decision branches.

## 9. Lock checklist and deliverables

The following must be filled in the authoritative registration, not left to implementation defaults:

1. Baseline code/configuration/replay anchor and state snapshot semantics.
2. Corpus and split manifests, item/session counts and schedules, evidence annotations, time conventions.
3. Deterministic route decision table and all parsing, ranking, acceptance, merge, and budget parameters.
4. Reader artifact, tokenizer, prompts, seed list, replicate count, execution schedule and completeness policy.
5. Primary population/endpoint, weighting and estimator, dependence handling, multiplicity, power rationale, numerical disposition and harm bars.
6. Rubrics, graders, human audit and adjudication details, seal/unseal procedure.
7. Part 1 artifacts and explicit Part 2 test specifications, followed by passing execution reports before the run.

The report must include complete/any evidence at each stage, paired answer gains and losses, same-item ORACLE comparisons, NULL and N1 results, displacement and anchor-error distributions, cost distributions, all denominators, registered dispositions, deviations, and limits. Trace every reported number to committed artifacts. Close out through the repository report, README/digest, memory, errata when needed, logs and PR workflow.

## 10. Revision record

Revision 2 replaces binary retrieval/reasoning attribution with matched-item evidence/reader diagnostics; uses a common-budget allocation comparison; removes C2/C3 and A/B from this study; separates event and assertion time; requires sufficient evidence in serialized prompts; removes outcome-dependent NULL exclusions; replaces unsupported mechanism claims with scoped expectations; and adds explicit statistical, scoring and preflight requirements. Open choices remain visible rather than being silently assigned.
