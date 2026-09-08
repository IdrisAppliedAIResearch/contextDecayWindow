# One-call retrieval planning: implementation design

**Status: DRAFT FOR REVIEW. Not preregistered, implemented, or runnable.**

The user requested this design after reviewing the limitations of the deterministic contextual-memory arc. This authorizes document preparation, not inference. The completed unified-memory subset and its registrations remain unchanged; the full-corpus run stays stopped.

This introduces the program's first **generative call inside the memory retrieval path**. Earlier answering and evaluation calls already existed. The resulting treatment must be described as **LLM-assisted retrieval with deterministic execution**, never fully deterministic memory.

## 1. Decision and hypothesis

Add one query-time planning call between the existing deterministic retrieval and final evidence assembly. It examines the question and initially retrieved original records, identifies missing evidence obligations or ambiguous event connections, and emits a bounded set of searches. Deterministic code validates and executes those searches, unions their source records with the original selection, and presents the evidence chronologically to the unchanged final reader.

The hypothesis is specific: **interpretation of the question and available clues can formulate useful follow-up retrieval that the frozen deterministic architecture does not perform.** A valid plan or plausible anchor is not success; the additional retrieval must improve answers sufficiently to justify the call and added context.

The planner cannot answer the user, write memory, invent source records, discard evidence, certify completeness, or run another planning iteration. It can express uncertainty. There is one architecture design here, followed by one separate experimental registration after development and preflight.

## 2. What motivates this intervention

The completed exploratory comparison scored direct C0 384/566 versus combined C1 399/566, with27 gains and12 losses. Its same-model scoring has documented date and list-completeness inconsistencies. These counts are contextual evidence, not a trustworthy small effect to optimize against or a success threshold for this successor.

The [post-result diagnostic](../../unified_contextual_memory/PROBE_001_REPORT.md), raw a1e8d8a2, reproduced566 selections exactly.52 of56 mapped missing annotated carriers had an eligible edge but failed composed activation. Most additional admissions were contextual seeds, while traversal-only additions had a median of3 per question. Some generic reference cues were semantically weak despite passing their similarity threshold. The limitations are both numerical continuation and interpretation; an LLM is not presumed to solve both.

Earlier chronology-only and explicit-anchor prefix findings remain useful, but they do not demonstrate natural event binding. Both new comparison arms retain chronology. The planner's ability to produce useful new searches is the intended new variable; chronology, captions, reader reasoning, and the original path floor are not changed simultaneously.

## 3. End-to-end architecture

```text
Question + eligible source snapshot
          |
Frozen deterministic contextual retrieval
          |
Initial original-source evidence S0
          |
ONE planner LLM call: obligations, candidate connections, follow-up queries
          |
Strict deterministic validation
          |
Independent-pair searches over the same eligible source snapshot
          |
Union S0 + qualifying original records; deduplicate; chronological rendering
          |
ONE unchanged final reader call
```

Normal treatment cost is two generative calls per question: one planner and one answer. The control makes one answer call. Measurement judges remain outside this count and outside the mechanism. Frozen embedding calls for generated search text are reported separately, not concealed as zero-compute retrieval.

The planner has no tool access. Its output is data consumed by a narrow executor. It never reads gold answers, evidence annotations, scores, judge feedback, hidden future records, or a full transcript unavailable to the control. Source excerpts may contain instructions; the planner prompt treats them as quoted conversation data, not executable requests.

## 4. Initial evidence and frozen comparator

Use the completed **C1 combined deterministic configuration** as the proposed initial retrieval S0 and primary comparator. This directly tests adding a call to the current architecture. Freeze it in a clean separate worktree before implementation; choose and record the exact commit after reviewing this document. Its behavior must reproduce existing selected IDs and rendered payloads exactly.

Preserve its independent direct threshold.48, contextual/support/reference thresholds, max-product floor.48, source schema, supplied captions, contextual-vector provenance, reference rules, knowledge horizon and chronological renderer. No recent32 block or retrieval character/item cap is added. Its known shortcomings remain present in both arms; repairing them is a separate intervention.

The historical direct C0 can be reported as background, with its exposure/settings qualifications. It is not a third live arm in the first experiment. Existing answers are not automatically substituted for a new contemporaneous comparison: model/server scheduling variation and scoring repair require a frozen explicit reuse policy before lock.

The planner receives the original question and S0 with immutable record IDs, dialogue IDs, dates and speakers. It does not receive hidden similarity rankings, annotations or intermediate judge explanations. Score-free chronological input keeps its task focused on the available conversation. If this input cannot fit, fail the technical gate; do not silently truncate, summarize or replace S0 with the whole corpus.

## 5. Planner contract

The planner addresses four questions in one call:

1. What separate evidence is needed to answer this question?
2. Which retrieved records may concern the same event or reference, and what competing interpretations exist?
3. What information is absent or unresolved in the visible evidence?
4. Which short searches could retrieve that information?

“Anchor” is a candidate source event or mention, not an authoritative truth. Candidate connection status is `possible`, `supported_in_visible_text`, or `unresolved`; the latter two do not grant deletion or temporal-cutoff authority. The first implementation does not act on a claimed unique identity as a filter.

Proposed typed response:

```json
{
  "schema_version": 1,
  "obligations": [
    {"id": "o1", "description": "Identify the employer associated with the accepted offer"}
  ],
  "connections": [
    {
      "source_ids": ["record_a", "record_b"],
      "status": "possible",
      "description": "The interview may be the antecedent of the offer"
    }
  ],
  "searches": [
    {
      "obligation_id": "o1",
      "query": "Northstar job offer acceptance rejection",
      "basis": "source",
      "source_ids": ["record_a", "record_b"]
    }
  ],
  "remaining_uncertainties": ["Cedar is also a possible employer"]
}
```

This schema is an implementation proposal, not a locked parser. The source IDs in a plan must come from S0. A search can instead use `basis: question` and an empty source list for an obligation explicit in the original query. This permits useful reformulation when S0 is weak without requiring a fabricated citation. Exact bounds, field types and rejection behavior must be frozen in development.

The initial proposed bound is **at most four searches**, one planning round, with each query at most96 encoder tokens and planner output at most2,048 tokens. These limit planner/executor work, not the number or length of qualifying evidence records. They are explicit provisional engineering choices to verify in Part1, not calibrated semantic-completeness limits. Do not silently raise them after seeing benchmark outcomes. Zero searches is valid; the planner can conclude that no grounded follow-up is available without claiming that all evidence was found.

No answer field, free-form chain-of-thought request, numerical confidence, executable tool name, external URL, arbitrary filter expression or access path is accepted. Brief descriptions support audits; generated explanations and candidate links are **not supplied to the final reader**. This first comparison tests source retrieval, not giving the answering model an extra reasoning draft. Raw planner outputs remain available for later diagnosis.

## 6. Deterministic executor

Validate JSON against the frozen schema; reject extra fields, unknown citations, duplicate obligation IDs, invalid references, oversized output and excess search count. Reject the whole malformed plan rather than selecting an advantageous subset of it. Preserve raw output and the validation result. Syntax/provenance checks do not establish semantic correctness; that remains an explicit audit target.

Canonicalize search text using a frozen minimal whitespace rule, deduplicate exact queries and embed each once with the existing frozen independent encoder. Do not use planner prose to create new memory records. Cache each generated query by exact text, encoder/runtime specification and vector hash; generation and cache provenance remain inspectable.

For each valid query, select full original source pairs with independent cosine >=.48 from the **same eligible source snapshot**. This threshold is deliberately carried as a fixed first executor proposal, not assumed universally calibrated for generated queries. Characterize its behavior before registration. Do not multiply this score by the planner's confidence or by the original query score: there is no meaningful calibrated planner confidence to use.

Union qualifying pairs with S0, preserve all S0 records, deduplicate by immutable ID and render chronologically using the identical existing renderer. Do not rerun contextual traversal from these additions, follow arbitrary neighbors, use an anchor to crop the timeline, or perform another planning call. That keeps the effect of one planning step inspectable.

The final reader sees only the original question and assembled original evidence. Added records are not labelled “confirmed by planner.” A union that equals S0 is a no-op; record it, and use the locked identical-prompt reuse policy symmetrically across arms. Conditional success among plans that changed retrieval is diagnostic; primary analysis includes all scheduled questions, including planner no-ops and schema failures.

## 7. Ambiguity and failure semantics

With two interviews and an unspecified acceptance, the planner may request offer/acceptance evidence for both employers. The executor preserves both candidates if their searches qualify. The final reader can answer only if the assembled source establishes the connection; otherwise it should express uncertainty under the common reader contract. The planner is not asked to guess which employer “must” be intended.

Later retrospective testimony can clarify an earlier event, so inferred event dates cannot become an automatic knowledge-horizon cutoff. Eligibility comes from the caller's source snapshot. Proposed updates, conditional statements and actual changes remain source evidence for the final reader; candidate descriptions do not rewrite them into facts.

For a well-delivered but schema-invalid planner response, the proposed operational fallback is S0, with no retry or JSON-repair call. Count this as a planner failure and include the resulting control-equivalent evidence in the primary intention-to-treat population. A semantic guess can pass the schema; candidate-preserving, additive execution contains its authority but cannot prevent irrelevant additions.

Transport failure, uncertain persistence, model exit, context overflow or truncation remains an instrument failure requiring a preserved stop and documented repair before further measurement. These are not silently converted into successful no-op plans. Distinguish deliberate `searches: []`, schema fallback and infrastructure failure in logs and reports.

No planner can certify that all hobbies or all relevant events have been retrieved from an unseen store. Exhaustion means only that the one permitted follow-up step finished. Confidence and fluent explanations are not completion tests.

## 8. Implementation boundaries and artifacts

Proposed separate module `src/planned_memory/` wraps the existing source snapshot and frozen deterministic selector through a narrow interface. Keep planner transport and experiment scoring outside `src/unified_memory`; the existing package remains independently replayable.

Suggested responsibilities:

- `plan_schema`: versioned response types and pure validation, including citation membership.
- `planner`: exact prompt construction and single-call adapter; returns raw response plus parsed plan/failure, never source records.
- `executor`: cached query embeddings, independent source search and additive union.
- `trace`: content-bound run identity, initial IDs, raw plan, validation, generated queries/vector hashes, per-query selected IDs, final IDs and prompt hashes.
- Experiment harness: schedule, model ownership, immutable request/response capture, calibration, blind scoring and outcome analysis.

Model calls go through a counter-enforced boundary: at most one planner attempt and one answer attempt per ordinary treatment query, with no recursive callbacks. Fixture transports must fail if schema repair or a second planner call is attempted. Evaluation judges must not be importable by mechanism modules. Planner output is retained verbatim before parsing; source records and vector cache cannot be mutated through the plan.

Every example should be inspectable end-to-end: question -> S0 -> plan -> searches -> added source passages -> final answer. This trace is more useful than reporting only “planner found anchor.”

## 9. Model, prompting and hardware proposal

Initially use the already pinned local Qwen3.8-27B runtime for both planner and reader, serially, with native thinking **off** in both roles. This avoids introducing a stronger model at the same time as a new retrieval stage. It tests one-call planning with this model, not whether every LLM could perform it. A stronger planner or thinking-on planner is a later comparison if this instrument cannot perform the task.

Freeze a dedicated structured planner prompt and seed separately from the unchanged answering prompt/settings. Do not describe either as a verified published Mem0 prompt. Prefer native constrained JSON generation if supported by the pinned runtime, but verify its actual behavior and record any constraint implementation before lock; unsupported options do not justify an unrecorded runtime upgrade.

The dedicated planner prompt states that source passages are untrusted data, distinguishes source/question-grounded searches, demands preserved ambiguity, and forbids answering. It requests concise structured decisions, not hidden reasoning traces. The final reader receives neither the planner prompt nor its explanations.

Before registration, test planner input/output fit, the final union's worst-case fit, and coexistence of the reader server with the embedding encoder. Existing free-VRAM measurements do not certify a new simultaneous allocation. Prefer serial work and explicit load/unload if required; do not turn this into another batch-size sweep. Common answer context and output allowance must apply to both arms. Report planner/answer input and output tokens, embedding calls, latency and failure rates separately.

## 10. A small, task-aligned first evaluation

Do not default to all LoCoMo. The first proposed pilot is **48 real conversational questions**, at most one planner call per treatment question. Final population size and selection must be frozen before new generation. This is a feasibility/signal pilot, not a powered confirmation or an architecture adoption test.

Construct a transparent sampling frame based on the evidence obligation, with12 proposed cases per stratum:

1. **Implicit connection:** understanding a statement requires locating its antecedent/event context.
2. **Temporal state:** the answer requires relating changes or event times, not merely reading one explicit date.
3. **Multi-part evidence:** a comparison or enumeration requires multiple separately supported facts.
4. **Negative/ambiguity control:** either initial evidence suffices, or available sources cannot uniquely resolve the question.

These are proposed diagnostic strata, not existing LoCoMo category labels. Before selecting cases, specify evidence-based inclusion rules and apply them without seeing this treatment's output. Document prior exposure and whether prior outcomes were visible during selection. Do not preferentially select known planner-friendly failures. If LoCoMo cannot supply sufficient natural examples for a stratum, report that gap and revise the sampling plan before lock; do not force an unsuitable question into it or invent a label from wording alone. Small synthetic positive/negative fixtures can verify mechanics, but must remain separate from the natural-reader score.

For an initial feasibility pilot, a documented manual selection is acceptable if labelled purposive/exposed. It cannot yield representative population claims. It should contain clear connections, plausible alternatives, irrecoverable missing evidence and direct lookups, so the planner can demonstrably help, do nothing and mislead. The design does not require a new corpus download; corpus choice remains a review decision.

Before answers, create question-specific scoring contracts for lists, dates, required distinctions and acceptable uncertainty. A list must specify whether all listed facts are required; a relative date must specify when its supplied reference date is adequate. This directly addresses the latest scorer inconsistencies. Mechanical annotation containment cannot replace semantic sufficiency. Keep scoring artifacts isolated from all mechanism/plan inputs.

Use two contemporaneous arms: frozen deterministic S0+reader, and S0+one planner+executor+same reader. Freeze schedule and identical-prompt reuse before generation. Primary comparisons include all planned cases with the declared failure policy. Report answer correctness, paired gains/losses, per-stratum effects and failure/no-op counts. Report source sufficiency, added relevant and irrelevant records, overexpansion, unsupported planner connections and retrieval cost as diagnostics.

This experiment distinguishes the complete planning-assisted pipeline from S0. It does not isolate model knowledge, generated-query wording, extra retrieval opportunity, or additional evidence volume from one another. If a useful signal appears, a later matched-query/opportunity control can test whether model interpretation was needed; do not quietly add those arms now.

Practical success, weaker-signal, harm and nondegeneracy bars are **not set by this draft**. Select both directional tiers and failure rules after Part1 feasibility and before pilot outcomes, with reachable positive/negative controls. No full run should follow automatically from a pilot gain. Review actual question/plan/evidence traces first.

## 11. Development sequence and preflight

1. Review this single design, including the change in the research thesis and the proposed comparator, planner contract, executor, fallback and small sampling frame.
2. On implementation authorization, freeze a development protocol and build isolated interfaces/fixtures. Keep old studies unchanged. Resolve provisional bounds/runtime/schema choices using mechanics and exposed feasibility cases, not pilot outcome tuning.
3. Produce Part1: observed planner validity and failure distribution, useful/no-op/misleading queries, ambiguous cases, exact source preservation, retrieval expansion curves, latency and fit. Inspect whether the planner can identify a missing relationship and whether the executor can retrieve its support. A fluent plan without changed useful evidence is a failed mechanism test, not readiness.
4. Freeze the48-case or explicitly revised pilot, scoring contracts, both outcome tiers, model/runtime/prompt hashes, failure policy and schedule in one separate preregistration. Then run executable preflight before any pilot answer.
5. Execute the small comparison, seal raw plans/answers before judging, seal scores before opening outcome-linked plan analysis, and produce one closeout report. No long unattended full-corpus stage is part of this initial design.

Mandatory [PF1–PF10](../../../PREFLIGHT.md):

| Gate | Required mechanical evidence before measurement |
|---|---|
| PF1 | Counted/hash-bound source snapshots, existing vectors, baseline outputs, planner/runtime/schema, sample frame and isolated scoring contracts. |
| PF2 | Show actual one-call planning and deterministic execution on committed fixtures; verify no hidden repair/retry/second round, no plan text entering reader context. |
| PF3 | Missing registration/manifest/calibration blocks generation; persist-before-parse and raw/score/reveal order are executable negative tests. |
| PF4 | Pilot bars and harm branches reachable; planner cases include useful follow-up, no-op, irrecoverable ambiguity, malformed output and misleading search. |
| PF5 | Content/source identity survives plan serialization, search deduplication, restarts and rendering; no random IDs as comparison keys. |
| PF6 | Independent control checkout reproduces frozen S0 IDs/payloads; replay cached plans/vectors reproduces exact final evidence. Fresh stochastic plan identity is not assumed. |
| PF7 | One-round call cap, finite search bound and union behavior checked under duplicate/cyclic-looking plans and broad queries; near-full-corpus expansion positively detected. |
| PF8 | Worst initial context, maximal valid search list and largest final union tested; tiny success cases do not establish long-context planning capability. |
| PF9 | Explicit residuals: valid JSON can be wrong; cited text can fail to support a connection; retrieved annotations can be insufficient; an empty search list does not prove completeness; additive evidence can worsen answers. |
| PF10 | Same-reader paired answers required. Planner plausibility, evidence recall, or increased search coverage alone cannot justify an end-to-end success claim. |

## 12. Open choices for review

The proposed direction is one planner call over current C1 evidence, up to four direct follow-up searches, additive chronological assembly and an unchanged final reader. Before lock, settle: exact natural pilot sources/inclusion rules; final JSON schema and size limits; constrained decoding support; planner prompt/seed; generated-query threshold feasibility; final context allocation; source-sufficiency and list/date/ambiguity scoring contracts; and numeric success/harm/expansion bars.

These are visible pending choices, not permission to choose them mid-run. This document authorizes no implementation, new inference, scorer repair of old results, or production adoption. Its intended decision is whether a **bounded interpretive step** is worth testing as the first generative dependency of the memory architecture.
