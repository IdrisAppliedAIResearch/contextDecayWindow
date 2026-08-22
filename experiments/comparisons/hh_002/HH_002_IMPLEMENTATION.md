# HH-002 Implementation Document — putting this component on the published leaderboard

**Status:** `IMPLEMENTATION PLAN — nothing built, nothing run, nothing authorized`
**Predecessor:** HH-001, which ran Mem0 locally and is reported in `PAPER_002.md` §5
**Date:** August 20, 2026

---

## 0. The numbers, first

The goal is a score for this component on the table below — the same benchmark,
the same questions, the same judge, the same metric.

| System | LoCoMo, LLM-as-a-Judge | Who ran it |
|---|---:|---|
| Full context | **72.90%** | Mem0 authors |
| Mem0ᵍ (graph) | **68.44%** | Mem0 authors, own system |
| **Mem0** | **66.88%** | Mem0 authors, own system |
| Zep | **65.99%** | Mem0 authors, **not Zep's** |
| RAG (best variant) | **60.53%** | Mem0 authors |
| OpenAI memory | **52.90%** | Mem0 authors |
| A-MEM | **48.38%** | Mem0 authors, **not A-MEM's** |

Source: arXiv:2504.19413v1 Table 2, recorded in `COMPETITIVE_LANDSCAPE.md` §2.

**A 62% figure was named when this work was authorized and appears nowhere in
this programme's records.** The nearest are Zep's **LongMemEval** 63.8% at
gpt-4o-mini and RAG's 60.53%. Confirm the target before anything is built.
Everything below assumes this table.

## 0.1 Why comparing to all seven costs barely more than comparing to one

**Do not run seven systems.** Mem0's authors already ran them, through one
harness, and published the result. Reproduce that harness and insert this
component, and the resulting number is comparable to **every row at once**,
because every row was produced by the pipeline we would be running.

That is the whole leverage of this study. The expensive part — building a
harness on which seven memory systems are commensurable — is already done and
published. What HH-002 buys is a seat at that table.

**What that inherits, and it is not small.** Five of the seven rows are the Mem0
authors' reproductions of other people's systems. Zep's own paper reports on DMR
and LongMemEval and never on LoCoMo; A-MEM's number here is not A-MEM's claim
about itself. A competitor's reproduction of a competitor is weaker evidence
than a self-report, and the report must attribute every row it quotes. This is
the same limitation every reader of that table already has — we would not be
creating it, but we would be standing on it.

---

## 1. What HH-001 could not do, and why this exists

HH-001 ran Mem0 on this programme's own reader, at a matched budget, and won by
7.7 points. That result is real and it is **not** a claim about Mem0 as
published: its substrate is one local 27B model where Mem0's paper used
GPT-4o-mini as extractor, answerer **and** judge.

| Claim | Status |
|---|---|
| Beats Mem0 as run here, one local reader, matched budget | **Held.** HH-001, §5 |
| Places on the published LoCoMo table | **Not attempted.** This document |

## 2. The design inversion

**HH-001 held our harness constant and varied the memory layer.**

**HH-002 must hold *their* harness constant and insert our memory layer into
it** — their answerer, judge, judge prompt, metric definition and question set.
Anything less produces a number that cannot be placed beside 66.88% however
carefully it is measured.

This inverts what counts as a deviation. In HH-001, swapping Mem0's embedder for
ours was required for a fair contrast. In HH-002 **every substitution is a
threat**, because the target is a specific published figure from a specific
pipeline.

## 3. Build order

Each stage gates the next.

### Stage 1 — Acquire and read their harness

Locate the evaluation code behind arXiv:2504.19413. Record what it does rather
than what the paper says: question set and size, answer prompt, judge prompt,
judge model and version pin, metric definition, and how retrieved memories are
serialized into the answer prompt.

**Deliverable:** their pipeline described with a file and line for every claim,
plus every place the code and the paper disagree.

**Stop condition:** if the harness is unpublished or unrunnable, HH-002 stops
here and reports that. Reimplementing their evaluation from prose is not a
reproduction and cannot carry a comparison to their table.

### Stage 2 — G-CTRL: reproduce the table before touching anything

Run their harness, their configuration, their pins, unmodified. The question is
not whether this component is good. It is whether this machine reproduces their
published numbers at all.

**Reproduce at least Mem0's 66.88% and full context's 72.90%** — their own
system and the ceiling. Those two are the rows they controlled end to end, so a
failure there is a reproduction failure rather than a question about somebody
else's system.

**Bar:** a tolerance fixed in writing before the run. Proposed ±3 percentage
points absolute, derived from the judge's own run-to-run variance — measure it by
scoring one answer set twice — rather than chosen as a round number.

**This is the gate the study turns on.** Without it a low score cannot be
attributed between *the published number does not reproduce* and *our rig runs
their harness badly*, and `AGENTS.md` §9.2 requires the report to say which. A
G-CTRL failure is a publishable result: a failure to reproduce a headline number
from a widely-cited paper is worth reporting on its own, and the plan treats it
as an outcome rather than an abort.

### Stage 3 — Insert this component as a memory backend

Replace only the memory layer. Their answerer, judge, prompts, questions and
metric stay untouched.

The seam is narrow: their pipeline queries a memory system and serializes what
comes back into the answer prompt. Our component exposes `context()`, returning
a rendered block for a query and a budget. The adapter maps one to the other.

**Two decisions fixed in writing before running:**

- **Budget.** Their pipeline gives Mem0 a `top_k`, not a character budget. Fix
  ours at the character length their configuration actually delivers, measured
  in stage 2, so neither side is handed more context. Record the measured number.
- **Embedder.** Their pipeline embeds with an OpenAI model. Using ours changes
  two things at once. Run both: **their embedder for the headline**, ours as a
  registered secondary. Report both.

### Stage 4 — The arms that make the table readable

Through the same harness: **this component**, **Mem0** (reproduced in stage 2),
**full context** (the ceiling), and **no memory** (the floor). The other five
rows are inherited from their table with attribution; they are not re-run.

The floor is not optional. HH-001's floor scored zero, which is what established
the corpus was not being recited from pretraining. A floor above zero here would
mean GPT-4o-mini knows LoCoMo, and every row in the table would need re-reading —
including theirs.

---

## 4. What this costs, and the decision it forces

**The programme's first paid external API dependency.** Every prior result was
produced on hardware in this room.

Order of magnitude, to be replaced by a measured figure: LoCoMo is ten
conversations of roughly 600 turns. Ingestion at Mem0's `1 + n` calls per pair,
answering ~1,500 questions, judging every answer, across four run arms — tens of
thousands of GPT-4o-mini calls. Cheap per call; the total is real.

**Price it from a single-conversation pilot before authorizing the rest.** That
is stage 2's first task.

Two costs that are not money:

- **Reproducibility leaves the room.** A vendor model can be deprecated or
  updated silently. Pin the dated model string, record it in the run header, and
  expect the pin to expire. `AGENTS.md` §4's byte-identical rerun rule cannot be
  met against an API and the report must say so rather than implying otherwise.
- **The judge is theirs.** That cuts both ways, and both halves belong in the
  report: it removes the objection that we scored ourselves, and a judge tuned on
  their output shape is grading ours. Carry the deterministic containment
  endpoint alongside, as HH-001 did, so one number in the study is one no judge
  produced.

---

## 5. What HH-002 can and cannot establish

**Can, if G-CTRL passes:** a score for this component on the same benchmark,
questions, judge and metric that produced all seven published rows — the one
comparison a reader of that paper can place directly.

**Cannot:**

- **Confirmatory standing.** LoCoMo is spent on both splits: NF-004 read the
  holdout, HH-001 read it again. `REGISTERED-LIVE` at best, under §4.1.
- **A self-reported claim for the five inherited rows.** Zep's and A-MEM's
  numbers there are the Mem0 authors' reproductions. Every quotation carries the
  attribution.
- **A capability claim.** LoCoMo fits a modern context window — HH-001 measured
  45,984 to 90,713 characters. Full context wins the published table at 72.90%
  and costs the most. On this benchmark a memory layer buys cost, not capability,
  and that stays true whatever this component scores.
- **Anything about breadth.** As in HH-001, the arm carries no coverage
  objective.

---

## 6. Open decisions, in the order they block work

1. **The target table.** The seven rows above, or something else? §0.
2. **Vendor API access.** Required for stage 2 and everything after.
3. **Spend ceiling**, set after the single-conversation pilot prices the run.
4. **G-CTRL's tolerance**, derived from measured judge variance rather than chosen.
5. **Whether a G-CTRL failure ends the study or becomes the study.** Decide now,
   while the answer is cheap and nobody knows which way it goes.

---

## 7. What transfers from HH-001

| Asset | Where |
|---|---|
| Corpus lock, split manifest, canonical QA identity | `experiments/external/locomo/` |
| The frozen component arm and its budget-charged packer | `src/analysis/hh001_arms.py` |
| Sealed-answer ordering, blinded judging, commitments gate | `src/analysis/hh001_run.py` |
| Deterministic containment endpoint, no model | `src/analysis/hh001_endpoints.py` |
| Per-call token and latency accounting | `src/analysis/hh001_reader.py`, `hh001_cost.py` |
| Prohibitions that still bind | `paper/notes/HH001_EVIDENCE_SPINE.md` §8 |

The measurement spine transfers. The reader, the judge and the harness do not —
which is the entire point of the study.
