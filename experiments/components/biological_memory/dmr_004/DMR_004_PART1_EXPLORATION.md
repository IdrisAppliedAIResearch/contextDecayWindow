# DMR-004 Part 1 - Query Population Characterization

**Document type:** Mandatory Part 1 exploration record (`AGENTS.md` §4)
**Status:** `COMPLETE - NOTHING LOCKED`
**Stage:** DMR-004, deterministic query-obligation compiler
**Spec:** `../deterministic_retrieval/DMR_004_QUERY_OBLIGATION_COMPILER_IMPLEMENTATION_SPEC.md`
**Artifacts:** `artifacts/query_corpus.json`, `artifacts/part1_record.json`
**Part 1 record SHA-256:** `d34e50c5ba6bf6127b3a219e7959bdb95be991be223d642e3cc5032fdf4c6e61`
**Corpus digest:** `16e06f6d363ddc9d6743452713fc642b0cedf52c0f86fa62fff8e280f094daa9`
**Date:** August 12, 2026

Part 1 exists so that findings can change the design before anything is locked.
They have. This record is the evidence; no pre-registration exists yet and no
compiler has been written.

## 1. Corpus

524 user queries, text only. No answer, evidence marker, haystack session,
embedding, domain label, or rubric is reachable from the loader
(`src/analysis/dmr004_corpus.py`).

| Source | n | distinct | chars median | chars p95 |
|---|---|---|---|---|
| internal (study 005 + 010 probe turns) | 24 | 24 | 139 | 254 |
| longmemeval (all 500 question strings) | 500 | 500 | 72 | 192 |

LongMemEval's `question_type` is loaded on a separate field for the §8
benchmark-independence measurement only, and `queries_only()` exists so that
mechanism-side callers cannot reach it by accident.

## 2. Falsifiable identity

> At grammar SHA X, `compile` is a pure precedence parser over a canonical
> NFKC-casefolded whitespace-collapsed view carrying an offset map back to the
> original string; its only non-open plans are those whose canonical view
> matches a registered source-span pattern, and every other query returns
> `OPEN` with at least one ambiguity code.

Two candidate grammars were built against that identity and measured. `R1` is
specification §5.2 read literally. `R2` is `R1` plus the three exclusions §5.2
does not contain. `R2_RAW` is `R2` matching the raw string instead of the
canonical view, retained only so one figure below stays reproducible.

## 3. Finding 1 - the specification's grammar marks half the corpus falsely complete

53.4% of LongMemEval questions carry an aggregate frame: "how many", "how
much", "how long", "total", "average", "difference", "the order of". Their
answers are computed over an unknown number of stored items.

Surface grammar cannot see this. One interrogative frame, one contiguous
complement, so §5.2 returns `LOOKUP` with `support_mode = ONE_EVIDENCE`.

**272 of 524 queries (51.9%)** are marked with a fixed evidence obligation
under R1 and are aggregates. Examples, all classified `LOOKUP` by the
specification as written:

- *How many bikes do I own?*
- *How many days did I spend in total traveling in Hawaii and in New York City?*
- *What is the total cost of the new food bowl, measuring cup, dental chews, and flea and tick collar I got for Max?*
- *What is the order of the six museums I visited from earliest to latest?*

Section 1 of the specification says it is better to say completion cannot be
determined mechanically than to label a partially understood request complete.
Every member of this set violates that principle, and it is the majority of the
corpus. R2 routes them to `OPEN` with code `AGGREGATE_FRAME`.

## 4. Finding 2 - two of the four gated classes have no instances to gate on

Per-class support under R2, n=524:

| Class | n | share | supports a rate bar (n≥30)? |
|---|---|---|---|
| OPEN | 305 | 58.2% | yes |
| LOOKUP | 173 | 33.0% | yes |
| HISTORY | 35 | 6.7% | yes |
| ENUMERATE_N | 10 | 1.9% | **no** |
| CONJUNCT | 1 | 0.2% | **no** |

G4 as specified requires that "registered lookup, conjunction, finite
enumeration, and history classes each meet their own bar." With one conjunction
instance in 524 queries, the finest rate a conjunction bar can resolve is 1.00.
**No conjunction bar is reachable on any corpus available to this stage.**

This is the defect that stopped DMR-001: a bar locked without a reachability
check, unreachable by construction, failed on the holdout. PF4 is being applied
per bar here, before the lock, rather than per statistic afterwards.

## 5. Finding 3 - every conjunction detector is a corpus detector

Five surface tests for multi-part requests, run on both sources:

| Probe | internal | longmemeval | separation |
|---|---|---|---|
| coordinated imperative (`name X and Y`) | 66.7% | 0.4% | 0.663 |
| comma list of three (`A, B, and C`) | 66.7% | 2.0% | 0.647 |
| imperative sequence (`name X … then state Y`) | 50.0% | **0.0%** | 0.500 |
| coordinated interrogative (`…, and what is …`) | 20.8% | **0.0%** | 0.208 |
| top-level semicolon | 0.0% | 0.2% | 0.002 |

The only rule with no corpus separation is the one with no instances. Every
rule that finds conjunctions finds them almost exclusively in the house
scripts. A conjunction class built on any of them is mechanically a detector
for "this query was written by this program's authors", which is exactly the
G6 failure mode in the specification's own surrogate table.

The internal probes are semantically five-part requests — *"name the project
and lead, then state the primary value, technical specification, and decision
threshold"* — but syntactically one imperative frame with noun-phrase
coordination. Natural users write the same way. Top-level clause separators are
not how multi-part requests are expressed; the specification's requirement that
"plain lexical *and* is insufficient" is therefore a requirement that the class
never fire.

## 6. Finding 4 - two named classes fail their own names under R1

**HISTORY.** R1 fires on 106 queries (20.2%). 41 of them match
`our|the|my previous|earlier|last conversation|chat|discussion`. *"I'm going
back to our previous conversation about DIY home decor projects. Can you remind
me what sealant you recommended?"* is a pointer to **where to look**, not a
request for **what changed**. Under R1, HISTORY also fires on 49 of the 56
`single-session-assistant` items and 3 of the rest — a near-perfect benchmark
label detector. R2 excludes the pointer form and the count falls to 35.

**ENUMERATE_N.** R1 fires on 28 queries via an integer-plus-plural-noun rule.
27 carry code `NUMERAL_NOT_CARDINALITY` under R2: *$5 coupon*, *5K run*,
*iPhone 13 Pro*, *March 15th issue*, *10 days ago*, *the 7th job in the list*,
*27. Kg2 Bd5+*. Numerals in natural queries are prices, dates, model numbers,
distances and ordinals. Genuine list cardinalities number 10 in 524.

## 7. Finding 5 - matching the raw string breaks under doubled spaces

`R2_RAW` and `R2` agree on all 524 unperturbed queries. Under the whitespace
perturbation they diverge on **221 queries (42.2%)**: a two-word marker such as
`how many` stops matching the moment a user types two spaces, and the plan flips
`OPEN → LOOKUP` — the unsafe direction.

Canonicalization is therefore not a tidiness step. It carries an offset map
(`canonical_map`) so that spans still point into the original string, which is
what §5.1 requires and what index arithmetic cannot deliver once NFKC or
casefold changes a string's length.

Full perturbation table, R2: case 0.0%, whitespace 0.0%, punctuation 0.0%,
quotes 0.0%, decimal 0.0%, reordered conjuncts 0.0% (1 applicable). R1: all
0.0% except decimal at 11.1% — `3 days` → `3.0 days` flips `ENUMERATE_N` to
`LOOKUP`, the case §11 says must not silently become a valid integer.

## 8. Finding 6 - the span rule is a whole-query surrogate

The extracted source span covers a median **0.91** of the query under R1 and
0.89 under R2; 64.8% of R1 spans cover 90% or more of the query. The
specification's §9 warns that "a broad whole-query span can overlap every gold
span". It does. Any span bar stated as overlap agreement is unfalsifiable at
this width; exact offsets and the length distribution are the only usable form.

## 9. Degenerate states

| State | Reached on real queries? | Evidence |
|---|---|---|
| every query `OPEN` | no | max observed share 58.2% (R2) |
| every query `LOOKUP` | no | max observed share 67.9% (R1) |
| zero-length span | no — unreachable by construction | the span rule returns `None`, never an empty interval |
| span covers whole query | **yes** | 11 of 206 R2 spans at ≥95% coverage; 41.7% at ≥90% |
| overlapping spans | no | one span per plan in both grammars |
| duplicate obligations | no | 524 distinct query texts, one obligation each |
| excessive cardinality | no | largest requested count observed is 6, against a threshold of 10 |
| no interrogative frame | **yes** | 44 queries, led by the internal imperative probes (*"For structural engineering, name the project and lead…"*) |

## 10. What Part 1 changes

1. The five-class grammar of §5.2 does not fit the query population. Its
   dominant output on natural queries is a false completeness signal.
2. `CONJUNCT` cannot be gated. Either it is dropped from the registered classes
   or the stage acquires a corpus in which multi-part requests occur naturally
   and are not written by this program's authors.
3. `ENUMERATE_N` supports an exact-match bar over 10 instances at best, not a
   rate bar.
4. The honest reading of the stage question on this population is narrower than
   the specification assumes: for about a third of queries a deterministic
   obligation is representable; for the majority the only defensible output is
   "completion cannot be determined mechanically."
5. Any registered statistic must be base-rate-insensitive. On a 33/67 split,
   accuracy and F1 both reward answering `OPEN` always, which the surrogate
   table already names as the failure mode for finite precision.

Nothing above is a result. It is the population the design has to be built for,
and it is committed before the design exists.
