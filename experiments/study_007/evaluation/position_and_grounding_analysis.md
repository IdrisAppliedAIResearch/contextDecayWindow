# Study 007 — Post-hoc: Position vs Grounding vs Retrieval Specificity

**Status:** BINDING CORRECTION to `study_007_report.md`
**Prompted by:** reviewer challenge that the Bar 1 failure may be lost-in-the-middle
reintroduced inside the LTM block, not a context-use failure
**Cost:** zero new runs — computed from committed logs
**Reproduce:** `PYTHONUTF8=1 .venv/Scripts/python.exe scripts/analyze_study_007_position.py`

---

## Summary

The challenge was correct that the report's diagnosis was the least specific of
the available hypotheses and was not established by the evidence. Testing it
refutes **all three** candidate diagnoses — including the report's — and
identifies a fourth that the logs support directly.

| Hypothesis | Verdict |
|---|---|
| **A. The model doesn't use provided context** (the report's claim) | **REFUTED** |
| **B. Lost-in-the-middle inside the LTM block** (the challenge) | **REFUTED** |
| **C. Prior strength on art/monetary** | **REFUTED at Q11**, weak residual at Q14 |
| **D. The floor delivered topic presence, not fact presence** | **SUPPORTED** |

The Bar 1 failure is a **retrieval** failure, inside the mechanism this study
built. It is not downstream of retrieval at all.

---

## 1. The decisive test: item-level grounding at Q11

For each of the 17 rubric-critical items Q11 expects, is it in the rendered
`<retrieved_ltm>` block, and is it in the model's answer?

**Turn 120 (Q11), treatment:**

| | Count | Items |
|---|---:|---|
| In block | 10/17 | 847, S460ML, 92.4, 600, 2%, Halcyon Crossing, Anara Bekova, Federal Reserve, Vampyroteuthis, Kenji Watanabe |
| In answer | 10/17 | *identical set* |
| **In block but unused** | **0** | — |
| **In answer but not in block** | **0** | — |

**The model used every rubric item it was given and invented none.** Grounding
at Q11 was perfect.

Q11 scored 0.0 because the block carried 10 of 17 items — `1483`,
`Annunciation`, `Melozzo`, `della Rovere`, `Taylor Rule`, `Priya Mehta` and
`2.3%` were **absent from the context window**. The model could not have named
them.

### The "background knowledge" was not background knowledge

The report asserted the model "substituted its own background knowledge",
citing Cosimo de' Medici, Ghirlandaio, the ECB, the Bank of Japan and a 2024 BOJ
rate hike as content "never in this conversation."

Every one of those terms is **in the turn-120 LTM block**. They are real
conversation content — the script does discuss Renaissance patronage from
1450–1510 and central-bank inflation targets. They are simply not the
*rubric-critical planted facts*.

The model fabricated nothing. The report's most quotable sentence was wrong.

## 2. Hypothesis B — lost-in-the-middle: refuted

Ordered block position at Q11, with each episode's normalized midpoint:

| Pos | Domain | Midpoint | Rubric items carried | Used in answer? |
|---:|---|---:|---|---|
| 1 | civil | 7.2% | Halcyon, 847, S460ML, 92.4 | **yes** |
| 2 | art | 21.8% | Julius II only | **yes** |
| 3 | civil | 36.4% | Halcyon, 847, Bekova | **yes** |
| 4 | **monetary** | **53.0%** | Federal Reserve, dual mandate | **yes** |
| 5 | marine | 68.7% | Vampyroteuthis, Watanabe, marine snow | **yes** |
| 6 | civil | 80.9% | Halcyon, S460ML, Bekova, 92.4 | **yes** |
| 7 | civil | 93.4% | Halcyon, 847, 92.4 | **yes** |

Monetary sat at the **dead centre of the block (53.0%)** and was used. Content
was used at 7%, 22%, 36%, 53%, 69%, 81% and 93% — every position, without
exception, across a 33,406-character block.

There is no middle-loss signature at Q11. The prediction the challenge
specified — art and monetary middle-positioned while civil and marine sit at the
edges — is not what the block looks like: civil occupied positions 1, 3, 6 and 7,
spanning both edges *and* the middle, and art sat at position 2, the most
privileged region.

**At Q14 there is a weak, confounded residual.** Art's fact-bearing episodes sat
at positions 6 and 7 of 8 (74%, 84%) carrying `Annunciation`, `Melozzo` and
`1483`, and the answer instead used the date range from the art episode at
position 2. But marine at position 8 (94%) *was* used, which a position account
has to explain away. The confound is that position 2 was also the floor
selection — the highest-similarity art episode — so prominence and position move
together. One run cannot separate them, and 7 of 14 block items being unused at
Q14 is expected anyway: Q14 asks for **one** fact per domain, so most block
content is correctly not quoted.

## 3. Hypothesis C — prior strength: refuted at Q11

Prior strength predicts the model overrides retrieved specifics with fluent
background knowledge for art and monetary. At Q11 it overrode nothing: it
reported `Federal Reserve` and `2%` from the block, added no rubric item that
was not in the block, and contradicted no retrieved fact. Where its art and
monetary prose looks generic, that prose was itself retrieved.

The Q14 art selection is weakly consistent with prior strength, and equally
consistent with the position confound above.

## 4. Hypothesis D — the floor delivered topic presence, not fact presence

Which episodes the policy actually selected at Q11:

| Phase | Source turn | Similarity | Topic | Carries the domain's planted facts? |
|---|---:|---:|---|---|
| floor | 20 | 0.5042 | civil | partly |
| floor | **31** | 0.4963 | **art** | **no** — the patronage overview, not turns 55/56/60 |
| fill | 28 | 0.4900 | civil | partly |
| floor | **69** | 0.4802 | **monetary** | **no** — a central-banking overview, not turns 61/62/65 |
| floor | 105 | 0.4751 | marine | yes |
| fill | 17 | 0.4635 | civil | partly |
| fill | 14 | 0.4495 | civil | partly |

Two things went wrong together, and both are retrieval-side:

1. **`k_min = 1` buys one episode per topic, and that episode is whichever ranks
   highest by similarity — not whichever carries the planted facts.** For art the
   winner was turn 31 (a topic overview); the facts live in turns 55, 56 and 60.
   For monetary the winner was turn 69; the facts live in 61, 62 and 65. A
   "list everything across all four topics" query embeds closer to summary prose
   than to a specific sentence about a 1483 altarpiece.
2. **All three fill slots went to civil.** Fill is pure global similarity with no
   per-topic cap — by design — so the domain with the most episodes took every
   remaining slot. Art and monetary never got a second chance.

At Q14 the fill happened to reach art turns 58 and 59, `1483` and `Annunciation`
entered the block, and Q14 scored 0.5 against Q11's 0.0. That is the same
mechanism, succeeding by luck of the similarity ordering.

## 5. What this means for Bar 1's attribution — and for the replay gate

Bar 1's log-attribution check passed because "four-domain coverage" was
operationalized as **≥ 1 planted term per domain present in the block**. Under
that definition the block did cover four domains: art contributed `Julius II`,
monetary contributed `Federal Reserve`.

Under the stronger definition the rubric actually scores — the domain's
rubric-critical facts are present — the block covered **two** domains at Q11.

So the pre-registered failure branch the report invoked was **mis-triggered**.
The correct branch is the adjacent row of the same table:

> Bar 1 fails without four-domain coverage → Budget or floor insufficient in the
> live run despite replay. **Compare live retrieval log to replay prediction; the
> divergence is the diagnosis.**

There is no divergence: the replay predicted exactly what happened, because the
replay gate used the same permissive coverage definition. **The gate's criterion
was too weak, in precisely the same way** — it checked that a domain was
represented, not that it was represented by the content the study is scored on.

This is the same failure class this study documented four times already: a
criterion that measures presence of a unit while the thing that matters is what
the unit contains.

## 6. Corrected diagnosis

**The memory architecture is still the bottleneck.** Formation holds the facts
(Bar 3, 4/4). Retrieval delivered four topics but only two topics' facts. The
model used everything it received, at every position in a 33,406-character
block, and invented nothing.

## 7. Implications for Study 008

The report proposed provenance instructions and prompting. **That is now the
wrong target** — there is no grounding deficit to fix at Q11. Prompting a model
that already used 10 of 10 available items cannot add the 7 items that were
absent.

Ranked by what the evidence supports:

1. **Make the floor fact-aware, or raise it.** `k_min = 1` is the direct cause.
   Either raise `k_min` (the sweep showed `k_min = 2` at `B_ltm` 24k–28k makes the
   floor causal, at a targeted-recall cost that must be re-measured), or select
   the floor episode by expected information content rather than by similarity to
   a query that favours summaries.
2. **Cap fill per topic, or reserve a fill quota.** Three of three fill slots
   going to one domain is a no-cap consequence the pre-registration chose
   deliberately; the Q11 log is the first evidence it costs breadth.
3. **Strengthen both gate criteria** to require the domain's rubric-critical
   facts, not merely a planted term. The current criterion passes on `Julius II`.
4. **Ordering is worth one cheap test but is not the lead hypothesis** — a
   Q14-only, confounded signal against a clean Q11 null.

Do not revisit formation. Do not run a prompting study on this evidence.
