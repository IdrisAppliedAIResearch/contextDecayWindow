# TC-001 — Does the tiered stack beat the flat arm?

**Document type:** Study pre-registration
**Status:** `REGISTERED — bars locked before either arm's availability was computed`
**Standing sought:** `REGISTERED-OFFLINE` — pre-registered, zero generative calls,
byte-exactly replayable against a retained embedding cache, on a corpus already
observed. It is capped as characterization and **cannot** be `CONFIRMATORY`;
`TC_ARC_ROADMAP.md` §0.1 records why.
**Date:** August 22, 2026
**Branch:** `study/tc-arc-tier-cost`
**Arc:** `TC_ARC_ROADMAP.md` §2. This document closes roadmap §10 decisions 1 and 3
for this study only.
**Predecessors:** NF-004 (`PAPER_002.md` §6.1), HH-002 (§5.1), EC-002 (§9.1),
IC-001 (§9.2), DR-002 (§8.2), LV-001 (§12).

---

## 0. What this is, and what it is not

HH-002 scored **79.09%** on the harness behind arXiv:2504.19413's Table 2, above
every row of it. The arm that did it was `CdwArm`: rank adjacent-turn pairs by
cosine, pack a character budget, stop. No recency tier, no K threshold, no
candidate pool, no coverage selector, no clustering.

The deployed library is none of those things. It is four tiers filled in a fixed
order, and the arc's measured pathologies all live in that machinery.

**This study asks the root question and nothing else: over one store, one query
set and one budget, does the tiered path put more answer-bearing text in the
window than the flat path?**

It is **not** a tuning study, **not** a decomposition of which tier is
responsible — that is TC-003 — and **not** a reader study. §9 states what a
result here cannot support.

## 1. The question

> Holding the candidate set, the vectors, the renderer, the cost accounting and
> the budget identical, does `episodic.build_context` deliver a question's
> evidence more often than a flat cosine ranking packed to the same budget?

## 2. Corpus, unit and budget

**Roadmap §10 decision 1, taken here and written down before any bar.**

**Corpus — LoCoMo development.** The four conversations reserved by
`experiments/external/locomo/LOCOMO_CORPUS_LOCK.md`: `conv-41`, `conv-42`,
`conv-47`, `conv-48`. 1,365 adjacent-turn pairs, 882 question records, 871
unique by content, 868 with fully resolvable evidence.

Chosen over the internal 121-turn store for one reason that is not preference:
**power**. The internal store offers 17 enumeration items and 21 targeted items
across 13 questions. A paired sign test on that population cannot separate a
real effect from none, and locking a bar on it would repeat DMR-001's `PF4`
defect. LoCoMo development supplies 868 paired questions with per-item evidence
labels that need no model to read.

Its cost is stated plainly: LoCoMo development is **spent** — it was opened for
NF-003's successor exploration and its outcomes have been seen at other
granularities. That caps this study at `REGISTERED-OFFLINE` and no result here
may be reported as confirmation. Acquiring a new sealed corpus is roadmap §10
decision 2 and is not a dependency of this study.

**Unit — the adjacent-turn pair.** NF-004's confirmed unit on this corpus, and
`CdwArm`'s own unit. Both arms are offered the identical 1,365 pair identities
with identical vectors; nothing about the unit differs between arms.

**Budget — 16,000 characters, primary.** Three reasons, all fixed before any
TC-001 number existed:

1. It is the flat arm's **own shipped operating point** — HH-002's
   `commitments.json` records `component_budget_chars: 16000` — so the flat arm
   enters at the configuration that produced the 79.09%.
2. At 32,000 characters this endpoint is **near ceiling on this corpus already**.
   The committed `development_analysis.json` records own-cosine pair ranking at
   855 of 871 on any-evidence and 826 of 868 on complete evidence under raw-text
   packing. A ceiling is a `PF4` reachability problem, not a matter of taste.
3. NF-004's confirmatory run used 16,000.

**32,000 characters runs as a registered secondary with no bars**, so the
deployed budget is measured rather than left unmeasured.

## 3. Arms

Both arms are pure functions of (store, query, budget). Both are offered the same
1,365 candidate identities and the same vectors from the same read-only cache.

| | **A_FLAT** | **A_TIERED** |
|---|---|---|
| Selection | Every candidate ranked by its own cosine to the query, descending | Recency window (N = 32), then K-threshold hits (cosine ≥ 0.48), then A3 cluster-diversity coverage over the full pool |
| Order offered to the packer | Cosine descending, ties by `(session_order, pair_order)` | Recency first, then K, then coverage — the shipped N-first order |
| Implementation | `hh002_arms.rank_pairs`'s ordering, asserted equal to it | `episodic.build_context`, unmodified |
| Packer | `episodic._packing.pack_stm_payload` with an empty N tier | `episodic._packing.pack_stm_payload` |
| Renderer | The DR-001 renderer | The DR-001 renderer |
| Cost | Exact serialized characters, skip on overflow | Exact serialized characters, skip on overflow |

**Held identical:** store, candidate identities, vectors, embedder
(`06507c7b…`, solo call shape), renderer, packer, drop policy, budget,
measurement code, seed 5005.

**The single difference is which candidates each path chooses and in what order
it hands them to the serializer.**

### 3.1 Two deliberate departures from `CdwArm` as HH-002 ran it

**The flat arm renders through the DR-001 renderer, not `BLOCK_SEPARATOR`.**
`CdwArm` packs raw pair text; the library packs XML episode elements costing a
measured 68 characters more each at the median — 305 against 237, so about a
quarter more cost per candidate. Letting the flat arm pack raw text while the
tiered arm pays XML would hand it roughly a quarter more content per byte, and
the study would be measuring rendering overhead rather than tier logic. Both arms
render identically. This makes the flat arm *not* a reproduction of HH-002's
79.09% configuration, and no number here should be read as one.

**The flat arm's `recent_context` block is empty, which is 18 characters
cheaper** than the tiered arm's two non-empty blocks (52-character wrapper
against 70). That is 0.11% of the budget, and §6.1's measured band bounds its
effect directly: the sham perturbations move the budget by ±80 and ±160
characters, four to nine times further. A registered robustness check in §8
repeats the primary with the flat arm charged the missing 18 characters.

## 4. Endpoints

Evidence availability, read off the delivered block by candidate identity. No
inference, no judge, no reader, no string matching against an answer key.

**Primary — complete evidence delivery.** For each question, whether *every*
pair carrying one of its resolved evidence dialogue ids is present in the
delivered block. Population: the 868 unique development questions with at least
one resolved evidence id and no unresolved ones. NF-004's headline endpoint on
this corpus.

**Secondary, no bars:**

- Any-evidence delivery, over all 871 unique questions with ≥1 resolved id.
- Both endpoints at the 32,000-character secondary budget.
- **Delivered composition by tier** for `A_TIERED` — recency, K and coverage
  counts — and, when evidence arrived, **which tier carried it**. `PAPER_002.md` §9.1
  records that the medians concealed all of it; composition is where
  IC-001's failure was visible and the aggregate was not.
- Delivered episodes and delivered characters, per arm, as distributions.
- Per-conversation (4) and per-LoCoMo-category (5) breakdowns.
- **The discordant pairs themselves, pre-specified so the reading is not
  chosen afterwards.** For each gain, which tier of `A_TIERED` carried the
  evidence. For each loss, the rank the evidence held in the flat cosine order
  and whether it was dropped for budget or never reached. NF-003 found that its
  63 coarse-rank rescues had median own-cosine rank 46 against 10 for the fine-
  rank gains; the same cut is registered here before the split is known.

## 5. Preflight Part 1 — what the two paths actually do

Run before any bar below was written. Artifacts:
`artifacts/tc001/preflight/tc001_preflight_part1.json` and
`artifacts/tc001/preflight/tc001_preflight_pf4_reachability.json`.
Code: `src/analysis/tc001_exploration.py`, `src/analysis/tc001_reachability.py`.

**Neither artifact contains either arm's absolute availability**, and the
reachability artifact refuses at runtime to carry a directional key. The band in
§6 is derived from within-arm sham perturbations; the reachability check reports
only how many questions the arms disagree on, never which way.

### 5.1 Behavioral identity, in one falsifiable sentence each

**A_FLAT** delivers the highest-cosine candidates that fit, and nothing else.

**A_TIERED** delivers the last 32 pairs of the conversation regardless of the
query, then spends what remains of the budget on high-cosine and cluster-diverse
candidates.

### 5.2 Name-to-behavior — every named part, tested

| Name | Claim | Measured |
|---|---|---|
| `recency_window_n` | The last N episodes | `TRUE` — the delivered recency set is exactly the last 32 in store order, and is identical across 25 different queries. **On this corpus the library's N tier is a real window**, unlike the least-recently-delivered rotation that carried the name through eleven live studies |
| `k_threshold` | Candidates at cosine ≥ 0.48 | `FIRES` — see §5.3. It is not inert here, which is the opposite of IC-001's finding on the internal store |
| `candidate_policy` | `full_store` considers the whole store | `TRUE` — pool size equals the candidate count on every question |
| A3 coverage selector | Cluster-diversity selection over the pool | `RUNS` — see §5.3 for how often it lands anything |
| `flat_order` | `CdwArm`'s ranking | `PASS` — asserted equal to `hh002_arms.rank_pairs` on committed data, order digest recorded |

### 5.3 Distributions, not summaries

**Candidates.** 1,365 pairs; per-conversation pool 323 to 355. Pair text is p50
237 characters (p05 77, p95 452, max 734). The rendered element is p50 305
(p95 520, max 802): the DR-001 renderer adds p50 **68** characters per candidate,
min 66, max 76. The empty two-block payload costs 35.

**The K threshold is not inert on this corpus.** Zero of 871 questions have no
candidate at cosine ≥ 0.48; the count per question is p05 9, p50 84, p95 263,
max 323, and the best cosine available is p50 0.694 (min 0.513). **This is the
opposite of IC-001's finding on the internal store, where the same threshold
delivered zero episodes at 8 of 8 probes.** The tiered arm enters this study with
a working similarity path, which is the condition under which it has the best
chance of winning.

**At 16,000 characters the recency window takes 32 of 32 on every one of the 871
questions and 61% of the delivered characters** (p05 0.572, p50 0.629, p95
0.648). K lands p50 22 episodes (min 1, max 30) and is never zero. **Coverage
lands nothing on 722 of 871 questions — 82.9%** (p50 0, p95 12, max 35). The
tiered arm drops p50 57 episodes and up to 266.

**The two arms deliver the same amount and not the same thing.** Tiered p50 54
episodes in 15,961 characters; flat p50 54 in 15,969. The Jaccard overlap of
their delivered sets is p05 0.078, **p50 0.215**, p95 0.375, max 0.506. Equal
counts, one-fifth shared content — a difference an aggregate would conceal
entirely, which is `PAPER_002.md` §9.1's exact lesson.

**At 32,000 the arms converge.** Recency share falls to p50 0.315, K lands p50
64, coverage is still empty on 420 of 871 (48.2%), and Jaccard rises to p50
0.588. That convergence is a second reason the tighter budget carries the bars:
the looser one measures a smaller contrast on an endpoint already near ceiling.

### 5.4 Degenerate and absorbing states

Neither path has feedback: both are pure functions of (store, query, budget), no
output influences a later input, and no state persists between questions. `PF7`'s
absorbing state therefore cannot arise, and this is a structural fact rather than
an empirical one.

The degeneracy that *can* arise is a **constant output** — an arm whose delivered
block stops depending on the query because a fixed tier consumes the budget. That
is checked directly, on every question of every conversation:

| Conversation | Questions | Distinct flat sets | Distinct tiered sets |
|---|---:|---:|---:|
| `conv-41` | 193 | 193 | 193 |
| `conv-42` | 260 | 260 | 239 |
| `conv-47` | 190 | 190 | 186 |
| `conv-48` | 228 | 228 | 228 |

**Neither arm is constant.** The flat arm returns a different delivered set for
every one of the 871 questions. The tiered arm collides on 25 of 871, all inside
two conversations — which is what a design that spends 32 of its ~54 delivered
episodes on a query-independent window should do, and is reported rather than
smoothed away. The tiered arm delivered recency-only on **0 of 871** questions at
both budgets, so the internal store's total starvation of the later tiers does
not reproduce here.

### 5.5 Cost

At pool sizes of 323 to 355 and a 16,000-character budget, per-query wall clock
over 40 timed questions per conversation:

| Conversation | Pool | Tiered p50 | Flat p50 |
|---|---:|---:|---:|
| `conv-41` | 340 | 93.2 ms | 13.4 ms |
| `conv-42` | 323 | 102.3 ms | 13.7 ms |
| `conv-47` | 355 | 89.5 ms | 15.9 ms |
| `conv-48` | 347 | 96.4 ms | 15.6 ms |

**The tiered path costs about 6.5× the flat path per query** at roughly a third
of `PAPER_002.md` §10's 1,000-candidate measurement. Descriptive, carried here
because it is measured in passing; latency is TC-005's question and no bar in
this study touches it.

## 6. Bars — locked here, before either arm's hit count exists

### 6.1 The null band, measured

Each arm compared **against itself** at a nudged budget, on the primary endpoint,
over 871 questions — the same three-question superset of the registered
population that §7.1 records, for the same reason and with the same consequence,
which is none at this magnitude. A budget moved by half a percent carries no
mechanism claim, so whatever paired movement it produces is what this endpoint
does at a packing boundary rather than what an architecture does.

| Perturbation | Budget | Flat gains/losses (net) | Tiered gains/losses (net) |
|---|---:|---:|---:|
| −1.0% | 15,840 | 1 / 3 (−2) | 1 / 3 (−2) |
| −0.5% | 15,920 | 1 / 1 (0) | 1 / 1 (0) |
| +0.5% | 16,080 | 0 / 0 (0) | 2 / 0 (+2) |
| +1.0% | 16,160 | 0 / 0 (0) | 4 / 0 (**+4**) |

**B = 4 questions**, the largest |net| any sham perturbation produced within a
single arm at 16,000 characters.

Registered floor, stated before the measurement was read: if the measured value
had been 0, B would be set to 1 — the smallest difference the endpoint can
express — with the reason recorded rather than the band rounded up to something
comfortable. **The floor was not needed.** Roadmap §10 decision 3 required the
band be derived from a measured quantity and not chosen round; 4 is measured, and
it is the number the instrument produced rather than a number anyone picked.

Two things the table says that are worth stating rather than leaving in the
artifact. First, the flat arm barely moves — |net| ≤ 2, and exactly zero at both
positive nudges — while the tiered arm moves in both directions and as far as 4.
The tiered arm sits closer to packing boundaries, so the band is set by the arm that
is more sensitive to them, which is the conservative choice. Second, the
smallest perturbation measured is ±80 characters and moved the endpoint by at
most 2 questions; §3.1's wrapper asymmetry is **18** characters, 4.4× smaller
still. §8 measures it directly anyway.

At the 32,000 secondary budget the same procedure gives 6, driven entirely by the
tiered arm (the flat arm is 0 at all four perturbations). It is recorded for
completeness; no bar attaches to that budget.

### 6.2 The statistic

Per question, paired: `gains` = A_TIERED delivers complete evidence and A_FLAT
does not; `losses` = the reverse; `ties` = both or neither. `net = gains − losses`.

One-sided exact binomial (sign test) on the `d = gains + losses` discordant
pairs, `p = 0.5`:

- for the tiered direction, `p₊ = Σ_{i=gains}^{d} C(d,i) / 2^d`
- for the flat direction, `p₋ = Σ_{i=losses}^{d} C(d,i) / 2^d`

One primary endpoint, one budget, one population, one test. No multiplicity
correction is applied because none is earned; every other quantity in §4 is
descriptive and carries no bar.

### 6.3 Dispositions — both tiers registered before the run, per AGENTS.md §9.3

| ID | Condition | Verdict |
|---|---|---|
| **D1** | `net ≥ B` and `p₊ ≤ 0.01` | **TIERED_WINS** — the tiered stack delivers more evidence than the flat arm on this corpus at this budget |
| **D2** | `net ≥ B` and `0.01 < p₊ ≤ 0.10` | **TIERED_CARRIES_SIGNAL** — reported as signal with its margin and sample size; justifies a successor, not an adoption |
| **D3** | `net ≤ −B` and `p₋ ≤ 0.01` | **FLAT_WINS** — the tiers cost delivery on this corpus at this budget |
| **D4** | `net ≤ −B` and `0.01 < p₋ ≤ 0.10` | **FLAT_CARRIES_SIGNAL** |
| **D0a** | `|net| < B` | **NO_DIFFERENCE_ESTABLISHED — inside the band.** Explicitly *not* a win for the simpler arm. Simplicity is not entitled to a free pass |
| **D0b** | `|net| ≥ B` and both `p₊ > 0.10` and `p₋ > 0.10` | **NO_DIFFERENCE_ESTABLISHED — outside the band, not separable.** Margin, `d` and both p-values reported |

The table is exhaustive over the real line and every branch is reachable at the
discordant count §7.1's `PF4` probe measured. The lower tier exists only because it
is registered here; `AGENTS.md` §9.4 forbids applying one after a number is on
the table.

## 7. Preflight Part 2 — checklist

| # | Check | Answer |
|---|---|---|
| **PF1** | Inputs exist | `locomo10.json`, 2,805,274 bytes, SHA-256 `79fa87e9…`, matching `LOCOMO_CORPUS_LOCK.md`. Cache `locomo_dev_embeddings.db`, file SHA-256 `2ba61701…`, content SHA-256 `e103b293…`, 2,236 entries, covering all 1,365 pair texts and all 871 unique question texts. Part 1 recorded **2,247 hits and 0 misses** against it in read-only mode, so the corpus costs no model call. Counts: 4 conversations, 1,365 pairs, 882 question records, 871 unique, 868 evaluable for the primary. Every source file's SHA-256 is recorded in the run header |
| **PF2** | Mechanism identity | §5.2. Every named tier, threshold, pool policy and ranking function checked against its name on committed data, not inherited from a prior study's description |
| **PF3** | Gate ordering enforced | **G0**, the reproduction anchor, is a separate committed phase. The run phase refuses to open either arm's availability until `g0_reproduction.json` exists, is git-tracked, and reports `PASS`. The ordering is asserted in code and visible in git order — Study 011 ran its determinism check after scoring, and a gate that runs afterward is not a gate |
| **PF4** | Thresholds achievable | §7.1 |
| **PF5** | Comparison keys stable | Candidates key on `PairCandidate.identity` = SHA-256 of `(sample_id, session_id, dialogue ids, text)`. Questions key on SHA-256 of the canonical QA record plus a duplicate ordinal. Delivered episodes are read off the payload by the renderer's own `turn` attribute. No uuid, path, timestamp or run-generated identifier enters any comparison |
| **PF6** | Reproduction anchor | **G0** reproduces `experiments/external/locomo/artifacts/development_analysis.json` exactly from the same dataset and cache: `unique_question_strict_any` 820 → 855 with 44 gains and 9 losses, and `all_evidence` 773 → 826 with 71 gains and 18 losses. Reproduction is by identity and value, not by count alone: checked before this document was written, it reproduces **all 882 per-question rows byte-for-byte** as well as the per-conversation and per-category tables. G0 re-runs it as a committed, gating phase. **A failed G0 stops TC-001** |
| **PF7** | Absorbing-state proof | §5.4. Neither path has feedback, so no absorbing state exists to prove absent; the constant-output check that *can* fail was run on every question of every conversation and is reported |
| **PF8** | Ablation length adequate | Not applicable, and stated rather than skipped: this is a full-population offline replay over all 868 evaluable questions, not a sampled ablation. There is no length that could be inadequate. What it cannot detect is any behavior that emerges only past 1,365 candidates or past 32 sessions — `PAPER_002.md` §10's latency horizon is TC-005's question, not this one |
| **PF9** | Surrogate audit | §7.2 |
| **PF10** | Live-evaluation requirement | §9 |

### 7.1 PF4 — reachable, and failable

A paired sign test is decided entirely by its discordant pairs. If the two arms
never disagreed about whether a question's evidence arrived, no bar on that
contrast could fire in either direction — which is the defect DMR-001 locked and
`PF4` exists to catch.

`tc001_preflight_pf4_reachability.json` reports how many questions the arms
disagree on, at both budgets and on both endpoints. **It does not report which
way**, and `_forbid_direction` raises at runtime if a gains, losses, net,
per-arm-hits, direction or winner key reaches the artifact. That is what makes
this readable before the bars are locked.

| Budget | Endpoint | Discordant | Concordant | Best one-sided exact p at that `d` |
|---|---|---:|---:|---:|
| 16,000 | complete evidence | **451** | 420 | 1.7 × 10⁻¹³⁶ |
| 16,000 | any evidence | 438 | 433 | 1.4 × 10⁻¹³² |
| 32,000 | complete evidence | 191 | 680 | 3.2 × 10⁻⁵⁸ |
| 32,000 | any evidence | 173 | 698 | 8.4 × 10⁻⁵³ |

**The arms disagree on 451 of 871 questions at the primary budget** — 52% —
spread across all four conversations (85 / 147 / 83 / 136). Every branch of §6.3
is therefore reachable: D1 and D3 can fire, since the smallest reachable p is
132 orders of magnitude below the 0.01 bar; D2 and D4 can fire, since a
near-even split of 451 discordant pairs lands p between 0.01 and 0.10; and D0a
can fire, since a split within 4 of even is possible at any `d`. **No branch is
unreachable by construction, and no branch is guaranteed.**

The discordant count also fixes the band's meaning: B = 4 against d = 451 is a
band of 0.9% of the discordant population, not a threshold that swallows the
contrast.

One bookkeeping note, recorded rather than smoothed. The probe evaluates 871
questions — every unique question with at least one resolved evidence id. The
registered primary population is **868**, which additionally excludes the three
questions carrying an evidence id that resolves to no dialogue turn (two in
`conv-42`, one in `conv-47`). The probe's population is a superset by three;
three questions cannot change a reachability verdict at d = 451, and the study's
own measurement uses 868.

### 7.2 Surrogate audit — can this pass while the property it certifies is false?

**Yes, in two named ways, and both are accepted residuals rather than repaired.**

1. **Evidence present is not evidence used.** LV-001 measured 16 of 16 offline
   availability against 1.5 of 8 live. This endpoint certifies that the text
   carrying an answer reached the window; it certifies nothing about whether a
   reader used it. This is the arc's central open gap and it is TC-006's whole
   subject. It is stated here, before the run, so no result of this study can be
   read as closing it.
2. **A hit says nothing about what surrounds it.** A question counts as a hit
   when its evidence pairs are in the block, even if the block is otherwise full
   of unrelated material. Delivered composition and delivered episode counts are
   reported alongside the primary for exactly this reason.

**And the mirror question — can the bar fail while the property is true?** Yes,
if the two arms rarely disagree. That is what `PF4`'s discordant count exists to
rule out, and it is why the band is measured rather than assumed.

## 8. Registered robustness check — no bar

The primary is repeated once with `A_FLAT`'s budget reduced by 18 characters, so
both arms pay the same block-wrapper cost (§3.1). The verdict under the matched
wrapper is reported next to the primary. If the two disagree, the disagreement
is the finding and the primary verdict is reported as not robust to a 0.11%
budget difference.

## 9. What a result here does not establish

- **Nothing about answers.** Availability is not a verdict. The live evaluation
  this endpoint requires is TC-006's fact-use instrument over frozen contexts,
  and TC-006's own first task is measuring whether that instrument's resolution
  is finer than the margin it must test. Until that exists, no delivery result
  in this arc — including this one — supports a claim that fixing delivery
  improves answers.
- **Nothing about deletion.** If `A_FLAT` wins, that is a delivery result on one
  corpus at one budget. It does not authorize removing the tiers, because the
  tiers were not built only for delivery and because TC-003 has not yet asked
  whether allocation rather than the tiers themselves is the cause.
- **Nothing about which tier is responsible.** Composition is reported and is
  descriptive. TC-003 owns the decomposition.
- **Nothing that transfers off this corpus.** LoCoMo development is four
  conversations of one dialogue style. TC-002's whole subject is whether an
  availability result holds off its original corpus.
- **No confirmation of anything.** The corpus is spent; the standing is capped.

## 10. Dependency and the Rule 4 re-read

**Dependency line, from the roadmap §2, re-read from the file rather than from
memory on August 22, 2026:** *"Requires a store with per-item evidence labels and
both paths runnable over identical candidate identities."*

**Satisfied.** LoCoMo development supplies per-question resolved evidence dialogue
ids, and `PF1` records both paths running over the identical 1,365 pair
identities. Expiry: none — the dependency was already satisfied when written.

**This study blocks nothing.** Under roadmap Rule 1 there is no arc-level
dependency clause, and TC-002 through TC-006 are runnable whatever this reports.
When TC-001 reports a verdict, Rule 4 requires every other study's dependency
line to be re-read against the new evidence and the re-read logged in
`TC_ARC_DEPENDENCY_LOG.md` with an explicit per-study verdict, **before the next
study is registered.**

This registration closes roadmap §10 decisions 1 (corpus, for this study) and 3
(the null band, for this study). Decisions 2 and 4 are untouched by it.
