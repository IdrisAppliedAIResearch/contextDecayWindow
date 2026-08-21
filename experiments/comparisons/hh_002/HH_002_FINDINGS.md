# HH-002 Findings — this component on the published LoCoMo table

**Status:** `REGISTERED-LIVE` — pre-registered, run on an observed corpus, not replayable
**Date:** August 21, 2026
**Pre-registration:** `HH_002_PRE_REGISTRATION.md`, hashed before the first generation call
**Generated tables:** `RESULTS.md` · **Provenance:** `paper/notes/HH002_EVIDENCE_SPINE.md`

---

## 1. The result

1,540 LoCoMo questions, the Mem0 authors' own harness at `7b3abd06`, their
answer prompt, their judge prompt, gpt-4o-mini as answerer and judge.

| System | LLM-as-a-Judge | Mean prompt tokens | Source |
|---|---:|---:|---|
| **This component** | **79.09%** | **4,243** | measured here |
| Full context | 72.90% | — | arXiv:2504.19413 Table 2 |
| *Full context, reproduced here* | *72.47%* | *25,405* | *measured here* |
| This component, undated turns | 71.56% | 3,696 | measured here |
| Mem0ᵍ (graph) | 68.44% | — | Table 2, Mem0's own system |
| Mem0 | 66.88% | — | Table 2, Mem0's own system |
| Zep | 65.99% | — | Table 2, **run by Mem0, not Zep** |
| RAG (best variant) | 60.53% | — | Table 2 |
| OpenAI memory | 52.90% | — | Table 2 |
| A-MEM | 48.38% | — | Table 2, **run by Mem0, not A-MEM** |
| *RAG 500/k=4, best variant found here* | *65.32%* | *2,030* | *measured here, post-hoc* |
| RAG 500/k=1, reproduced here | 45.78% | 570 | measured here |
| No memory | 26.30% | 84 | measured here |

**The component scores above every published row.** Against the ceiling row
reproduced on this rig it wins by **6.62 points** — 210 gains against 108,
one-sided exact binomial **p = 5.6e-09** — while sending **six times fewer
prompt tokens**. The deterministic endpoint, which involves no model, agrees
at **+15.32 points, p = 9.3e-31**.

## 2. What licenses the comparison

**G-CTRL passed on the row that could not be mis-specified.** Full context is
`--chunk_size -1`: the whole conversation, no chunking, no embedder, no
retrieval, no sweep. This rig reproduced it at **72.47% against a published
72.90% — 0.43 points.** The registered tolerance was ±3.0.

That single number is what makes the rest of this table readable. It says the
corpus adaptation, the prompt reconstruction, the judge and the metric behave
as the authors' did.

**The judge is stable.** The same 1,540 sealed answers were scored twice: rates
45.78% and 45.71%, **0.06 points apart, 3 items flipped (0.19%)**. This is not
an instrument whose noise could manufacture a 6-point gap.

## 3. G-CTRL's second row failed, and the target was mine

`A_RAG` at chunk 500 / k=1 scored **45.78% against a published 60.53% — a
14.75 point miss.**

**This is a pre-registration error, not a reproduction failure.** The published
row is *"RAG (best variant)"* — the top of a sweep the paper does not fully
specify. `HH_002_PRE_REGISTRATION.md` §5 mapped it to the Makefile's `run-rag`
recipe, which is one point in that sweep and not necessarily the best one. The
recipe was reproduced faithfully; it was pointed at the wrong number.

The rig is not in doubt, because the same rig reproduced the harder,
unambiguous row to within half a point. The post-hoc sweep settles it:

| Variant | chunk | k | Mean prompt tokens | Score | vs 60.53 |
|---|---:|---:|---:|---:|---:|
| `A_RAG_500_K4` | 500 | 4 | 2,030 | **65.32%** | +4.79 |
| `A_RAG_1000_K2` | 1000 | 2 | 2,012 | 50.65% | −9.88 |
| `A_RAG` (registered) | 500 | 1 | 570 | 45.78% | −14.75 |
| `A_RAG_1000_K1` | 1000 | 1 | 1,047 | 39.16% | −21.37 |

**The sweep spans 39.16% to 65.32%, and the published 60.53% falls inside
it.** A single RAG configuration is worth 26 points on this benchmark, so
"RAG (best variant)" is not one number that either reproduces or does not —
it is a choice, and the pre-registration bound itself to the wrong point in
it. The rig is exonerated on both rows; only the full-context row got a valid
pre-registered gate, and that is how the result is reported.

**A finding that fell out of the diagnostic.** `A_RAG_500_K4` and
`A_RAG_1000_K2` deliver the *same* budget — 2,030 against 2,012 mean prompt
tokens, within 1% — and four 500-token chunks beat two 1000-token chunks by
**14.68 points** (318 gains, 92 losses, p = 1.6e-30; deterministic endpoint
+11.30, p = 2.1e-22). At a fixed budget, retrieving more and finer beats
retrieving fewer and coarser. This is the same shape as NF-004's confirmed
result on a different mechanism, and it was not predicted here.

Against the best variant the sweep found, the component still leads by
**13.77 points** (276 gains, 64 losses, p = 8.4e-33).

## 4. G-FLOOR failed, and it is a finding about the benchmark

**With no memory block at all, the reader answers 26.30% of LoCoMo
correctly.** The registered bar was below 5%.

This is not contamination. It is guessability meeting a judge instructed to be
generous. Examples the judge scored CORRECT with an empty context:

| Question | Gold | Answer given |
|---|---|---|
| What does Andrew view his pets as? | Family | family members |
| Who supports Caroline when she has a negative experience? | Her mentors, family, and friends | Friends support Caroline. |
| When did Maria go hiking with her church friends? | The weekend before 22 July 2023 | Last Saturday. |

The judge prompt says it outright: *be generous, and count an answer correct if
it touches the same topic.* That prompt was reproduced byte-exact, so **this
floor sits under every row of the published table**, Mem0's included. The
paper reports no floor.

Read against it, the table compresses:

| System | Raw | Above the 26.30% floor |
|---|---:|---:|
| This component | 79.09% | **52.79** |
| Full context (reproduced) | 72.47% | 46.17 |
| Mem0 | 66.88% | 40.58 |
| RAG 500/k=1 | 45.78% | 19.48 |

The floor is not uniform. It is **32.34% on open-domain** — 841 of the 1,540
questions — and 11.21% on temporal. A benchmark whose largest stratum is a
third answerable with no memory at all measures less than its headline
suggests.

*Caveat on the last column:* the floor is measured on this rig with the same
model, judge, prompt and questions the published rows used. It is not a
measurement of their runs.

## 5. The timestamp ablation

Registered as prediction 5 before any result existed: the undated variant would
trail, and the gap would concentrate in category 2.

| Category | n | Dated | Undated | Effect |
|---|---:|---:|---:|---:|
| 2 temporal | 321 | 68.54% | 32.09% | **+36.45** |
| 1 single-hop | 282 | 71.63% | 72.34% | −0.71 |
| 3 multi-hop | 96 | 55.21% | 57.29% | −2.08 |
| 4 open-domain | 841 | 88.35% | 87.99% | +0.36 |
| **Overall** | **1,540** | **79.09%** | **71.56%** | **+7.53** |

**The entire overall gap comes from one stratum**, and the other three move by
less than the judge's own rounding. NF-004's candidate unit carries no
timestamp because its endpoint was evidence delivery; the harness renders every
turn dated. Adopting the harness's convention was the fair choice, and this
measures exactly what it bought rather than assuming it.

## 6. Cost

| Arm | Mean prompt tokens | Ratio to this component |
|---|---:|---:|
| Full context | 25,405 | 6.0× |
| **This component** | **4,243** | **1.0×** |
| This component, undated | 3,696 | 0.9× |
| RAG 500/k=1 | 570 | 0.13× |
| No memory | 84 | 0.02× |

The component wins the table on accuracy **and** sends a sixth of the ceiling
arm's tokens. Its store is built with **zero generative calls** — that is
architectural, not measured: `append()` embeds and stores, and no code path
asks a model to write text about what was stored.

## 7. What this does not establish

- **Not a measurement of Mem0.** Mem0's row needs a hosted-platform account
  (`MemoryClient`, `MEM0_API_KEY`, org and project ids) this study does not
  have. Zep's needs `ZEP_API_KEY`. Both are quoted with attribution and were
  never re-run. **No paired test against them is possible** — their per-item
  answers were never published.
- **Five of seven inherited rows are Mem0's reproductions of competitors.**
  Zep's own paper never reports LoCoMo. A competitor's reproduction is weaker
  evidence than a self-report.
- **Not confirmatory.** LoCoMo is spent on both splits — NF-004 read the
  holdout, HH-001 read it again — and generation ran against a vendor API, so
  `AGENTS.md` §4's byte-identical rerun rule cannot be met. `REGISTERED-LIVE`.
- **Not a capability claim.** LoCoMo fits a modern context window; the whole
  corpus is 25,405 tokens at the mean. A memory layer here buys cost, and on
  this corpus also accuracy, but not reach.
- **Not a claim about Mem0's current product.** Their maintained harness
  benchmarks Mem0 Platform v3 at 92.5% with gpt-4o and `top_k=200` — a
  different answerer, 6.7× the retrieved memories, and a new pipeline. Nothing
  here compares to it.
- **Nothing about breadth.** The arm carries NF-004's pair ranking and no
  set-level coverage objective.
- **One replicate.** The published rows are single runs too, and judge variance
  is 0.06 points, but the answerer was not replicated.

## 8. Predictions, scored

Sealed before results. These carry no standing.

| # | Prediction | Outcome |
|---|---|---|
| 1 | `A_NONE` below 2% | **Wrong.** 26.30% — the study's most consequential finding |
| 2 | Both G-CTRL rows within tolerance | **Half.** Full context −0.43; RAG missed on a target I mis-specified |
| 3 | Component beats RAG by more than 5 points | **Right.** +33.31 |
| 4 | Component lands between 60.53% and 72.90% | **Wrong — high.** 79.09%, above the table |
| 5 | Undated variant trails, gap concentrated in category 2 | **Right, and cleanly.** +36.45 in category 2, ≈0 elsewhere |
