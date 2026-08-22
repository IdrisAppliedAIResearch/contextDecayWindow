# HH-002 Pre-Registration — this component on the published LoCoMo table

**Status:** `REGISTERED — written before the first generation call`
**Date:** August 21, 2026
**Predecessor:** HH-001 (`PAPER_002.md` §5), which ran Mem0 locally on this
programme's own reader and won by 7.7 points
**Plan of record:** `HH_002_IMPLEMENTATION.md`

---

## 1. The question

HH-001 established that this component beats Mem0 **as run here** — one local
27B reader, one matched budget, this programme's harness. It established
nothing about the number Mem0 published.

HH-002 asks the other question: **what does this component score on the
benchmark that produced the published table**, measured by the harness that
produced it, using the model its authors used?

## 2. The target

arXiv:2504.19413 Table 2, LLM-as-a-Judge column, over LoCoMo:

| System | Score | Who produced it |
|---|---:|---|
| Full context | 72.90% | Mem0 authors |
| Mem0ᵍ (graph) | 68.44% | Mem0 authors, own system |
| Mem0 | 66.88% | Mem0 authors, own system |
| Zep | 65.99% | Mem0 authors, **not Zep's** |
| RAG (500/k=1) | 60.53% | Mem0 authors |
| OpenAI memory | 52.90% | Mem0 authors |
| A-MEM | 48.38% | Mem0 authors, **not A-MEM's** |

**A 62% figure was named when this work was authorized and appears nowhere in
this programme's records.** The nearest are Zep's LongMemEval 63.8% and RAG's
60.53%. This study is registered against the table above.

## 3. The harness

`mem0ai/mem0` at commit `7b3abd06` (2 May 2025), directory `evaluation/`,
retired upstream in June 2026 and read here from the canonical git blobs. Its
README carries the arXiv:2504.19413 badge and it contains one implementation
file per row: `src/memzero/`, `src/zep/`, `src/rag.py`, `src/langmem.py`,
`src/openai/predict.py`.

**Not the current harness.** `mem0ai/memory-benchmarks` benchmarks Mem0
Platform v3 at 92.5% with gpt-4o as answerer and judge and `top_k=200`. Its
published results contain only Mem0's own rows — no competitor was ever run
through it publicly — so a number from it is comparable to one system, not
seven. The jump from 66.88 to 92.5 is a different answerer model, 6.7× the
retrieved memories and a new pipeline moving together, and is not a memory
architecture result.

Three prompt strings are vendored byte-exact under `vendor/` and the run
refuses to start if their SHA-256 drifts:

| File | SHA-256 |
|---|---|
| `rag_answer_prompt.txt` | `744495b77f2955d4…` |
| `rag_system_message.txt` | `0c6b92630ba4c22f…` |
| `llm_judge_accuracy_prompt.txt` | `44fb3d8f7a1f37b2…` |

## 4. Population

All 10 LoCoMo conversations, 5,882 turns. Of 1,986 questions, **1,540 are
scored** — category 5 is adversarial and is skipped by `evals.py:22` and
`llm_judge.py:86`, so no category-5 record reaches any published number. 1,540
is the denominator of every row in §2 and is the denominator here.

## 5. Arms

| Arm | Memory layer | Purpose |
|---|---|---|
| `A_FULL` | Whole conversation, `chunk_size=-1` | **G-CTRL**, published 72.90% |
| `A_RAG` | 500-token chunks, `k=1` | **G-CTRL**, published 60.53% |
| `A_CDW` | This component, 16,000 chars, harness turn rendering | **The entry** |
| `A_CDW_NOTS` | This component, undated turn rendering | Registered secondary |
| `A_NONE` | Nothing | Floor / contamination |

**Budget.** 16,000 characters — this component's shipped configuration, the
one HH-001 ran and `PAPER_002.md` describes. The published table does not
control context size across rows (full context takes ~26,000 tokens, RAG takes
500), so each system enters as its authors configured it. This one does too.

**Turn rendering.** The harness renders every turn as
`{timestamp} | {speaker}: {text}`. NF-004's candidates carry no timestamp
because its endpoint was evidence delivery. LoCoMo category 2 is entirely
temporal and is unanswerable from undated text however well retrieved, so
handing this arm undated turns while the harness hands RAG dated ones would be
a handicap the study invented. `A_CDW` takes the harness's convention;
`A_CDW_NOTS` runs beside it so the size of that effect is measured, not
assumed.

**Embedder.** `text-embedding-3-small`, the harness's. NF-004's ranking is
dimension-guarded at 1024 and this model is 1536; the guard, not the
algorithm, is what refuses it. `hh002_arms.rank_pairs` is that function's body
with the guard parameterised, and `test_hh002_fidelity` asserts it returns the
frozen function's order on 1024-dimensional input. NF-004's module is not
modified.

## 6. Endpoints

**Primary — `llm_score`.** Mean over the 1,540 scored records of the binary
CORRECT/WRONG verdict from `metrics/llm_judge.py`, gpt-4o-mini at
`temperature=0.0` with `response_format={"type":"json_object"}`. This is the
column in §2.

**Secondary — `f1`.** The set-overlap over `simple_tokenize` from
`metrics/utils.py::calculate_metrics`. Deterministic, no model in the loop.
Carried because a study whose primary endpoint is a language model grading
language model output should contain one number no judge produced.

ROUGE, BERTScore, METEOR and SBERT are commented out in the upstream function
and are not computed. BLEU is absent from the table and needs nltk; not
computed.

## 7. Gates, fixed now

**G-CTRL.** `A_FULL` must reproduce 72.90% and `A_RAG` must reproduce 60.53%.

*Tolerance rule, fixed before any score is seen:* ±3.0 percentage points
absolute, **or** the interval implied by measured judge run-to-run variance,
**whichever is wider**. Variance is measured by judging `A_RAG`'s sealed
answers twice — the answers are byte-identical between replicates, so every
disagreement is the judge's own. `A_RAG` is named now, before any number
exists.

*If G-CTRL fails*, the study reports that as its result. A headline number
from a widely-cited paper failing to reproduce is worth publishing. It is not
an abort, and no claim about this component is made on a rig that cannot
reproduce the rows it is standing beside.

**G-FLOOR.** `A_NONE` must score below 5%. LoCoMo has been public since
February 2024. Above 5% means gpt-4o-mini knows the corpus and every row in §2
— theirs included — needs re-reading.

**H1, the one directional claim.** `A_CDW` > `A_RAG` on `llm_score`, paired by
item, one-sided exact binomial sign test, α = 0.05. Both endpoints must agree
in sign or no directional claim is made. At n = 1,540 the bar is reachable and
so is its reversal.

**No paired test against an inherited row.** Mem0's, Zep's and A-MEM's
per-item answers were never published. Their rows are quoted with attribution
and never entered into a test.

## 8. Deviations from upstream, and why none can move a score

| Deviation | Why it is inert |
|---|---|
| **Batch API transport** | This account's chat endpoint refills at ~7 requests/minute against a 10,000/day bucket; the study needs ~15,000 calls. Batch carries the same model, messages and temperature. It is when the answer returns, not what it is. |
| **Category 5 not generated** | Upstream answers all 1,986 then discards 446 at scoring. Records that reach no metric cannot change a metric. |
| **Concurrency** | Upstream already judges with 10 threads. Every call is independent and results are keyed by item, never by position. |
| **Dated model pin** | `gpt-4o-mini-2024-07-18` rather than the moving `gpt-4o-mini` alias. |
| **Query-embedding memoisation** | Each of the 1,540 questions is embedded once, one text per call, and reused across arms. The repeat request would be the first request. |
| **Candidate corpus batched** | `A_CDW`'s pairs are embedded in batches; `A_RAG`'s chunks are **not**, because that arm reproduces a published row and batch shape is known in this programme to move vectors. |
| **jinja2 kept** | A literal substitution silently drops the template's trailing newline. |

## 9. What this cannot establish

- **Confirmatory standing.** LoCoMo is spent on both splits — NF-004 read the
  holdout, HH-001 read it again. `REGISTERED-LIVE` at best, and generation
  against a vendor API is not replayable, so `AGENTS.md` §4's byte-identical
  rerun rule cannot be met. The report says so rather than implying otherwise.
- **A self-reported claim for five of the seven rows.** They are the Mem0
  authors' reproductions of other people's systems.
- **A capability claim.** LoCoMo fits a modern context window. Full context
  wins the published table and costs the most. On this benchmark a memory
  layer buys cost, not capability, whatever this component scores.
- **Anything about breadth.** As in HH-001, the arm carries no set-level
  coverage objective. `SCOPE_LIMITS.md` records that gap.
- **Anything about Mem0's current product.** §3.

## 10. Predictions

Ranked, falsifiable, sealed before results. These carry no standing and exist
so the record shows what was expected.

1. `A_NONE` scores below 2%.
2. `A_FULL` lands within tolerance of 72.90%; `A_RAG` within tolerance of 60.53%.
3. `A_CDW` beats `A_RAG` by more than 5 points.
4. `A_CDW` lands between 60.53% and 72.90% — above RAG, below full context.
5. `A_CDW_NOTS` trails `A_CDW`, and the gap is concentrated in category 2.
