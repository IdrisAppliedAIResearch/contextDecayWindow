# HH-001 Pre-Registration — Head-to-Head Against a Published Memory Layer

**Status:** `DRAFT — NOT LOCKED. NOT RUNNABLE.`
**Integrity anchor:** none yet. The anchor is the SHA of the commit that first
contains the **locked** version of this file. This draft is not that commit.
**Authorized by:** user, August 19, 2026 — *to lay out the design only.* No
implementation, acquisition, capture, generation, scoring or inference is
authorized by this document.
**Predecessors:** NF-004 (the confirmed availability result), LV-001 (the live
run that separated availability from answers), EC-001 (the substitution failure
this design exists to avoid repeating), NF-008 (the reader-study design brief
this absorbs)
**Corpus:** LoCoMo, both splits — **already read** (§2.3)
**Seed:** 5005
**Planned generative calls:** **many.** This is the first study in the programme
whose instrument requires them.
**Date:** August 19, 2026

---

## 0. What this document is, and what it is not

`AGENTS.md` §4 requires the design to be committed before implementation, and
its SHA to be the integrity anchor. This file is the design. It is **not yet the
anchor**, for three reasons stated up front rather than discovered later:

1. **Preflight Part 1 has not been executed.** §4 requires the mechanism to be
   characterized empirically — run, not read about — before a test of it is
   designed. Nothing has been run. §9 lists what must be.
2. **Four parameters are named by rule rather than by value** (§14). A locked
   registration carries values. `AGENTS.md` §4: *parameters live in one
   authoritative place: the pre-registration.*
3. **Two decisions are the user's, not the agent's** (§14.1, §14.2). One of them
   commits the programme to its first paid external API dependency, and it
   changes what the study is allowed to conclude.

The correct sequence from here is: resolve §14 → execute §9 Part 1 → close §10
Part 2 → lock this file in a commit containing no implementation files → build.
A reviewer should read this draft as *the argument for what the study must be*,
not as an authorization to run it.

**This study adds no component.** §7 forbids a second new component per study.
HH-001 adds an **instrument** — a shared reader and a shared judge — and freezes
every memory mechanism it measures.

---

## 1. The claim

Under one fixed reader, one fixed judge, and a matched delivered-character
budget, on the corpus where a published competitor reports its headline result:

> **A memory path that spends zero generative calls retains at least as much of
> a reader's answer accuracy as a memory path that spends `1 + n` generative
> calls per stored message pair, within a pre-registered non-inferiority margin
> of 5 percentage points.**

This is a **retention** claim, not a superiority claim, and the choice is
deliberate. `AGENTS.md` §9 states the programme's own frame:

> the question is rarely *does the deterministic version win*. It is **how much
> of that layer survives without the call.**

The claim is scoped to: this corpus, this reader, this judge, this budget, these
two frozen configurations. It does not claim that deterministic memory is
generally competitive, that the result transfers to another reader, or that
either system is correctly configured for any deployment.

### 1.1 The claim's mirror, registered at equal strength

§9.4 requires both directions of the guardrail. So the outcome **A2 beats A3**
is registered here as reachable, along with what it would and would not mean, so
that it cannot be quietly rounded down if it happens. See §7, tier `EXCEEDS`.

---

## 2. Why no head-to-head exists yet, and what has to be built

`paper/notes/COMPETITIVE_LANDSCAPE.md` §5 forbids every sentence of the form
*this component beats / matches / approaches / trails Mem0*. That prohibition is
not caution. It records that **no shared instrument exists on which those words
have a referent.** Three separate obstacles produce that, and HH-001 is a
proposal to remove all three at once. Each one, left in place, makes the study
uninterpretable rather than merely weaker.

### 2.1 The instrument problem — different measures of different objects

| | This component | Mem0 and its neighbours |
|---|---|---|
| Endpoint | Evidence **availability** at a fixed character budget | LLM-judged **QA accuracy** |
| Measured with | Zero model calls | A model answering and a model judging |
| Delivered text | Stored episodes verbatim | Model-extracted memories |

Placing 935/1,098 beside 66.88% would be a surrogate that passes without the
property it certifies — `AGENTS.md` §3's named recurring failure. **This
programme has already caught that exact substitution once, on itself.** LV-001's
shipping configuration preserved 16/16 targeted items offline and then fired its
registered live kill bar at a 0.5 tolerance; targeted score fell 3.5 → 1.5 and
the promotion did not happen. The magnitude sits inside the 3.0-point instrument
band and is `NOT DEMONSTRATED`; the disposition does not, and it fired.

So HH-001 cannot compare on availability. **The shared endpoint has to be the
downstream one — whether a reader answers correctly** — because that is the only
endpoint both architectures can be scored on without privileging the
representation one of them happens to use. Availability is retained here as a
registered secondary and **cannot set disposition** (§6.2).

### 2.2 The substrate problem — and EC-001's precedent

Mem0's published 66.88% was produced with GPT-4o-mini as extractor, answerer and
judge. This repository runs a local llama.cpp server. Running Mem0 with a
substituted model and reporting the result against its published number is
**exactly EC-001's failure**: its LongMemEval evaluator was Codex-substituted,
and Amendment 010 now forbids placing its 20.0% and 12.22% figures against any
published LongMemEval score. That prohibition was written after the run. Here it
is written before.

Two tiers are therefore registered, and **which one runs changes what the study
may conclude.**

#### Tier A — vendor-faithful (preferred)

Mem0 runs as published: `gpt-4o-mini` as extractor, answerer and judge, at a
pinned API model version. The reader and judge for **every** arm are that same
model, so the comparison is substrate-matched *and* the competitor arm is
reproducible against its own paper.

- Requires an external paid API dependency — **a first for this repository**,
  and a user decision (§14.1).
- Enables **G-CTRL** (§8), the reproduction gate that makes the denominator in
  §6.1's retention statistic trustworthy.
- Permits sentences of the form *against Mem0 as published*.

#### Tier B — matched-substrate fallback

Every arm, including Mem0's internal calls, runs on the pinned local
`Qwen3.6-27B-UD-Q6_K_XL`.

- No external dependency, no cost, fully self-hosted.
- **G-CTRL is unavailable.** Mem0's published number is not reproducible on this
  substrate and may not be quoted as this study's denominator.
- The conclusion narrows to: *under one fixed local reader at matched budget,
  arm X delivered more correct answers than arm Y*. That is a real head-to-head
  and a real finding. It is **not** a claim about Mem0 as published, and §13
  forbids writing it as one.

**Tier B is not a degraded Tier A. It is a different, narrower study**, and the
report must name which tier ran in its title line. Running Tier B and reporting
Tier A's sentence is the specific defect this section exists to prevent.

### 2.3 The seal problem — LoCoMo is exhausted

The corpus lock split all ten conversations by seeded digest: development
`conv-41`, `conv-42`, `conv-47`, `conv-48`; holdout `conv-26`, `conv-30`,
`conv-43`, `conv-44`, `conv-49`, `conv-50`. **NF-004 ran the holdout.** There is
no unread LoCoMo split left.

That is not fatal, but it fixes this study's standing and the fix must be stated
before the run, not chosen after it:

- **HH-001 Part 1 (this document) is `REGISTERED`, not `CONFIRMATORY`.** The
  endpoint is new and no arm has ever been tuned against it, which is worth
  something. But the component's configuration was selected using LoCoMo
  availability, so LoCoMo accuracy is correlated with a quantity this programme
  optimized on this corpus.
- **The bias is not one-sided, and saying so precisely matters.** Mem0's
  published configuration was also developed against LoCoMo, by its authors. So
  both arms carry corpus-specific selection. The bias is plausibly similar in
  direction and is **not** measured by this study. §13 forbids describing it as
  cancelled.
- **Confirmation requires a sealed corpus and is deferred to HH-002**, which
  this document does not register. LongMemEval-S is exhausted at the item level
  (EC-001 470 answerable, NF-005 465). Candidate sealed corpora — LongMemEval-M,
  or a fresh acquisition under a new corpus lock — are a §14.4 blocker for
  HH-002, not for this study.

---

## 3. Arms

Every arm is frozen before the run. No arm is tuned inside this study.

| Arm | Name | Memory layer | Purpose |
|---|---|---|---|
| **A0** | `NO_MEMORY` | none; question only | **Floor.** Measures how much the reader answers from pretraining |
| **A1** | `FULL_CONTEXT` | whole conversation in the window | **Ceiling.** Mem0 reports 72.90% here |
| **A2** | `CDW_PAIR` | this component, frozen at NF-004 `P_PAIR_RANK` | Treatment |
| **A3** | `MEM0` | Mem0 OSS at a pinned version, default config | Competitor |
| **A4** | `RAG_FIXED` | plain chunked embedding retrieval, matched budget | **Control.** Is any of this better than a naive vector store? Mem0 reports 60.53% for its best RAG variant |

**A0 is not optional and is not a formality.** LoCoMo has been public since
February 2024. A reader trained after that may have seen it. If the reader
answers a large share of questions with no conversation at all, the study is
measuring memorization and cannot discriminate memory layers. §8's `G-FLOOR`
makes that a stopping condition rather than a caveat.

**A4 is the control that protects the interesting result in both directions.**
If A2 and A3 both fail to beat naive chunked retrieval, the head-to-head between
them is a comparison of two things that do not matter.

**Deferred, and deliberately.** Mem0ᵍ (graph), Zep/Graphiti, A-MEM and
HippoRAG are **not** in this study. Graphiti alone requires a Neo4j deployment
and five generative calls per episode; each additional integration multiplies the
surface on which a faithful-configuration failure can go unnoticed and be
reported as a mechanism result. One competitor, run correctly and gated on
reproducing its own number, is worth more than four run approximately. A
successor may add them.

---

## 4. Population and stable keys

**Source.** The exact 2,805,274-byte `locomo10.json` at SHA-256
`79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`, from
official repository commit `3eb6f2c585f5e1699204e3c3bdf7adc5c28cb376`. Bytes are
not committed; the manifest is the artifact, per the LoCoMo corpus lock.

**Frame.** The six holdout conversations and their 1,098 fully resolvable
canonical unique QA records — NF-004's primary population, reused so the
availability secondary (§6.2) joins to a committed prior result by identity.

**Item identity.** NF-004's canonical QA hash: SHA-256 over `sample_id`, a NUL
byte, and sorted compact JSON of the complete source QA record. Source paths,
generated ids and timestamps are not comparison keys.

**Sample.** Live generation over 1,098 items × 5 arms × R replicates is not
feasible at local-model throughput, so the primary runs on a seeded subsample.
The **rule** is registered here; the **number** is a §14.3 lock blocker:

- Stratified by conversation (6 strata) and by LoCoMo question category,
  proportional allocation, seed 5005.
- `n` set by a power calculation at the §6.1 margin using the discordance rate
  measured in the §9 pilot — computed and committed **before any arm's outcomes
  are opened**, and never revised after.
- The subsample manifest and its content hash are committed before the first
  generation call.
- Every excluded item is excluded **mechanically by the seeded rule**, never by
  inspection. No category is dropped.

**Malformed records.** NF-004's six malformed evidence references are excluded
mechanically before scoring, as there. Not repaired, not imputed, not moved.

---

## 5. The shared instrument

This is the part that does not exist yet and is the study's real deliverable.

### 5.1 Reader

One model, one build, one prompt template, for every arm.

| | Tier A | Tier B |
|---|---|---|
| Reader | `gpt-4o-mini`, pinned dated version | `Qwen3.6-27B-UD-Q6_K_XL`, SHA-256 `f3b4a622…`, `llama-server.exe` SHA-256 `3827a6b6…` |
| Sampling | temperature 0, seed pinned where the API honours it | seed 5005, `--parallel 1`, no speculative decoding |

The prompt template is byte-identical across arms; **only the memory block
varies.** The template, its SHA-256, and one fully rendered example per arm are
committed before the first generation call.

**Prompts are reconstructed and hashed before inference**, carrying NF-008's
requirement. A rendered-prompt digest that does not match its committed value
stops the run.

### 5.2 Judge, and the endpoint that needs no judge

An LLM judge is a surrogate for correctness and must be treated as one.

**Primary judge.** One model, fixed across arms, with a registered rubric.

- **Blind.** Judges see answer text only. Arm labels, memory blocks and ordering
  are stripped. Presentation order is a seeded shuffle across the whole pooled
  set, committed before judging.
- **Calibrated before use**, per `experiments/audits/scoring_integrity/`:
  planted `NO_ANSWER` items (which must score 0 — §7 forbids scoring an
  answerless item above zero) and planted correct-but-unsupported answers. A
  judge that scores a planted `NO_ANSWER` above zero is unfit and the run stops.
- **Rationale required for every judgment**, committed with the score.

**Deterministic co-endpoint, computed for every answer.** Normalized containment
of the gold answer string — casefold, Unicode NFKC, whitespace and punctuation
collapse, with a registered numeric and date normalizer. **No model.** This
endpoint is weaker (it misses correct paraphrase) but it cannot be flattered by
a judge, and it is byte-reproducible.

**Both are computed on every answer and both are reported.** If the two
endpoints disagree in the **sign** of the primary contrast, the disposition is
`INSTRUMENT_DISAGREEMENT` and no directional claim is made (§7). This is a
stopping condition, registered before the run, precisely because a
judge-favourable and containment-unfavourable result is the shape a surrogate
failure would take.

**Judge fitness audit.** A seeded stratified audit sample (across arms and
across judged-correct / judged-incorrect) is independently re-rated following
DMR-004's two-rater precedent — the implementing agent plus the carried local
model, adjudicated by a rule fixed before any rating (DMR-004 reached finite
kappa 0.770 this way). **Neither rater is human**, and the report must say so;
DMR-004's own paper section had to be corrected once for describing them
otherwise. A pre-registered minimum agreement below which the judge is declared
unfit — and the study falls back to the containment endpoint alone — is a §14.3
lock blocker.

### 5.3 Budget matching

The resource under contention is delivered context. **Primary: matched
delivered-character budget of 16,000 characters**, NF-004's confirmed operating
point, measured on the serialized memory block by `len()` on the exact string
handed to the reader. A1 `FULL_CONTEXT` is exempt by definition and labelled as
the unbudgeted ceiling.

Each system fills that budget **in its own native selection order**, truncating
at the cap. Nothing is reordered to help any arm.

**A registered secondary at native defaults**, equally committed, runs every
arm at its own out-of-the-box configuration — Mem0's default `top_k`, the
component's shipped budget. Both are locked now and both are reported.

**PF9 note, recorded because it cuts both ways.** Budget matching can favour
either side. Mem0 typically returns a payload far smaller than 16,000
characters; forcing it to fill the cap means requesting more memories than it
would normally return, which can *hurt* it with noise. Leaving it at its default
gives the component roughly eight times the payload. There is no neutral choice,
which is why both are pre-committed and neither may be reported alone.

### 5.4 Replication, and measuring this instrument's own band

The 3.0-point band measured on the internal 13-point rubric (five identical
replicates scoring 8/8/8/8/11 — a switch, not a spread) does **not** transfer to
this instrument, and this study may not assume it does in either direction.

- **R ≥ 5 identical replicates per arm per item**, R odd, carrying Study 011
  Amendment 001's established minimum. Exact R is a §14.3 lock blocker.
- **Per-item primary outcome is the majority across replicates.**
- **The per-item unanimity rate is reported as this instrument's measured band**
  — a number this study produces about itself, per arm, before any contrast is
  interpreted. `AGENTS.md` §4: revalidate every carried subsystem at this
  study's scale. A carried band is not a measured one.
- Replicate schedule is registered in advance. Pairing is by schedule position,
  never by choosing a favourable run.

### 5.5 The embedder confound

A2, A3 and A4 all embed. If each uses its own default, the contrast is
memory-architecture **plus** embedder quality, and the study cannot separate
them. Mem0 defaults to an OpenAI embedding model; this component is pinned to
`Qwen3-Embedding-0.6B-Q8_0` at SHA-256 `06507c7b…`.

**Primary: one embedder for every arm that embeds** — the pinned local Qwen3 —
so the contrast is the memory architecture alone. Mem0 supports a configurable
embedder, so this is a supported configuration rather than a patch, and `G3`
verifies the release diff is empty either way.

**Registered secondary at each system's default embedder.** Under Tier A this
secondary is also what `G-CTRL` must run, because reproducing a published number
means reproducing the published configuration, embedder included. That produces
a stated asymmetry rather than a hidden one: **fidelity is established on the
default embedder, and the primary contrast runs on the shared one.** Both are
reported, and the report says which number came from which.

There is positive evidence that the embedder is not a neutral component here:
the same pinned embedder given the same text under a different call shape
returns a vector agreeing to cosine 0.999837 that still flips 6 of 146 committed
selection payloads. An embedder swap between arms is a much larger perturbation
than that.

---

## 6. Endpoints and statistics

### 6.1 Primary

Per item `i`, arm `a`: `y[i,a] = 1` if the majority of R replicates are judged
correct, else `0`.

Primary contrast is **A2 `CDW_PAIR` against A3 `MEM0`**, paired over the locked
`n` items. Report discordant counts `b` (A2 correct, A3 not) and `c` (A2 not, A3
correct), net, ratio, and the exact McNemar binomial p-value.

**Retention**, the operationalization of §9's question:

```
retention = ( acc(A2) − acc(A0) ) / ( acc(A3) − acc(A0) )
```

Normalized by the A0 floor because an uncorrected accuracy ratio credits both
memory layers with whatever the reader already knew.

**One interval method, registered for both quantities:** bootstrap over items,
10,000 resamples, seed 5005, percentile CI at 95%. Used for the paired
difference `δ̂ = (b − c) / n` and for retention. If `acc(A3) ≤ acc(A0)` the
retention denominator is non-positive, retention is **undefined and is reported
as undefined**, never clipped or substituted; disposition then reads `δ̂` alone
and the report states that the competitor arm did not clear the floor.

### 6.2 Registered secondaries — none may set disposition

- Deterministic containment endpoint, on the same contrast (§5.2) — except in
  its one disposition-bearing role: sign disagreement stops the study (§7).
- **Evidence availability at 16,000 characters**, joined to NF-004's committed
  per-item outcomes by canonical QA hash. This is the bridge between the two
  measurement worlds and the most interesting secondary in the study: it says
  whether availability predicted answers *this time*, after LV-001 found it did
  not. It carries no disposition.
- A2 and A4 (is the component better than naive chunked retrieval); A3 and A4
  (is Mem0); every arm against A1 ceiling and A0 floor.
- Per-conversation and per-category breakdowns.
- Native-default-configuration replication of the primary contrast (§5.3).

### 6.3 Cost: measured here, not cited — and carrying no disposition

Every arm's model client is wrapped in a counting shim. Reported per arm:
generative calls at ingest, generative calls at query, prompt and completion
tokens, wall-clock ingest time for the full corpus, and per-query latency
distribution.

**The component's zero is architectural, not empirical.** It is arithmetic on
the code path and it is not a finding; no disposition tier reads it. What is
empirical, and worth the instrumentation, is the *observed* count for Mem0 on
this corpus against the `1 + n` per message pair its paper describes — a
description this study is in a position to check.

Two comparisons are **forbidden** in the report even though both numbers will
exist: the component's 190 ms selection latency against Mem0's 1.44 s p95 total
(selection excluding embedding on one machine, versus end-to-end including
generation — not the same quantity), and any cost figure presented as a
performance result.

---

## 7. Disposition — every tier registered now

Fixed before any outcome exists, per §9.3. `δ̂` and its CI are from §6.1;
`δ_NI = 5` percentage points absolute.

| Disposition | Condition |
|---|---|
| **EXCEEDS** | 95% CI lower bound on `δ̂` **> 0** — the zero-call path beats the competitor |
| **PARITY** | 95% CI lower bound on `δ̂` **≥ −δ_NI** and not `EXCEEDS` — non-inferior at the registered margin |
| **SUBSTANTIAL_RETENTION** | retention point estimate ≥ 0.75 **and** its CI lower bound ≥ 0.50, and not `PARITY` — the lower registered tier |
| **DOES_NOT_SURVIVE** | retention CI upper bound < 0.50, **or** `acc(A2) ≤ acc(A0)` |
| **INSTRUMENT_DISAGREEMENT** | judged and containment endpoints disagree in the sign of the primary contrast — **no directional claim, at any tier** |
| **INSTRUMENT_FAILURE** | any gate in §8 stops the run |

**`EXCEEDS` would not mean the component is better than Mem0 in general.** It
would mean: on this corpus, at this budget, under this reader and judge, at this
Mem0 configuration. §13 governs how it may be written.

**`DOES_NOT_SURVIVE` is a result, not a defeat**, and §9's framing is registered
here so it cannot be applied after the fact: a mechanism that recovers most of
the layer and still loses head-to-head is a finding, and reporting it as a
failure throws the finding away. The retention number *is* the finding, whatever
its value.

**PF4 reachability is a lock blocker (§14.3), not a claim.** The tier boundaries
above are stated at plausible values; whether each is reachable in each direction
at the locked `n` and the pilot-measured discordance rate must be demonstrated
per bar — `DMR_001`'s precedent is a locked bar that was unreachable by
construction, and the standing rule from it is *reachability per bar, not per
statistic*. If any tier proves unreachable, the boundary changes **before** the
lock or the tier is removed. It may never change after.

---

## 8. Gate order

Gates execute in order and stop on first failure. No outcome is opened before
`G6`.

| # | Gate | Stops unless |
|---|---|---|
| **G0** | Registration identity | The runner carries this file's locked LF SHA-256 and first-commit SHA |
| **G1** | Source and population | Dataset hash, split manifest, canonical QA identities and the committed subsample manifest all match |
| **G2** | Leakage | Grep and import-graph checks prove no arm's memory code can read `qa.answer`, `qa.category` or `qa.evidence`. A planted forbidden import must fail |
| **G3** | Arm fidelity | Each arm is the frozen thing it names: A2 reproduces NF-004's committed selection payloads by SHA-256; A3 is the pinned Mem0 version, unpatched, with its diff against the release empty; A4's chunker matches its spec |
| **G-CTRL** | **Competitor reproduction (Tier A only)** | The A3 pipeline reproduces Mem0's published LoCoMo J-score within a registered tolerance. **Tier B: unavailable — recorded as such, never as passed** |
| **G-FLOOR** | Contamination | `acc(A0) < 0.60 × acc(A1)`. Above that the reader answers most items without the conversation and no memory layer is discriminable — `INSTRUMENT_FAILURE` |
| **G4** | Judge fitness | Calibration planted items score as registered; planted `NO_ANSWER` scores 0; audit-sample agreement clears its registered minimum |
| **G5** | Determinism, honestly bounded | A2's *selection* payloads are byte-identical across two processes. **Generation is not asserted to be reproducible** — the runtime is not bit-reproducible and §5.4's replicates measure that rather than assume it away |
| **G6** | Run | All arms, all replicates, one sealed outcome artifact per arm before any judging |
| **G7** | Result integrity | Totals recomputed from rows; call counts verified against §6.3's shim; both endpoints computed; disposition table applied **once** |

**`G-CTRL` is the gate this study turns on.** Without it, a low A3 score cannot
be attributed between *Mem0 loses* and *our rig ran Mem0 badly*, and §9.2
requires a report to say which. `AGENTS.md` §4 puts it plainly: a gate is
trusted to stop only after its tested population and its non-stopping branch are
shown capable of existing.

---

## 9. Preflight Part 1 — Exploration

**Status: NOT EXECUTED.** This section is the work order, not a record. `AGENTS.md`
§4: *characterize the mechanism empirically before designing a test of it — not
by reading the code, not by trusting its name, not by citing a prior study.*
Findings here may change the design before anything is locked, and that is the
point.

1. **Mem0's behavioural identity in one falsifiable sentence.** Install the
   pinned version, ingest one LoCoMo conversation, and record what it actually
   does: how many generative calls, of what kind, with what prompts, producing
   how many memories of what median length. The `1 + n` figure in
   `COMPETITIVE_LANDSCAPE.md` is read from Mem0's paper. **It has not been
   observed here.** Confirm or correct it.
2. **Name-to-behaviour check on every configurable Mem0 knob** the study touches
   — `top_k`, the extraction prompt, the update policy, the vector store, the
   embedder. The programme has been wrong about the behaviour behind a name
   four times (the N tier alone carried three rules under one word), and never
   once because the name looked suspicious.
3. **Payload-size distribution, not a summary**, for A2, A3 and A4 at native
   defaults. §5.3's budget-matching argument rests on Mem0's payload being much
   smaller than 16,000 characters. Measure it.
4. **Contamination probe.** Run A0 on a small seeded sample and measure it
   directly. `G-FLOOR` is a stopping condition; discovering it fires after
   building the full rig wastes the rig.
5. **Judge behaviour on planted items** before it judges anything real.
6. **Timing pilot.** One conversation end to end, all five arms, R replicates,
   with wall clock. This produces the feasibility number that sets `n` (§4) and
   is the difference between a runnable study and one that stops at 40%.
7. **Discordance-rate pilot** on a seeded slice disjoint from the primary
   subsample, sized to inform §7's power calculation without opening the
   primary contrast.
8. **Degenerate and absorbing states, on a real trace:** what Mem0 does with an
   empty store, with a query matching nothing, and at the truncation boundary;
   what the component does when the budget exceeds the whole store (NF-004's
   96k ceiling behaviour, re-checked at this budget).

---

## 10. Preflight Part 2 — Checklist

Every item is answered explicitly. `AGENTS.md` §4: *"Assumed" is not an answer;
"verified at `<SHA>`" is.* **Nothing below is verified yet.** The status column
is the honest state of a draft, and each row names what closes it.

| # | Check | Status | Closes when |
|---|---|---|---|
| **PF1** | Inputs exist | **OPEN** | LoCoMo bytes re-verified against the committed SHA-256; Mem0 version pinned by PyPI version *and* git SHA, with its licence read and recorded; Tier A API model version pinned, or Tier B declared |
| **PF2** | Mechanism identity | **OPEN** | §9 items 1–3 executed and committed; A2 verified as NF-004's frozen `P_PAIR_RANK` by payload SHA-256, not by name |
| **PF3** | Gate ordering | **OPEN** | Planted tests prove each gate in §8 is unreachable-past after failure; `G-CTRL` and `G-FLOOR` proven to execute before `G6` |
| **PF4** | Thresholds achievable | **OPEN — highest risk** | Every tier boundary in §7 shown reachable **per bar**, in both directions, at the locked `n` and pilot discordance rate. DMR-001 locked a bar unreachable by construction; the rule from it is per-bar, not per-statistic |
| **PF5** | Comparison keys stable | **PARTLY SATISFIED** | Canonical QA hash carried from NF-004 and content-based. Still to close: a stable key for a *generated answer*, since Mem0 assigns its own memory ids and the reader emits free text |
| **PF6** | Reproduction anchor | **OPEN** | A2 replays NF-004's committed selection payloads by digest; Tier A additionally reproduces Mem0's published score at `G-CTRL` |
| **PF7** | Absorbing state | **OPEN** | Mem0's update policy has feedback — a stored memory affects later ADD/UPDATE/DELETE/NOOP decisions. Demonstrate on a real trace of full conversation length whether ingestion reaches a fixed point or oscillates |
| **PF8** | Ablation length | **OPEN** | State what the locked `n` can and cannot detect. It cannot detect: transfer to another reader, another corpus, another Mem0 configuration, or any effect smaller than the measured §5.4 band |
| **PF9** | Surrogate audit | **DRAFTED — §11** | Residuals recorded and carried into the report |
| **PF10** | Live evaluation | **SATISFIED BY CONSTRUCTION** | This study *is* the live evaluation NF-004's PF10 demanded. Its own mirror applies: an accuracy result on this corpus authorizes no deployment claim |

---

## 11. Surrogate audit (PF9), drafted

`AGENTS.md` §3 asks whether a gate can pass while the property it certifies is
false. §9.4 requires the mirror too. Both, per instrument:

| Instrument | Can pass while the property is false | Can fail while the property is true |
|---|---|---|
| **LLM judge** | Rewards fluent, confident, unsupported answers; A0's floor is the partial correction and the containment co-endpoint is the rest | Penalizes correct answers in unexpected form; containment is worse at this, which is why the *sign* rule (§7) needs both, not either |
| **Containment** | Gold string appears inside a wrong or contradictory answer | Correct paraphrase, or a differently formatted date or number, scores 0 |
| **Majority-of-R** | Hides a bimodal arm that is right 3/5 and catastrophically wrong 2/5 — §5.4's unanimity rate is the residual that exposes it | A genuinely improved arm sitting just under 50% per-replicate reads as unchanged |
| **Matched budget** | Advantages whichever system's native payload is closer to the cap (§5.3) | Handicaps a system whose selection degrades when forced to fill |
| **Retention** | Denominator near zero inflates it without limit — §6.1's undefined rule is the guard | A0 contamination shrinks both numerator and denominator and compresses real differences |
| **G-CTRL** | Reproduces a published aggregate while differing per item — an aggregate match is weaker evidence than it looks | Fails on genuine version drift in Mem0 or the vendor model, which is a real reproduction finding and not this rig's fault; §9.2 requires the report to say which |

**Two residuals that no gate here removes**, carried into the report by
requirement:

1. **Both arms' configurations were selected on LoCoMo** (§2.3). Neither is an
   unbiased estimate for its system. The biases plausibly point the same way and
   this study does not measure them.
2. **Availability and accuracy are different properties**, established by LV-001
   on this programme's own corpus. §6.2's availability secondary is the direct
   test of whether that gap reappears here — and whichever way it lands, it does
   not license reinterpreting NF-004.

---

## 12. Leakage

Carried unchanged from NF-004 and extended to the new arms.

- Memory code in **every** arm receives conversation text, candidate identities,
  session membership, source order, question text, vectors and budget. It must
  not read `qa.answer`, `qa.category`, `qa.evidence` or dialogue `dia_id`.
- Mem0's ingestion is fed the conversation **only**. Questions are supplied at
  query time, as in its published protocol.
- Evidence joins exist only in the measurement module, after every arm's outputs
  are frozen.
- The judge never sees arm labels, memory blocks or the gold answer's source
  location — only the answer text, the question, and the gold answer.
- A planted forbidden import must fail the build.

---

## 13. What this study may not claim under any outcome

Written as prohibitions so they can be grepped, following
`COMPETITIVE_LANDSCAPE.md` §5, which stays in force except where this study
supplies the missing instrument.

| Forbidden | Why |
|---|---|
| Any comparison against Mem0 **as published**, from a Tier B run | Substituted substrate. EC-001's precedent and Amendment 010's rule, applied in advance (§2.2) |
| Any claim that the corpus-selection bias cancels between arms | Both arms were tuned on LoCoMo; the biases are plausibly similar in direction and are **not measured here** (§2.3) |
| Any generalization beyond this reader, judge, budget, corpus and pair of configurations | One reader, one judge, one corpus, `n` items, R replicates |
| `CONFIRMATORY` standing for any HH-001 result | LoCoMo is exhausted. This is `REGISTERED`. Confirmation is HH-002 on a sealed corpus (§2.3) |
| Any cost figure reported as a performance result, or the 190 ms placed against Mem0's 1.44 s | Different quantities (§6.3) |
| "Zero inference calls in the memory path" | Withdrawn. `DO_NOT_WRITE.md` item 1. The claim is **no generative calls**; an embedding model is resident |
| Any novelty claim for the mechanism | `DO_NOT_WRITE.md` §4; the programme's papers do not call their own contribution novel |
| Reporting `DOES_NOT_SURVIVE` as a dead end without its retention number, CI and named successor | §9 and §9.1: a stop closes a design, not a question |
| Reporting `EXCEEDS` without the §11 residuals and the §5.3 budget asymmetry | §9.4's mirror. The upward error is the one this programme's own review cycles found it makes |
| Introducing any disposition tier, margin or bar after a number is on the table | §7 `Never`, §9.4. Both tiers exist now or neither does |

---

## 14. Open decisions that block the lock

The first two are the user's. The rest are the agent's, closed by executing §9.

### 14.1 Tier A or Tier B — *user decision*

Tier A commits the programme to a paid external API and its first dependency on
a vendor model, and it is the only path that permits any sentence about Mem0 *as
published*. Tier B costs nothing, keeps the repository self-contained, and yields
a narrower but genuine result. **A third option exists and should be named:
Tier A for `G-CTRL` alone** — reproduce Mem0's published number with the vendor
model to establish fidelity, then run the head-to-head on the local substrate for
every arm. That buys the attribution `G-CTRL` provides at a fraction of Tier A's
cost, and its own weakness must be registered if chosen: fidelity is then
established on a substrate the comparison does not use.

### 14.2 Scope of the competitor set — *user decision*

This draft registers Mem0 alone (§3). Adding Mem0ᵍ, Zep/Graphiti or A-MEM makes
the paper's positioning section far stronger and multiplies the number of places
a misconfigured competitor can be reported as a mechanism result. The
recommendation is Mem0 alone for HH-001.

### 14.3 Values this draft names only by rule

Each is a parameter, and `AGENTS.md` §4 requires parameters to live here as
values before the lock:

- `n`, the subsample size (§4) — set by power calculation on §9's pilot.
- `R`, replicates per arm per item (§5.4) — ≥ 5, odd, set by §9's timing pilot.
- `G-CTRL`'s reproduction tolerance (§8) — proposed ±5 percentage points
  absolute against 66.88%; requires a defensible basis, not a round number.
- `G-FLOOR`'s contamination threshold (§8) — proposed `acc(A0) < 0.60 × acc(A1)`;
  §9 item 4's probe measures whether that boundary discriminates anything on this
  corpus and reader, and the value moves before the lock if it does not.
- The judge-audit minimum agreement (§5.2).
- A4 `RAG_FIXED`'s chunk size, overlap and `top_k` (§3) — a control that is
  tuned is not a control, so these are fixed by a stated convention and never
  adjusted after seeing A4's score.
- PF4 reachability demonstrations for every tier in §7 (§10).

### 14.4 Not a blocker for HH-001, recorded so it is not forgotten

HH-002's sealed corpus (§2.3). LongMemEval-S is exhausted. Identifying an unread
corpus, locking it before any outcome is computed, and deciding whether the
component's configuration may be carried unchanged onto it are HH-002's problems.
Recording them now costs nothing; discovering them after HH-001 reports would
cost the confirmation.

---

## 15. Deliverables and layout

```text
experiments/comparisons/hh_001/
  HH_001_PRE_REGISTRATION.md      this file; the anchor once locked
  HH_001_PREFLIGHT_REPORT.md      §9 Part 1 findings and §10 Part 2 closures
  HH_001_SPRINT_PLAN.md           execution plan, written after the lock
  amendments/                     standalone; the locked file is never edited
  artifacts/
    subsample_manifest.json       seeded item selection, hashed
    arm_fidelity/                 G3 evidence per arm
    g_ctrl/                       competitor reproduction evidence
    runtime/                      model, build and server hashes per §5.1
    outcomes/                     one sealed artifact per arm, pre-judging
    judging/                      blinded surface, sealed mapping, rationales
    cost/                         §6.3 call and token counts
  HH_001_REPORT.md                result, dispositions, §11 residuals
```

**Close checklist** (`AGENTS.md` §6): report carrying the registration SHA;
root `README.md` both halves; `AGENTS.md` digest entry at ≤ 400 characters;
`ERRATA.md` if any published number moves; memory files; all logs and scoring
artifacts committed; PR.

**The paper's positioning sections change only after this study reports.**
`paper/notes/COMPETITIVE_LANDSCAPE.md` §5 and `DO_NOT_WRITE.md` item 35 stay in
force until then, and a passing HH-001 relaxes exactly the sentences its
instrument supports and not one more.

---

## 16. Stops and exclusions

Stop without a result on: any failed gate; a changed input hash; a leakage
violation; a Mem0 version or vendor model version that differs from the pin; a
judge that fails calibration; a rendered prompt whose digest does not match its
committed value; a call-count shim reporting generative calls in the A2 memory
path. Record in every case whether **the mechanism failed or the instrument
could not test it** (§9.2).

No retuning, alternate budget, alternate reader, alternate judge, added
competitor arm, changed margin, changed disposition boundary, category exclusion,
answer repair, or promotion claim is authorized. Any such change requires a
standalone amendment committed **before** its affected outcome is opened — or, if
it adds a factor, a new study.
