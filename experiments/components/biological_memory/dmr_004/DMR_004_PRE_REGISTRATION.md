# DMR-004 Pre-Registration - Deterministic Query-Obligation Compiler

**Document type:** Locked pre-registration
**Status:** `LOCKED - IMPLEMENTATION AUTHORIZED`
**Development gold SHA-256:** committed at `510f410d`, before this document
**Stage:** DMR-004
**One new component:** `QueryObligationCompiler` in `src/biological_memory/query_obligations.py`
**Spec:** `../deterministic_retrieval/DMR_004_QUERY_OBLIGATION_COMPILER_IMPLEMENTATION_SPEC.md`
**Part 1 record SHA-256:** `d34e50c5ba6bf6127b3a219e7959bdb95be991be223d642e3cc5032fdf4c6e61`
**Split manifest SHA-256:** `3007aa3a8af1ea8494b37c3cd9923657093fe649600791475631c44db61b19cf`
**Corpus digest:** `16e06f6d363ddc9d6743452713fc642b0cedf52c0f86fa62fff8e280f094daa9`
**Date:** August 12, 2026

## 0. What Part 1 changed, and the authority for changing it

Part 1 measured the query population before this design existed and found the
specification's five-class grammar does not fit it. Three changes follow, all
made before the lock, which is what Part 1 is for.

1. **Conjunction and finite enumeration are emitted but not gated.** Part 1
   found 1 conjunction and 10 enumerations in 524 queries, and found that every
   conjunction detector with usable support fires on 66.7% of this program's own
   probes and 0.4% of natural questions. A bar on either class would be
   unreachable, corpus-identifying, or both. DMR-001 stopped on a bar locked
   without a reachability check; this is that check, applied per bar, before the
   lock.
2. **An aggregate frame demotes a lookup to open.** Read literally, §5.2 assigns
   `LOOKUP` with `ONE_EVIDENCE` to 272 of 524 queries whose answers are computed
   over an unknown number of stored items. §1 of the specification says it is
   better to say completion cannot be determined than to call a partly
   understood request complete; the registered grammar therefore does that.
3. **Source spans are not scored against gold spans.** Part 1 measured the
   extracted span at a median 0.91 of the query. Overlap agreement at that width
   is unfalsifiable, so span integrity is gated on exact offsets, non-overlap,
   bounds, and stability instead.

The stage question is unchanged. Its honest scope on this population is
narrower than the specification assumed, and §12's decision is read against
that scope in §9 below.

## 1. Hypothesis

A pure precedence parser over the user's own query text can decide, without a
model call and without any answer-key label, whether a request's evidence
obligation is mechanically bounded — and can do so conservatively enough that
the queries it calls bounded really are.

## 2. The component

```text
src/biological_memory/query_obligations.py
```

```python
class QueryObligationCompiler:
    def compile(self, query: str) -> QueryPlan: ...
```

Pure function. Zero embedding, network, filesystem, database, clock, random,
subprocess, and model calls. Imports from the standard library only.

```text
QueryPlan:
    query_hash         : sha256(original utf-8)
    normalized_hash    : sha256(canonical view)
    plan_class         : LOOKUP | CONJUNCT | ENUMERATE_N | HISTORY | OPEN
    obligations        : ordered[QueryObligation]
    completeness_mode  : FINITE | NOVELTY_ONLY | UNREPRESENTABLE
    ambiguity_codes    : ordered[str]
    design_sha256      : sha256 of the frozen grammar constants

QueryObligation:
    obligation_id      : sha256("dmr-obligation-v1\0" + query_hash + "\0" +
                                start + "\0" + end + "\0" + kind)
    kind               : LOOKUP | LIST_MEMBER | HISTORY_LINEAGE
    source_start       : int, offset into the ORIGINAL string
    source_end         : int, exclusive
    source_text        : query[source_start:source_end], exactly
    requested_count    : int | None
    support_mode       : ONE_EVIDENCE | N_DISTINCT | LINEAGE | NEVER_COMPLETE
```

Identity is content-addressed. No path, timestamp, uuid, or row number enters a
hash.

## 3. Canonicalization

NFKC, then case fold, then whitespace collapse, then strip — carrying a
per-character map from each canonical index back to the originating index in
the original string.

Both NFKC and case folding can change a string's length, so index arithmetic
against the original is not sound and the map is not optional. Part 1 also
measured what happens without canonicalization: matching multi-word markers
against the raw string flips 42.2% of plans under doubled spaces, in the
unsafe direction.

All matching is on the canonical view. All reported offsets are original
offsets. The Unicode version and the full pattern set are inputs to
`design_sha256`.

## 4. The registered grammar

Predicates are evaluated in this order, first match wins.

1. **HISTORY.** A history marker — `previous`, `prior`, `former`, `formerly`,
   `used to`, `initially`, `originally`, `back then`, or `how did/has/have …
   change/update/evolve` — that is **not** inside a discourse pointer
   `(our|the|my|a) (previous|earlier|last|prior)
   (conversation|chat|discussion|session|talk|exchange|game)`.
   → `plan_class HISTORY`, one `HISTORY_LINEAGE` obligation, `support_mode
   LINEAGE`, `completeness_mode NOVELTY_ONLY`.
2. **ENUMERATE_N.** A stated positive integer bound to a plural noun, together
   with a list or ordering request (`list`, `enumerate`, `name all`, `name
   every`, `order of`, `in the order`, `what are the`, `which`).
   → `ENUMERATE_N`, N `LIST_MEMBER` obligations, `N_DISTINCT`, `FINITE`.
   An integer that is a price, date, model number, distance, duration, or
   ordinal is not a cardinality; the bound-to-plural-noun requirement is what
   separates them, and where it fails the code `NUMERAL_NOT_CARDINALITY` is
   emitted and the query falls through.
3. **CONJUNCT.** Two or more clause-initial interrogative frames, a top-level
   semicolon, or a bulleted list.
   → `CONJUNCT`, one `LOOKUP` obligation per clause, `N_DISTINCT`, `FINITE`.
4. **Demotion to open.** An aggregate frame (`how many`, `how much`, `how
   long`, `how often`, `how far`, `total`, `in total`, `combined`,
   `altogether`, `average`, `mean`, `median`, `difference`, `differ`, `compared
   to`, `more than`, `less than`, `fewer than`, `sum of`, `count of`) or a
   superlative over an unnumbered set (`most recent`, `latest`, `earliest`,
   `highest`, `lowest`, `best`, `worst`, `the most`, `largest`, `smallest`,
   `first`, `last` without a stated integer).
   → `OPEN`, no obligation, `UNREPRESENTABLE`, code `AGGREGATE_FRAME` or
   `SUPERLATIVE_OVER_UNNUMBERED_SET`.
5. **LOOKUP.** One clause-initial interrogative frame with a contiguous
   complement.
   → `LOOKUP`, one `LOOKUP` obligation, `ONE_EVIDENCE`, `FINITE`.
6. **OPEN.** Everything else, `UNREPRESENTABLE`, code
   `NO_INTERROGATIVE_FRAME`.

`completeness_mode` is `FINITE` for `LOOKUP`, `ENUMERATE_N` and `CONJUNCT`;
`NOVELTY_ONLY` for `HISTORY`; `UNREPRESENTABLE` for `OPEN`. A lineage
obligation does not claim completeness: a value may have had any number of
prior values, and the query text does not bound them.

## 5. Registered statistic

**Youden's J** on the binary decision `completeness_mode == FINITE` against the
adjudicated gold `finite`:

```text
J = sensitivity + specificity - 1
```

J is base-rate-insensitive by construction. A compiler that answers `OPEN`
always scores J = 0; one that answers `FINITE` always also scores J = 0. This
is the constraint carried from DMR-001C, where macro F1 over an 18.6%
base-rate corpus rewarded frequent firing and a control's precision equalled
the base rate exactly.

Balanced accuracy `(sensitivity + specificity) / 2` is reported alongside. Raw
accuracy and F1 are reported but **cannot** be used to pass any gate.

## 6. Gates

*Bars are set in §7 from development reachability and are binding.*

| Gate | Meaning | Bar |
|---|---|---|
| **G1 Purity** | Query text and the frozen grammar are the only inputs; no network, model, filesystem, clock, random, or subprocess call; the module's import closure is standard library only | zero violations |
| **G2 Determinism** | Plans, obligation ids, spans, and ambiguity codes reproduce byte-identically in a second process, and no registered perturbation changes any plan class | zero differences |
| **G3 Finite safety** | Of the queries the gold says are not finite, the share the compiler marks `FINITE` | *see §7* |
| **G4 Class coverage** | Recall on `LOOKUP`, the one class with enough adjudicated instances to carry a bar | *see §7* |
| **G5 Span integrity** | Every obligation span is within bounds, non-overlapping with its siblings, exactly equal to `query[start:end]`, and recovers the same substring after canonicalization | 100% |
| **G6 Benchmark independence** | No registered marker phrase fires only on this program's own probes | zero internal-only markers |

`HISTORY`, `ENUMERATE_N` and `CONJUNCT` are **emitted and reported, not gated**.
After adjudication the development gold holds 2 history, 2 enumeration and 8
conjunction instances in 120 queries; none can carry a rate bar, and the 8
conjunctions are all internal probes. Their counts and this reachability
finding are restated in the report. **High overall accuracy cannot pass if G3
fails.**

## 7. Bars

Set from the development gold and from the inter-rater reference band, before
the compiler exists. Every bar is checked reachable in **both** directions — a
bar no admissible result can fail is not a bar.

### The reference band

Two independent raters agree on `finite` at raw 0.875, Cohen's κ 0.752, and
**Youden's J 0.759 in one direction and 0.770 in the other**. That is the
ceiling this stage can honestly ask for: a deterministic parser is not required
to beat two raters agreeing with each other. `plan_class` agreement is 0.808
with a **dispute rate of 0.192** and κ 0.667; 23 of 120 development queries are
therefore `DISPUTED` and leave the per-class statistics.

### The bars

| Gate | Bar | Fails when | Passes when | Reachable both ways |
|---|---|---|---|---|
| **G_J** primary | Youden's J ≥ **0.50** on the holdout sample | J = 0 for any degenerate compiler | J ≈ 0.76 is the inter-rater band | yes: always-`OPEN` and always-`LOOKUP` both score 0 |
| **G3** finite safety | false-finite rate ≤ **0.15** | always-`LOOKUP` scores 1.00 | always-`OPEN` scores 0.00 | yes |
| **G4** LOOKUP coverage | `LOOKUP` recall ≥ **0.60** | always-`OPEN` scores 0.00 | always-`LOOKUP` scores 1.00 | yes |
| **G5** span integrity | 100% well-formed | one malformed span fails it | — | yes |
| **G2** determinism | zero differences across processes and under all six perturbations | one differing digest fails it | — | yes |
| **G1** purity | zero violations | one non-stdlib import fails it | — | yes |
| **G6** benchmark independence | zero markers firing only on internal queries | one internal-only marker fails it | measured at 0 of 45 today | yes |

**G_J, G3 and G4 must all pass.** Each alone is passed by a degenerate
compiler and the three together are not: always-`OPEN` passes G3 and fails G4
and G_J; always-`LOOKUP` passes G4 and fails G3 and G_J. This is the
specification's §9 surrogate table turned into a joint condition rather than a
warning.

Rater A scores a false-finite rate of 0.186 against the adjudicated gold and
would **not** pass G3. That is recorded deliberately: the bar asks the compiler
to be more conservative than a human rater, which is what fail-closed means.

The finest rate the holdout can resolve is 1/105 ≈ 0.010 for G3 and 1/42 ≈
0.024 for G4, on the projected class sizes, so every bar above sits well inside
the corpus's resolution.

### Untested vocabulary

21 of the 45 registered marker phrases fire on neither corpus (`prior`,
`formerly`, `used to`, `originally`, `back then`, `how far`, `altogether`,
`mean`, `median`, `differ`, `more than`, `less than`, `fewer than`, `sum of`,
`enumerate`, `name all`, `name every`, `lowest`, `worst`, `largest`,
`smallest`). They are kept for generality and **marked `UNEXERCISED`**; the
report must list every marker that never fired, so no coverage is claimed that
was not demonstrated.

## 8. Parameters, each with its own justification

No parameter is inherited without a reason stated here. DMR-001C's binding
constraint turned out to be `min_event_size`, carried unchanged through three
studies and never once tested on its own.

| Parameter | Value | Why this value |
|---|---|---|
| corpus | 524 queries | every query this program has been scored on, plus every LongMemEval question. Not a sample — the whole of both. |
| split share | 0.40 development | leaves 315 holdout queries, enough that the 180-query annotation sample is a majority of it while development still supports bar-setting |
| annotation sample | 120 dev / 180 holdout | 120 is the largest a single rater can label carefully in one pass without drift; 180 holdout keeps the projected minority class (`LOOKUP`, ~42) above the 30-instance floor a rate bar needs |
| minimum instances for a rate bar | 30 | below 30 the finest resolvable rate exceeds 0.033 and a bar cannot distinguish a real miss from one query |
| Youden's J bar | 0.50 | two-thirds of the 0.76 inter-rater band; a compiler at chance scores 0 |
| false-finite bar | 0.15 | strict by intent: below the 0.186 a human rater achieves against the same gold |
| `LOOKUP` recall bar | 0.60 | below the 0.70–0.80 at which the raters recover each other's `LOOKUP` labels |
| seed | `5005` | program-wide constant since Study 006; used for the split and the annotation sample, on two independent domains |
| rater B decoding | temperature 0, top_k 1 | the runtime is not bit-reproducible even so, which is why the raw responses are the committed artifact rather than the procedure |

## 9. Decision

**PASS** — G1, G2, G5, G6 pass and G_J, G3 and G4 all pass. Freeze the compiler
and its unsupported-query contract for DMR-005. The claim is narrow and must be
stated as: on held-out natural queries, a model-free precedence parser decides
whether a request's evidence obligation is mechanically bounded, at better than
half the agreement two independent raters reach, without ever claiming
completeness for more than 15% of the requests that do not have it.

**STOP** — any of G_J, G3, G4 fails. The arc has no principled mechanical
sufficiency signal. Per specification §12, DMR-001 through DMR-003 may remain
useful fixed-depth components but a model-free adaptive controller is not
authorized, and the failed compiler **must not** be replaced with a second
language-model call inside this arc.

Neither outcome authorizes retrieval, an ablation, or a live run. Query
representation alone changes nothing that is delivered to a reader.

### What this stage cannot claim either way

`CONJUNCT`, `ENUMERATE_N` and `HISTORY` are not gated, so no result here
supports or refutes the specification's claim that those obligations are
representable. Part 1 found the instances do not exist to test it on, and that
finding stands independently of how the compiler scores.

## 10. Preflight

**State:** `NOT RUN`.

PF1–PF10 are executed after implementation and before gates, and the artifact
is committed. PF4 is already partly discharged above: every bar in §7 carries
its reachability in both directions, which is the check DMR-001 omitted.
