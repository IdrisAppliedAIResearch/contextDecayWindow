# DMR-004 - Deterministic Query-Obligation Compiler Implementation Specification

**Document type:** Prospective implementation specification
**Status:** `DESIGN ONLY - NOT PRE-REGISTERED - NO IMPLEMENTATION AUTHORIZED`
**One proposed component:** `QueryObligationCompiler`
**Depends on:** Query text only; it is independent of DMR-001 through DMR-003
but precedes route control
**Reference:** `DMR_ARC_IMPLEMENTATION_ROADMAP.md`
**Date:** August 11, 2026

## Complete Arc Roadmap

This roadmap is repeated in every DMR specification so that no stage can be
read as an isolated optimization.

### Arc Thesis

The system should reconstruct useful context through deterministic memory
operations, then give that context to one downstream language-model reader.
The reader is the consumer of recall, not the controller of recall. Query
embeddings and stored embeddings are permitted retrieval primitives; generated
intermediate language is not.

### Non-Negotiable Invariants

1. Exactly one generative inference call is permitted per answered user turn,
   and it occurs only after retrieval terminates.
2. The memory path is extractive and provenance-preserving. Stored episode text
   is immutable; no generated summaries or rewritten search queries enter it.
3. Retrieval state contains vectors, typed edges, hashes, scores, bitsets, and
   deterministic query features only. It contains no model-authored reasoning.
4. A small active foreground and the serialized reader budget are separate
   limits. The existing 32,000-character ceiling remains a matched experimental
   control, not a claim about brain capacity.
5. The answer key and rubric may measure retrieval but cannot form, rank, route,
   stop, or pack it.
6. Each study adds one component. A downstream stage cannot rescue a failed
   upstream mechanism by changing it in the same study.
7. Existing known corpora are diagnostic development sets. Confirmatory claims
   require a newly locked holdout whose answers remain sealed through retrieval.
8. Offline availability is not an answer verdict. Any delivery-changing stack
   must pass the required 35-turn ablation before a longer or live run.

### Ordered Studies

| Stage | One new component | Mechanical question | Required output | Binding stop |
|---|---|---|---|---|
| **DMR-001** | Online event-context formation | Can a label-blind deterministic encoder partition a conversation into nondegenerate events and store stable encoding context? | Frozen episode-to-event map, typed event records, encoding-context vectors, and formation report | Stop if event identity is unstable, collapses to singletons/one giant event, or cannot beat structural controls on sealed boundary evidence |
| **DMR-002** | Typed event-bound pattern completion | Given an unchanged direct seed, do `MEMBER_OF_EVENT` edges recover other elements of that encoded event better than generic adjacency or recursive cosine? | Frozen completion operator and matched-opportunity offline report | Stop on no broad gain, any targeted loss, cross-event contamination, or identity-equivalence to a control |
| **DMR-003** | Retrieved-context recurrence | Does reinstating an encoding-time context state cue useful unvisited events that fixed-query similarity chaining does not reach? | Frozen recurrence operator, state traces, cycle proof, and matched-budget report | Stop on no differentiated cue, no broad gain, any targeted loss, or recurrent/absorbing behavior |
| **DMR-004** | Deterministic query-obligation compiler | Can explicit lookup, conjunction, enumeration, history, and open-query obligations be represented without a model or answer-key labels? | Frozen compiler, obligation manifests, coverage/ambiguity report, and unsupported-query contract | Stop if compiler output is unstable, key-dependent, fails registered class coverage, or falsely marks open requests complete |
| **DMR-005** | Deterministic route and stopping controller | Can frozen obligations and evidence novelty switch among direct, event, and context routes without a second model call? | Frozen state machine, route traces, false-stop report, and call-count proof | Stop if routing is equivalent to fixed depth, false stops exceed the locked bar, unsupported queries are claimed complete, or any extra generation occurs |
| **DMR-006** | No new memory component; integration validation | Does the frozen stack improve reader answers when retrieval is completed before one reader call? | Offline gates, 35-turn ablation, then only if eligible a separately authorized longer/live run | Stop on any targeted reader regression, failure of broad/domain gates, nondeterminism, budget violation, or pre-reader generation |

### Dependency and Branch Order

1. Execute only one stage per `study/dmr-NNN-short-name` branch and pull request.
2. Complete mandatory Part 1 exploration before locking that stage's
   pre-registration. Commit the pre-registration before implementation.
3. Freeze every upstream artifact by content hash. A later study imports the
   frozen artifact and proves byte-identical reproduction before adding its one
   component.
4. If DMR-001 stops, DMR-002 through DMR-006 are blocked because there is no
   validated event substrate. If DMR-002 stops, DMR-003 may test context
   recurrence from DMR-001, but DMR-005 cannot claim an event-completion route.
5. DMR-006 begins only after all included routes pass their own offline gates.
   Its 35-turn ablation precedes any 120-turn or live run.

### Arc Success Claim

The strongest claim this arc can earn is narrow: on preregistered held-out
conversations, a deterministic multi-route memory path supplies better evidence
and reader answers than the frozen direct-retrieval control, without targeted
losses, domain losses, extra generation calls, or budget violations. It cannot
establish that the implementation is how a brain works.

## 1. Stage Question

A retrieval controller cannot know when to continue or stop unless "enough
evidence" has a representation. Asking another language model to decide would
abandon this arc's thesis. DMR-004 tests the narrower alternative: compile only
explicitly recoverable structure in the user's own query into deterministic
obligations, while marking ambiguous and open-ended requests as unsupported for
completeness claims.

This is deliberately fail-closed. It is better to say "completion cannot be
determined mechanically" than to label a partially understood request complete.

## 2. Scientific Claim and Engineering Hypothesis

Category-specific cortical activity can precede recall
([Polyn et al., 2005](https://doi.org/10.1126/science.1117645)), top-down signals
can bias retrieval
([Tomita et al., 1999](https://doi.org/10.1038/44372);
[Rajasethupathy et al., 2015](https://doi.org/10.1038/nature15389)), and
controlled retrieval can dissociate from post-retrieval selection
([Badre et al., 2005](https://doi.org/10.1016/j.neuron.2005.07.023)).

These studies support goal-sensitive retrieval control; they do not show that
human goals are regular-expression plans. The obligation compiler is an
engineering hypothesis: explicit surface structure may provide a conservative
control signal without generated reasoning.

## 3. Scope

### Included

- Pure query-text normalization, tokenization, clause recognition, and stable
  source-span extraction.
- Five output classes: single lookup, explicit conjunction, explicit finite
  enumeration, history request, and open/unsupported.
- A support policy stating what a later controller may and may not claim.
- Exact provenance from every obligation back to query character offsets.

### Excluded

- Reading the memory store, embeddings, candidate results, answer key, rubric,
  known facts, domain labels, conversation history, or model output.
- Generated paraphrases, coreference resolution, semantic role labeling,
  inferred list cardinality, answer completeness, retrieval, routing, stopping,
  or scoring.
- Treating "all" as a known finite number when the query does not state one.

## 4. Intended Future Interface

```text
src/biological_memory/query_obligations.py
```

```python
class QueryObligationCompiler:
    def compile(self, query: str) -> QueryPlan: ...
```

The compiler is a pure function with zero embedding, network, filesystem,
database, clock, random, and model calls.

Proposed output:

```text
QueryPlan:
    query_hash         : sha256(original utf8)
    normalized_hash    : sha256(canonical normalized text)
    plan_class         : LOOKUP | CONJUNCT | ENUMERATE_N | HISTORY | OPEN
    obligations        : ordered[QueryObligation]
    completeness_mode  : FINITE | NOVELTY_ONLY | UNREPRESENTABLE
    ambiguity_codes    : ordered[enum]
    design_sha256      : sha256

QueryObligation:
    obligation_id      : sha256(query hash + source offsets + kind)
    kind               : LOOKUP | LIST_MEMBER | HISTORY_LINEAGE
    source_start       : int
    source_end         : int
    source_text        : exact query substring
    requested_count    : int | None
    support_mode       : ONE_EVIDENCE | N_DISTINCT | LINEAGE | NEVER_COMPLETE
```

## 5. Deterministic Grammar

### 5.1 Canonicalization

The compiler stores the original UTF-8 query unchanged. Matching uses a locked
canonical view: Unicode normalization form, case folding, whitespace collapse,
and a fixed tokenizer. Source offsets always point into the original string.
Normalization rules and Unicode version are part of the design hash.

### 5.2 Recognized Classes

The eventual pre-registration must lock exact tokens and precedence. The
mechanical shape is:

1. **HISTORY:** an explicit history marker such as "history", "previous
   values", "before and after", or "how did X change", plus one unambiguous
   source span for the target. Output one `HISTORY_LINEAGE` obligation.
2. **ENUMERATE_N:** an explicit positive integer cardinality tied to a list
   request, such as "list the 4" or "what are the three". Output one
   `N_DISTINCT` obligation with that integer.
3. **CONJUNCT:** two or more independently valid lookup clauses separated by
   top-level semicolons, bullets, or repeated interrogative frames. Plain
   lexical "and" is insufficient unless both sides independently match the
   locked lookup grammar.
4. **LOOKUP:** one interrogative frame with one contiguous requested source
   span. Output one `ONE_EVIDENCE` obligation.
5. **OPEN:** every remaining query, including unbounded "tell me everything",
   ambiguous pronouns, implicit multi-part questions, and list requests without
   mechanically knowable cardinality.

An `OPEN` plan may still be retrieved later, but its completeness mode is
`UNREPRESENTABLE` or `NOVELTY_ONLY`. No controller may report all obligations
resolved for it.

### 5.3 Precedence and Ambiguity

History precedes enumeration, enumeration precedes conjunction, conjunction
precedes lookup, and any unresolved overlap falls to `OPEN`. Multiple numeric
tokens, nested coordination, malformed cardinality, unmatched quotation, or
conflicting class markers emit an ambiguity code and fail closed.

The compiler does not replace obligation spans with synonyms. A later embedder
may embed the exact extracted span under the same call shape in every arm.

## 6. Independent Annotation Protocol

To measure the compiler without leaking answer labels, annotators see query text
only. They mark:

- whether the query has a mechanically finite evidence obligation;
- query class;
- number of explicit obligations or explicit list cardinality;
- exact source spans supporting each obligation;
- ambiguity and whether a completeness claim is possible from query text alone.

Annotators do not see answers, memories, retrieval outputs, domain labels, or
compiler output. Agreement and adjudication rules are committed before compiler
outcomes open. Development queries and confirmatory holdout queries are separate.

## 7. Part 1 Exploration Before Pre-Registration

The future branch must characterize:

1. Query-shape distributions across the internal corpus, LongMemEval, and a new
   natural-language holdout.
2. The exact proportion representable by each proposed grammar revision.
3. Every ambiguity code and false-positive class on development annotations.
4. Perturbation stability under case, whitespace, redundant decimal formatting,
   punctuation, reordered conjuncts, and adversarial uses of "and" or numbers.
5. Degenerate outputs: every query `OPEN`, every query `LOOKUP`, zero-length
   spans, overlapping spans, duplicate obligations, and excessive cardinality.
6. Whether the grammar silently encodes benchmark-specific labels or phrases.

The selected grammar is locked based on annotation performance and conservative
coverage, not downstream retrieval score.

## 8. Prospective Measures and Gates

### Required Measures

- Plan-class confusion matrix.
- Finite-versus-open precision and recall.
- Obligation-count exact match.
- Source-span exact and overlap agreement.
- False-finite and false-complete-capable rates, reported separately.
- Coverage by query class and corpus, not one aggregate.
- Byte-identical output digests across processes.
- Zero-call and import-boundary evidence.

### Binding Gate Meanings

Part 1 sets achievable numeric bars before the registration lock:

| Gate | Required meaning |
|---|---|
| G1 Purity | Query text and locked grammar are the only inputs; zero external/model calls |
| G2 Determinism | Plans, spans, IDs, and ambiguity codes reproduce byte-identically |
| G3 Finite safety | False classification of open/ambiguous queries as mechanically finite is below the locked strict bar |
| G4 Class coverage | Registered lookup, conjunction, finite enumeration, and history classes each meet their own bar |
| G5 Span integrity | Every obligation is an exact nonoverlapping source span with stable offsets |
| G6 Benchmark independence | Leakage and phrase-ablation tests do not reveal answer-key or benchmark-label dependence |

High overall accuracy cannot pass if G3 or any registered class fails.

## 9. Surrogate Audit

| Metric | False-pass mode | Protection |
|---|---|---|
| Query-class accuracy | Majority `LOOKUP` can dominate | Per-class gates and confusion matrix |
| Finite precision | Conservative `OPEN` can achieve high precision with no coverage | Separate class-coverage gates |
| Span overlap | A broad whole-query span can overlap every gold span | Exact offsets and span-length distribution |
| Annotation agreement | Humans can agree on structure that retrieval cannot use | DMR-004 claims representation only; DMR-005 tests control utility |
| No model call | Hidden learned NLP service can still exist | Pure-process network/import sentinels and dependency manifest |
| Stable output | A stable but benchmark-specific phrase table can pass | Phrase ablation and held-out source tests |

## 10. Stage Preflight

**State:** `NOT RUN`.

### Part 1 Deliverables

- Falsifiable identity: "At grammar SHA X, compile is a pure precedence parser
  whose only non-open plans match registered source-span patterns Y."
- Name checks for obligation, finite, open, ambiguity, source span, cardinality,
  and completeness mode.
- Full class and error distributions.
- Real-query demonstrations of every degenerate state.

### PF1-PF10

| Check | DMR-004 required artifact |
|---|---|
| PF1 | Query corpora, annotation protocol, blind labels, grammar, and split manifests with hashes/counts |
| PF2 | Executed identity and name-to-behavior traces on committed queries |
| PF3 | Test proving split/annotation lock and purity gates precede held-out output access |
| PF4 | Reachability table for every class, precision, coverage, and ambiguity bar |
| PF5 | Query/span/design hash and offset stability proof |
| PF6 | Reproduce any carried segmentation behavior by exact plan identity before new comparison |
| PF7 | Pure compiler has no feedback; prove bounded parse depth and output cardinality on intended maximum query length |
| PF8 | State that this stage detects parsing errors, not retrieval loops or reader regressions |
| PF9 | Completed surrogate table with majority/open-only baselines |
| PF10 | State that query representation alone authorizes no retrieval, ablation, or live run |

## 11. Verification Contract for Later Implementation

Tests must cover canonicalization, offsets across Unicode normalization, every
grammar class and precedence collision, malformed numbers, number formatting,
quoted spans, punctuation, nested coordination, duplicate obligations, maximum
length, output bounds, pure two-process replay, dependency/import restrictions,
and zero network/model calls. Numeric formatting tests must treat integer and
finite decimal answer forms as potentially value-equivalent without making
query cardinalities like `3.0 items` valid integers unless preregistered.

## 12. Decision

If DMR-004 passes, freeze the compiler and its explicit unsupported-query
contract for DMR-005. If it stops, the arc has no principled mechanical
sufficiency signal. DMR-001 through DMR-003 may remain useful fixed-depth
retrieval components, but a model-free adaptive controller is not authorized.
Do not replace the failed compiler with a second language-model call inside this
arc.

## Sources

- [Polyn et al. (2005)](https://doi.org/10.1126/science.1117645)
- [Tomita et al. (1999)](https://doi.org/10.1038/44372)
- [Rajasethupathy et al. (2015)](https://doi.org/10.1038/nature15389)
- [Badre et al. (2005)](https://doi.org/10.1016/j.neuron.2005.07.023)
