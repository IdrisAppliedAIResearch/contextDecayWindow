# DMR-004 Annotation Protocol

**Document type:** Annotation protocol, committed before any label exists
**Status:** `LOCKED - NO LABELS PRODUCED AT COMMIT TIME`
**Stage:** DMR-004, deterministic query-obligation compiler
**Split manifest SHA-256:** `3007aa3a8af1ea8494b37c3cd9923657093fe649600791475631c44db61b19cf`
**Corpus digest:** `16e06f6d363ddc9d6743452713fc642b0cedf52c0f86fa62fff8e280f094daa9`
**Date:** August 12, 2026

Specification §6 requires annotators who see query text only, with agreement and
adjudication rules committed before compiler outcomes open. This document is
that commitment. It is committed in its own commit, before any label is
produced and before `src/biological_memory/query_obligations.py` exists.

## 1. Independence, honestly stated

There are no human annotators available to this program. Two raters are used:

**Rater A — the implementing agent.** Not independent of the compiler, because
the same agent writes both. The only protection available is order: A's labels
for a split are committed before the compiler is written, and A's labels for the
holdout are committed after the compiler is frozen by SHA but before it is run
on the holdout. Git order is the evidence.

**Rater B — the carried local model**, Qwen3.6-27B-UD-Q6_K_XL under llama.cpp at
`127.0.0.1:8080`, greedy decoding, one pass, prompt committed verbatim. B is
independent of the grammar in the sense that matters — it has never seen it —
and it is measurement-side only. It never forms, ranks, routes, stops, or packs
anything, and no part of the compiler may import, call, or depend on it.

The known limitation is recorded once here and applies to every number the
annotation produces: **rater A is not independent of the mechanism.** Where A
and B disagree, the adjudication rule below decides, and the dispute rate is
reported alongside every statistic computed from these labels.

## 2. What raters see

The query string. Nothing else.

Raters do not see answers, memories, retrieval outputs, haystack sessions,
domain labels, `question_type`, compiler output, each other's labels, or which
split a query belongs to. The rating file handed to each rater carries the
query text and the `query_id` only.

## 3. Label schema

Per query, three fields.

| Field | Values |
|---|---|
| `finite` | `true` / `false` |
| `plan_class` | `LOOKUP`, `HISTORY`, `ENUMERATE_N`, `CONJUNCT`, `OPEN` |
| `requested_count` | positive integer, or `null` |

Source spans are **not** hand-annotated. Part 1 measured the extracted span at a
median 0.91 of the query, which makes overlap agreement unfalsifiable; span
integrity is therefore gated on label-free properties — exact offsets,
non-overlap, and stability under perturbation — and not against gold spans.

## 4. Decision rules

These are semantic judgements, deliberately not lexical tests. A rater who
finds themselves matching a word list is applying the wrong instrument.

**`finite` is true** when a fixed number of stored items, knowable from the
query text alone, would fully satisfy the request.

**`finite` is false** when satisfying the request requires consulting an unknown
number of stored items. This includes counting, summing, averaging, computing a
duration or a difference, comparing across an unstated period, ordering a set
whose size the query does not state, and any request whose extent depends on
what happens to be stored.

> *How many bikes do I own?* → `finite: false`. The answer is a count over an
> unknown number of stored mentions. That the answer is one number does not make
> the evidence one item.

**`plan_class`**, applied in this precedence:

1. **`HISTORY`** — the query asks how a value changed over time, or asks for a
   superseded value as distinct from the current one. A reference to a prior
   *conversation* ("in our previous chat about X") is a pointer to where to
   look, not a history request, and is **not** `HISTORY`.
2. **`ENUMERATE_N`** — the query states an integer N and asks for the N members
   of a set. Record N in `requested_count`. An integer that is a price, a date,
   a model number, a distance, a duration, or an ordinal position is not N.
3. **`CONJUNCT`** — the query contains two or more requests, each of which would
   be a valid standalone lookup if asked alone.
4. **`LOOKUP`** — the query asks for exactly one fact, satisfiable by one stored
   item.
5. **`OPEN`** — everything else: unbounded requests, ambiguous reference,
   requests whose extent the text does not fix, and anything with `finite:
   false` that is not one of the above.

A query with `finite: false` may still be `HISTORY`, `ENUMERATE_N` or
`CONJUNCT` if its structure is one of those; `finite` and `plan_class` are
separate judgements.

## 5. Adjudication, fixed in advance

1. **`finite` disagreement resolves to `false`.** The conservative label wins.
   This stage is fail-closed by design, and the gold standard must not
   over-claim completeness any more than the compiler may.
2. **`plan_class` disagreement is recorded as `DISPUTED`,** not resolved.
   Disputed queries are excluded from per-class statistics and retained in the
   finite/open statistic, which rule 1 has already settled.
3. `requested_count` counts only where both raters chose `ENUMERATE_N` and
   agreed on N. Any other combination is `null`.
4. **No re-rating after seeing compiler output.** If a label is discovered to be
   wrong once outputs are open, it is recorded in an amendment and the original
   label stands for the gates.

## 6. Usability condition

The dispute rate on `plan_class` is reported before any gate is evaluated. It is
a property of the annotation, not of the compiler, and it is computed and
committed on the development sample before the pre-registration locks — so that
the pre-registration can set its bars knowing how noisy its gold standard is.

## 7. Samples

Drawn on a seed independent of the split seed, stratified by source, from
`artifacts/split_manifest.json`.

| Split | Annotated | internal | longmemeval | Split total |
|---|---|---|---|---|
| development | 120 | 9 | 111 | 209 |
| holdout | 180 | 15 | 165 | 315 |

All 24 internal queries are annotated: there are few of them and they carry the
imperative and no-interrogative-frame shapes LongMemEval does not contain.

## 8. Order of operations

The protocol's whole force is commit order. The intended sequence, each step its
own commit:

1. This document and the split manifest. *No labels exist.*
2. Development labels, rater A then rater B, with the agreement report.
3. The pre-registration, with bars set from Part 1 and the development
   agreement. *No implementation files.*
4. The compiler.
5. Holdout labels, rater A then rater B. *After the compiler's SHA is frozen,
   before it is run on the holdout.*
6. Gates.

A later step cannot repair an earlier one. If the order is broken it is recorded
as a deviation, as `DEVIATION_001` was in DMR-001B, and not rewritten away.
