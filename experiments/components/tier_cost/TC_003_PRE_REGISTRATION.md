# TC-003 — Reserved floors against sequential fill

**Status:** `PRE-REGISTERED, NOT RUN`
**Date:** August 22, 2026
**Branch:** `study/tc-arc-tier-cost`
**Arc:** `TC_ARC_ROADMAP.md` §4. That file is design-only; **this document
governs TC-003**, and where the two disagree the disagreement is a defect in
the roadmap.
**Standing sought:** `REGISTERED-OFFLINE` — bars locked before any arm's hit
count exists, zero generative calls, replayable against a retained embedding
cache, on a corpus this programme has already observed. Capped as
characterization; **not** confirmation.
**Integrity anchor:** the commit containing this file, before implementation.

---

## 0. What this is, and what it is not

Roadmap §4 states the proposal in one sentence:

> Greedy sequential fill lets whichever tier goes first take everything … give
> each tier a guaranteed minimum share of the budget and let them compete only
> for the remainder, so allocation stops depending on order.

**What it is.** That proposal, implemented as written and tested as written, on
the corpus the three prior arc studies used, against every fixed order the arc
has measured.

**What this study is testing, named precisely.** The arc now has two separate
levers on delivery and they are not the same size. TC-002 measured both on this
corpus:

| Lever | What it changes | Worth |
|---|---|---:|
| **Between tiers** | which tier is served first | **45 questions** |
| **Within the K tier** | the order the K tier offers its own members | **111 questions** |

`TC_ARC_DEPENDENCY_LOG.md`'s third re-read says TC-003 "should say which it is
testing." **TC-003 tests the between-tier lever.** Reserved floors are an
allocation rule between tiers, and each tier keeps its own offer order
untouched. §3.3 records the one place that statement is not exact and §6.4
registers the contrast that separates the two.

**What it is not.**

- **Not a shipping decision, whichever way it lands.** TC-002's §0 decided this
  for the arc: an availability result does not ship on its own. `PAPER_002.md`
  §9.3's live rejection is the binding evidence on adoption, and TC-006 owns
  adoption. That decision is inherited here, not re-opened.
- **Not a tuning study.** One floor rule, **zero free parameters**: equal shares
  among the tiers a configuration populates. Sweeping floor vectors adds a
  policy level, which under `AGENTS.md` §5 is a new study requiring escalation.
  It is not done here and no result here licenses it without one (§9.3).
- **Not confirmatory, and it cannot be.** Roadmap §0.1: LongMemEval is
  exhausted and LoCoMo is spent three times over.

### 0.1 Disclosure: what Preflight Part 1 saw before this document was written

Part 1 ran both order-invariance checks before this registration was drafted,
and I read their results. That is disclosed rather than glossed, because
`AGENTS.md` §7 forbids changing criteria after observing results and a reader is
entitled to check that nothing was.

**Neither check has a tunable parameter.** The bar is exact identity of the
delivered set across all six permutations. There is no threshold to move, no
population to choose, and no direction to pick, so nothing that *could* have
been chosen after seeing them was chosen after seeing them.

**What could have been shaped is the interpretation**, so §6.5 fixes the
interpretation of each check in both directions and §9.4 states the limit a
failure implies. Both sections are written to read the same way whichever
result they are applied to.

The six statistical contrasts are untouched by this. Part 1 records no arm's
availability by construction, and §7.1's PF4 artifact refuses to carry a
directional key.

## 1. The questions

**Q1 — the headline.** Does equal-share reserved-floor allocation deliver
evidence more often than the shipped N-first sequential fill?

**Q2 — against the other fixed order.** Roadmap §4's bar is "availability
against both fixed orders." Does it beat EC-002's K-first order?

**Q3 — the ceiling.** TC-001 found a flat cosine ranking ahead of the shipped
stack by 435 questions. Does allocation explain that gap?

**Q4, Q5, Q6 — the same three under the arc's standing dual configuration**,
where the recency tier is empty and the floor rule reduces to halves. The dual
arm travels with this arc by the author's standing instruction (roadmap §1.1),
and carrying it here separates "floors help" from "the recency floor costs more
than floors gain" — two readings a single configuration cannot tell apart.

**Q7 — the property that motivates the design.** Roadmap §4:

> A floors-based allocator should produce the same delivered set under permuted
> tier order. That is a deterministic property and is checked directly, not
> inferred.

It is checked directly, over all six permutations, **twice**: once for the order
tiers are *served* in, and once for the order that decides which tier *owns* a
candidate belonging to more than one. The second is not in the roadmap's
sentence and is in the design regardless, which is why it is registered.

## 2. Corpus, unit, budget, endpoint — inherited and frozen

Every input below is TC-001's, at the digests TC-001, TC-001B and TC-002 all ran
against. Nothing is re-derived.

| | Value |
|---|---|
| Corpus | LoCoMo development — `conv-41`, `conv-42`, `conv-47`, `conv-48` |
| Dataset | `locomo10.json`, SHA-256 `79fa87e9…`, asserted from `development_vector_manifest.json` |
| Unit | one adjacent user/assistant pair, rendered by the post-DR-001 compact renderer |
| Candidates | 1,365 pairs; per-conversation pools of 323–355 |
| Questions | **871** with at least one resolved evidence id; **868** of those with no unresolved evidence id |
| Vectors | `locomo_dev_embeddings.db`, read-only, file `2ba61701…` and content `e103b293…` asserted |
| Embedder | Qwen3-Embedding-0.6B Q8_0, solo call shape, SHA-256 `06507c7b…` pinned by `EpisodicConfig` |
| Packing | exact serialized cost, `DROP_POLICY` unchanged in both phases |
| Selector | E005 `A3_l0.1_r0.0_k16`, full-store pool |
| Seed | 5005 |

**Budget.** Primary **16,000 characters**; secondary **32,000**.

This returns to the arc's default. TC-001 and TC-001B both led at 16,000;
TC-002 led at 32,000 because it inherited EC-002's registered budget, and a
transfer test that also changes the budget tests two things. TC-003 inherits no
budget, so it uses the arc's and reports the other in full.

**Endpoint.** Primary **complete-evidence delivery**; secondary **any-evidence
delivery**. Again the arc's default, TC-001's and TC-001B's.

Evidence availability is candidate identity against LoCoMo's `evidence` dialogue
ids. Zero inference, no judge, no reader.

**The primary population is 868 questions**, the complete-evidence population.
The any-evidence secondary runs over 871.

## 3. Arms

Seven, all over identical candidate identities, identical vectors, the identical
renderer, and exact serialized cost with the same drop policy.

| Arm | What it is | First measured |
|---|---|---|
| `A_FLAT` | rank every candidate by cosine, pack to budget | TC-001 |
| `A_N_FIRST` | `build_context` — recency, then K, then coverage | TC-001 (as `A_TIERED`) |
| `A_K_FIRST` | EC-002's `pack_k_first` — K, then recency, then coverage | TC-002 |
| `A_DUAL` | `build_context` with `recency_window_n=0` | TC-001B |
| `A_DUAL_RANKED` | `A_DUAL` with the K tier offered best-first | TC-001B |
| **`A_FLOORS`** | equal-share reserved floors, shipped configuration | **here** |
| **`A_FLOORS_DUAL`** | the same rule, dual configuration | **here** |

`A_FLAT`, `A_DUAL` and `A_DUAL_RANKED` are the arc's standing arms (roadmap
§1.1) and are inherited, not redefined; `tests/test_dual_arm_standing.py` holds
them to that.

### 3.1 The floor rule, and why it has no free parameter

**Equal shares among the tiers the configuration populates.** Under the shipped
configuration three populated tiers reserve a third of the content budget each.
Under the dual configuration the recency tier is empty, so the other two reserve
a half each. It is **one rule at two configurations, not two tunings** — and the
rule takes no argument, which `test_the_floor_rule_has_no_free_parameter` holds
by inspecting its signature.

"Populated" is read off tier membership *before* ownership is resolved. That
keeps the floor vector unchanged under §6.5's ownership permutation, so that
check measures what ownership does rather than what ownership did to the floors.

### 3.2 The allocator is the committed packers generalized, not a rewrite

With every floor at zero and the remainder contested in tier order, the
allocator reduces **byte-for-byte** to:

| Service order | Reduces to |
|---|---|
| `(n, k, c)` | `episodic._packing.pack_stm_payload`, and so to `build_context` |
| `(k, n, c)` | `ec002_k_first_packing.pack_k_first` |

`assert_zero_floor_reduction` compares payload *strings*, not behaviour. Part 1
ran it on **871 questions × 2 budgets × 2 configurations = 3,484 checks, each
comparing three payloads, and all passed.** If it fails, the floors arm is a
rewrite of the packers and every contrast against them measures the rewrite as
well as the floors. §8.1 re-runs it inside G0.

### 3.3 The two phases, stated exactly

**Phase 1 — reserved.** Tier `t` receives an allowance of `share_t` of the
content budget and packs its own owned candidates into that allowance alone, in
its own offer order, charging exact serialized cost and skipping on overflow.

A tier's spend is charged **solo** — as if it were alone in the payload. The K
and coverage tiers share one rendered block, so solo accounting over-charges by
that block's opening tags when both are non-empty and never under-charges. Two
consequences, both load-bearing: the reserved phase can never exceed the budget,
and a tier's spend depends on *its own* admissions only, which is what makes
phase 1 invariant under service order by construction rather than by
observation.

**Phase 2 — contested.** Every candidate phase 1 did not admit, from any tier,
competes for the room actually remaining, ranked by its own cosine with the
library's own `(-relevance, turn_number, id)` tie-break.

**The contest key names no tier, and that is forced rather than chosen.** An
allocator whose remainder is contested in tier order is order-dependent again
the moment the remainder is non-empty, which is nearly always. A round-robin
contest is not a way out: its outcome depends on which tier holds each round's
first slot.

**What that costs, stated here and not buried.** Ranking the remainder by cosine
is a second change on top of the allocation, and it is the *within-tier* lever
§0 said this study is not testing. So C1, C2 and C4 measure the reservation
**and** the contest key together, and they bound the pair from above rather than
isolating either. **C5 is registered to separate them** (§6.4, §6.7): it
compares the floors arm against `A_DUAL_RANKED`, which already offers its K tier
best-first, so the contest key is common to both sides and the reservation is
what differs. Part 1 measures the size of the exposure directly — at 16,000 the
contest admits a median of 14 of 54 delivered episodes under the shipped
configuration and 22 of 55 under the dual one.

### 3.4 The wrapper asymmetry, and which contrasts it touches

An arm that delivers a recency episode renders a non-empty `recent_context`
block and pays **18 characters** more fixed wrapper than one that does not.

| Contrast | Both sides render recency? | Robustness pass |
|---|---|---|
| C1 `A_FLOORS` vs `A_N_FIRST` | yes | not needed |
| C2 `A_FLOORS` vs `A_K_FIRST` | yes | not needed |
| **C3** `A_FLOORS` vs `A_FLAT` | no | **§8.3** |
| C4 `A_FLOORS_DUAL` vs `A_DUAL` | neither | not needed |
| C5 `A_FLOORS_DUAL` vs `A_DUAL_RANKED` | neither | not needed |
| C6 `A_FLOORS_DUAL` vs `A_FLAT` | neither | not needed |

Only C3 is asymmetric. Applying the adjustment to a symmetric contrast would
introduce the asymmetry it does not have, so §8.3 covers C3 and nothing else.

### 3.5 No arm may be added after the run

The seven above are the arms. An eighth — in particular reserved floors combined
with the K tier offered best-first — is a different question, is named in §9.4
as such, and would require its own registration.

## 4. Endpoints and pre-specified cuts

**Primary endpoint.** Complete-evidence delivery at 16,000 characters.

**Secondary endpoints, all reported in full with dispositions:** any-evidence at
16,000; both endpoints at 32,000.

**Pre-specified cuts, fixed here so they cannot be chosen afterwards:**

1. Delivered composition by tier, per arm — IC-001's failure was visible in
   composition and invisible in the aggregate.
2. Which tier carried the evidence, on every question where any arm delivered
   it, and **which phase admitted it** — reserved or contested.
3. Discordant pairs by conversation and by LoCoMo question category.
4. Whether each tier's floor **bound** (the tier had owned candidates that did
   not fit its allowance) or was **slack** (the tier ran out of candidates
   first, and the reservation returned to the contest).
5. The questions on which every offered candidate fits, where allocation cannot
   matter and no arm can differ from any other.

## 5. Preflight Part 1 — what the arms actually do

Artifact: `artifacts/tc003/preflight/tc003_preflight_part1.json`, 3,152 seconds,
**0 cache misses** — the corpus costs no model call.

### 5.1 Behavioral identity, in one falsifiable sentence each

**`A_FLOORS`** reserves a third of the content budget for each populated tier,
fills each reservation from that tier's own offer order, then ranks everything
left over by cosine and fills the remainder.
*Falsifiable by:* setting every floor to zero and contesting in tier order,
which must reproduce the shipped packer byte-for-byte. 3,484 checks, all passed
(§3.2).

**`A_FLOORS_DUAL`** is the same rule where the recency tier is empty, so the K
and coverage tiers reserve a half each.
*Falsifiable by:* the same reduction under `recency_window_n=0`, and by the
share vector being `0, ½, ½` rather than a second set of tuned numbers.

### 5.2 Name-to-behavior — is a "floor" a floor, and is the remainder contested?

A floor that never binds is decoration. Measured, per budget, over 871
questions:

| Budget | Config | Recency floor binds | K floor binds | Coverage floor binds |
|---:|---|---:|---:|---:|
| 16,000 | shipped | **871 / 871** | 773 | 172 |
| 16,000 | dual | — (tier empty) | 733 | 138 |
| 32,000 | shipped | **0 / 871** | 665 | 363 |
| 32,000 | dual | — (tier empty) | 583 | 287 |

**At 32,000 the recency floor never binds, and that is registered as a
name-to-behavior failure rather than discovered as one later.** Thirty-two
recency episodes fit inside a third of 32,000 with room left over, so at that
budget the recency *reservation* does nothing and the arm's behaviour is driven
by the K and coverage floors alone. "Reserved floors" does not describe what the
recency tier gets at 32,000. It describes exactly what it gets at 16,000, which
is the primary.

**Is the remainder contested?** The reserved phase leaves a median of 4,624
characters at 16,000 (29% of the budget) and 8,719 at 32,000 (27%), and the
contest admits a median of 14 episodes at 16,000 under the shipped
configuration. It admitted nothing on 9 of 871 questions at 16,000 and on 0 at
32,000. The remainder is real and it is contested.

### 5.3 Distributions, not summaries

Median composition, 871 questions. `PAPER_002.md` §9.1 records the shipped
N-first arm's median composition as **16 recency, 0 non-recency similarity, 1
coverage**; the floors arm is a different shape, not a tuned version of the same
one.

| Budget | Config | Delivered | Recency | K | Coverage | Reserved / contested |
|---:|---|---:|---:|---:|---:|---|
| 16,000 | shipped | 54 | 18 | 31 | 3 | 38 / 14 |
| 16,000 | dual | 55 | 0 | 49 | 3 | 30 / 22 |
| 32,000 | shipped | 110 | 32 | 53 | 20 | 88 / 16 |
| 32,000 | dual | 111 | 0 | 83 | 23 | 75 / 29 |

Delivered characters run 15,804–16,000 and 31,717–32,000: the budget is spent,
not left on the table.

### 5.4 Degenerate and absorbing states

**Everything fits.** Where every offered candidate fits, allocation cannot
matter and no arm can differ from any other.

| Budget | Config | Questions where everything fits |
|---:|---|---:|
| 16,000 | shipped | **0** |
| 16,000 | dual | 238 |
| 32,000 | shipped | **0** |
| 32,000 | dual | **520** |

This caps what a contrast can find, and the cap is stated before the run: at
32,000 the dual-configuration contrasts have at most **351** questions on which
their arms can differ at all. At the primary budget and configuration the cap
does not bite.

**The contest admits nothing** on 9 of 871 questions at 16,000 under the shipped
configuration, 0 elsewhere.

**Below the empty tags** the allocator returns the empty payload, which is
`pack_stm_payload`'s own degraded behaviour after CC-003. Exercised in
`tests/test_tc003_floors.py`.

**No feedback anywhere.** `allocate` is a pure function of the candidate state,
the budget, the shares and the three orders. There is no path by which an
admission changes a candidate's eligibility other than by consuming budget.

### 5.5 Cost

At this corpus's pool sizes, per question at 16,000:

| | median | p95 | max |
|---|---:|---:|---:|
| `build_candidate_state` (clustering and selection) | 90.9 ms | 104.5 ms | 110.6 ms |
| `allocate` (the whole two-phase allocation) | **3.1 ms** | 13.5 ms | 17.4 ms |

**Allocation is roughly 3% of the selection path.** Floors are not a latency
argument in either direction, and this study does not make one.

## 6. Bars — locked here, before any arm's hit count exists

### 6.1 The null band, measured

TC-001's method, kept: compare each arm **against itself** at a budget nudged by
±0.5% and ±1%, and record only the paired gains and losses. A budget moved by
half a percent carries no mechanism claim, so whatever paired movement it
produces is what this endpoint does at a packing boundary rather than what an
architecture does. No arm's absolute hit count is recorded.

TC-001B's correction is kept — both endpoints are measured. TC-002's correction
is kept — the band is measured at **both** budgets, because TC-002 found it
moves from 4 to 7 when the budget changes and a band measured at the wrong
budget is not this study's band.

Only the two new arms are re-measured; the five inherited arms have committed
bands. Worst |net| over the four perturbations:

| Budget | Arm | any | complete |
|---:|---|---:|---:|
| 16,000 | `A_FLOORS` | 2 | 2 |
| 16,000 | `A_FLOORS_DUAL` | 1 | 3 |
| 16,000 | *inherited maximum (TC-001)* | *4* | *4* |
| 32,000 | `A_FLOORS` | 9 | **10** |
| 32,000 | `A_FLOORS_DUAL` | 1 | 1 |
| 32,000 | *inherited maximum (TC-002)* | *7* | *7* |

**B = 4 questions at 16,000. B = 10 questions at 32,000.**

Each is the maximum over every value measured at that budget, inherited values
included. **The primary contrast is judged against B = 4.**

**A band may not shrink.** Not because a quieter arm joined the comparison, and
not because a budget at which arms are quieter was added. This clause is why B
at 16,000 is 4 rather than the 3 the new arms measured, and it was written
before the 32,000 numbers were read.

**`A_FLOORS` at 32,000 is the noisiest arm this arc has measured** — 10
questions move under a 1% budget nudge, against 7 for the shipped configuration
and 0 to 1 for `A_DUAL_RANKED`. One candidate explanation is that three
allowances mean three packing boundaries and a budget nudge moves all of them,
where a single sequential fill has one. **That explanation is not tested here
and is not offered as a finding**; what is registered is the number and the
wider bar it buys.

The sham perturbations run over the **871** questions with at least one resolved
evidence id — a three-question superset of the complete-evidence primary's 868.

### 6.2 The statistic

Per question, paired. For a contrast `X vs Y`: `gains` = X delivers the
endpoint's evidence and Y does not; `losses` = the reverse; `ties` = both or
neither; `net = gains − losses`.

One-sided exact binomial (sign test) on the `d = gains + losses` discordant
pairs at `p = 0.5`:

- `p₊ = Σ_{i=gains}^{d} C(d,i) / 2^d` for the X direction
- `p₋ = Σ_{i=losses}^{d} C(d,i) / 2^d` for the Y direction

**Multiplicity.** **Six** registered contrasts, so Bonferroni across the family
at the arc's base levels of 0.01 and 0.10:

| | Per contrast |
|---|---|
| α, "wins" tier | **0.01 / 6** |
| α, "carries signal" tier | **0.10 / 6** |

Written as divisions rather than decimals so the family size and the level
cannot drift apart in transcription. **The divisor stays at 6.** A family
divisor may not shrink after a Preflight number has been read, and it may not
grow to accommodate an arm added later, because §3.5 forbids adding one.

### 6.3 Dispositions — both tiers registered before the run, per AGENTS.md §9.3

The same six-branch table applies to each contrast `X vs Y`, exhaustive over the
real line:

| ID | Condition | Verdict |
|---|---|---|
| **D1** | `net ≥ B` and `p₊ ≤ 0.01/6` | **X_WINS** |
| **D2** | `net ≥ B` and `0.01/6 < p₊ ≤ 0.10/6` | **X_CARRIES_SIGNAL** — justifies a successor, not an adoption |
| **D3** | `net ≤ −B` and `p₋ ≤ 0.01/6` | **Y_WINS** |
| **D4** | `net ≤ −B` and `0.01/6 < p₋ ≤ 0.10/6` | **Y_CARRIES_SIGNAL** |
| **D0a** | `\|net\| < B` | **NO_DIFFERENCE_ESTABLISHED — inside the band.** Explicitly *not* a win for whichever arm is simpler |
| **D0b** | `\|net\| ≥ B` and both `p₊ > 0.10/6` and `p₋ > 0.10/6` | **NO_DIFFERENCE_ESTABLISHED — outside the band, not separable** |

### 6.4 The six contrasts, instantiated

| Contrast | X | Y | X wins is called | Y wins is called | What it carries |
|---|---|---|---|---|---|
| **C1** | `A_FLOORS` | `A_N_FIRST` | `FLOORS_WINS` | `N_FIRST_WINS` | the roadmap's first bar |
| **C2** | `A_FLOORS` | `A_K_FIRST` | `FLOORS_WINS` | `K_FIRST_WINS` | the roadmap's second bar |
| **C3** | `A_FLOORS` | `A_FLAT` | `FLOORS_WINS` | `FLAT_WINS` | the arc's reference |
| **C4** | `A_FLOORS_DUAL` | `A_DUAL` | `FLOORS_DUAL_WINS` | `DUAL_WINS` | floors with no recency floor to pay for |
| **C5** | `A_FLOORS_DUAL` | `A_DUAL_RANKED` | `FLOORS_DUAL_WINS` | `RANKED_WINS` | **the reservation, separated from the contest key** |
| **C6** | `A_FLOORS_DUAL` | `A_FLAT` | `FLOORS_DUAL_WINS` | `FLAT_WINS` | the arc's reference, dual configuration |

**C1 is the headline** because it is the roadmap's own question. **C5 is the
isolating contrast**, for the reason §3.3 gives, and §6.7 states in advance what
it means when the two disagree.

**All six carry bars at the primary budget.** One exception is registered at the
secondary: §7.1 found that C5 has only **9** discordant pairs at 32,000 against
a band of **10**, so no result it could produce there can clear its own band in
either direction. **C5 is `DESCRIPTIVE` at 32,000** — its statistic is reported
with no disposition — and carries its bar at 16,000, where it has 46. The
Bonferroni divisor stays at 6 regardless (§6.2).

### 6.5 The two deterministic bars

Neither is a statistical test and neither has a tunable threshold. Each is exact
identity of the delivered set across all six permutations, on every question at
both budgets under both configurations. §0.1 discloses that Part 1 measured both
before this document was written.

**I1 — service-order invariance.** The order tiers are served in.

- **Passes on every question** → the roadmap's stated property holds for this
  allocator. It is invariance *by construction*: §3.3's solo accounting makes a
  tier's reserved spend depend on its own admissions only, and the contest key
  names no tier. A property that holds by construction is worth measuring
  anyway, because a construction argument is a claim about code.
- **Fails on any question** → the construction argument is wrong and the
  implementation, not the proposal, is at fault. The study stops and reports
  that, and no availability contrast is read, because the arm would not be
  well-defined.

**I2 — ownership-order invariance.** Which tier owns, pays for, and renders a
candidate belonging to more than one.

- **Passes on every question** → allocation is independent of every order this
  design contains, which is the roadmap's sentence in full.
- **Fails on any question** → §9.4's narrower statement is the one the report
  must make, in those words: floors make allocation independent of *service*
  order and leave it dependent on *ownership* order.

**Both are read against a control, and the control is part of the bar.** An
invariance result over an instrument that cannot express non-invariance is not
evidence. Two controls, both measured in §7.1: for I1, the same allocator with
its floors removed, which must separate the six orders on at least one question;
for I2, the number of questions where a candidate belongs to two tiers, which
must be non-zero or the check is vacuous.

**A third quantity is registered as a reported comparison, not as a bar:** the
same ownership permutation applied to the zero-floor sequential allocator. It
answers whether floors *created* an ownership dependence or merely inherited
one, and it is reported whichever way it falls.

### 6.6 What is fixed before the run, in one place

| | |
|---|---|
| Primary budget | 16,000 characters |
| Primary endpoint | complete-evidence delivery |
| Primary population | 868 questions |
| Headline contrast | **C1** |
| Isolating contrast | **C5** |
| Contrast family | 6 |
| α | 0.01 / 6 and 0.10 / 6 |
| Null band | **4** at 16,000, **10** at 32,000 |
| Contrasts without a bar | **C5 at 32,000 only** — unreachable, §7.1 |
| Deterministic bars | I1 and I2, exact set identity, six permutations |
| Wrapper-matched robustness | C3 only |
| Arms | seven, and no eighth |

### 6.7 What the study concludes, written before it can be read

**C1 is the headline, whatever it says.**

- **C1 = `FLOORS_WINS`** → reserved floors deliver evidence more often than the
  shipped sequential fill on this corpus. It authorizes nothing: §0 and §9.1
  forbid reading it as a shipping decision.
- **C1 = `N_FIRST_WINS`** → the roadmap's proposal is worse than the order it
  was designed to replace, which is a result and closes the question.
- **C1 = `NO_DIFFERENCE_ESTABLISHED`** → floors are not demonstrated to change
  availability against the shipped order at this power.

**C1 and C5 read together, fixed here because the pair is what makes the result
interpretable:**

| C1 | C5 | The reading |
|---|---|---|
| `FLOORS_WINS` | `FLOORS_DUAL_WINS` | the reservation itself carries the gain |
| `FLOORS_WINS` | `D0a` / `D0b` / `RANKED_WINS` | **the gain is the contest key, not the reservation.** §3.3's cosine contest is doing the work, and the report says so rather than crediting floors |
| `N_FIRST_WINS` or null | `FLOORS_DUAL_WINS` | the reservation helps only where the recency floor is not being paid for |
| null | null | floors are not demonstrated on this corpus at this power |

C2, C3, C4 and C6 are reported with their dispositions in every case. **No
combination of them replaces C1 as the headline.**

## 7. Preflight Part 2 — checklist

| # | Check | Answer |
|---|---|---|
| **PF1** | Inputs exist | `locomo10.json` and `locomo_dev_embeddings.db`, both digest-asserted in §2, both already used by TC-001, TC-001B and TC-002 at the same digests. Part 1 recorded **0 misses** in read-only mode. Every source file's SHA-256 is recorded in the run header |
| **PF2** | Mechanism identity | §3.2's 3,484 byte-for-byte reductions, §5.1's falsifiable sentences, §5.2's name-to-behavior check — which found and registered one failure, at 32,000 |
| **PF3** | Gate ordering enforced | **G0** is a separate committed phase (§8.1). The run phase refuses to compute any arm's availability until `g0_reproduction.json` exists, is git-tracked, and reports `PASS` |
| **PF4** | Thresholds achievable | §7.1 — and for both kinds of bar, statistical and deterministic |
| **PF5** | Comparison keys stable | Inherited from TC-001 unchanged: candidates key on `PairCandidate.identity`, questions on the canonical QA record's SHA-256 plus a duplicate ordinal, delivered episodes on the renderer's `turn` attribute. No uuid, path, timestamp or run-generated identifier enters any comparison |
| **PF6** | Reproduction anchor | §8.1 — twenty committed cells across five inherited arms, and §8.2 states what that does not cover |
| **PF7** | Absorbing-state proof | §5.4. No feedback in any path; the degenerate states are counted on every question rather than argued |
| **PF8** | Ablation length adequate | Not applicable: full-population offline replay over all 871 questions, not a sampled ablation. What it cannot detect is behavior that emerges past 1,365 candidates — TC-005's question |
| **PF9** | Surrogate audit | §7.2 |
| **PF10** | Live-evaluation requirement | §9.1, §9.2 |

### 7.1 PF4 — reachable, and failable, with the direction withheld

A sign test is decided by its discordant pairs; a contrast whose arms never
disagree cannot fire a bar in either direction, which is the defect DMR-001
locked and TC-001B's C3 was registered around. My own note from that failure is
why this section is written per bar rather than per statistic:

> reachability per bar, not per statistic; DMR-001 locked one that was
> unreachable by construction.

The probe is `src/analysis/tc003_reachability.py`; its artifact is
`tc003_preflight_pf4_reachability.json`, and the module refuses to write a
directional key, so the split that decides each contrast is not readable from
it.

**Discordant pairs, primary endpoint (complete evidence):**

| Contrast | 16,000 (`B = 4`) | 32,000 (`B = 10`) |
|---|---:|---:|
| **C1** `A_FLOORS` vs `A_N_FIRST` | 372 | 187 |
| **C2** `A_FLOORS` vs `A_K_FIRST` | 321 | 155 |
| **C3** `A_FLOORS` vs `A_FLAT` | 103 | 68 |
| **C4** `A_FLOORS_DUAL` vs `A_DUAL` | 286 | 122 |
| **C5** `A_FLOORS_DUAL` vs `A_DUAL_RANKED` | 46 | **9** |
| **C6** `A_FLOORS_DUAL` vs `A_FLAT` | 49 | 12 |

On the any-evidence secondary: 385, 313, 77, 283, 32 and 34 at 16,000; 168, 135,
49, 112, **9** and 10 at 32,000.

**At the primary budget every branch of §6.3's table is reachable for all six
contrasts.** The thinnest is C5 at 46 discordant pairs against `B = 4`, which
leaves room for `D0a`, `D0b`, and both signal and win tiers in both directions.

**C5 is unreachable at 32,000 and is therefore registered with no bar there.**
`|net|` cannot exceed the discordant count, so at 9 discordant pairs the largest
attainable `|net|` is **9**, and `B` at 32,000 is **10**. No result C5 could
produce at that budget can clear its own band in either direction — on either
endpoint, both of which have 9 discordant pairs. This is not a power caveat to
be noted afterwards; it is a bar that cannot fire, and registering it as a bar
would repeat DMR-001 exactly.

**C5 therefore carries a bar at 16,000, the primary, and is `DESCRIPTIVE` at
32,000.** Its 32,000 statistic is reported with its discordant count and no
disposition. The Bonferroni divisor stays at **6**: a family divisor may not
shrink after a Preflight number has been read (§6.2), and it does not shrink
because one contrast turned out undecidable at a secondary budget.

**C6 at 32,000 is reachable and partly so, and the arithmetic is recorded rather
than assumed.** At 12 discordant pairs on the complete endpoint, parity allows
`|net| ∈ {0, 2, …, 12}`:

| `\|net\|` | one-sided *p* | Branch against `B = 10` |
|---:|---:|---|
| 12 | 2.44 × 10⁻⁴ | **D1 / D3** — reachable |
| 10 | 3.17 × 10⁻³ | **D2 / D4** — reachable |
| ≤ 8 | — | **D0a** — reachable |

On the any-evidence secondary C6 has 10 discordant pairs, so `|net| ≥ 10` is
attainable only at `|net| = 10`, where *p* = 9.77 × 10⁻⁴ is already inside the
win tier. **`D2`, `D4` and `D0b` cannot fire for C6 at 32,000 on the
any-evidence endpoint**; `D0a`, `D1` and `D3` can. That is registered here so a
`D0a` there is read as the only alternative to an extreme, not as evidence of
similarity.

### The two deterministic bars are reachable too

An invariance check over an instrument that cannot express non-invariance is not
evidence, so §6.5 registers a control for each and PF4 measures both.

| Control | 16,000 | 32,000 | Verdict |
|---|---:|---:|---|
| Questions where the **zero-floor control separates** the six service orders — `A_FLOORS` | 871 / 871 | 871 / 871 | I1's check can fail |
| …`A_FLOORS_DUAL` | 633 / 871 | 351 / 871 | I1's check can fail |
| Questions where **a candidate belongs to two tiers** — both arms | 871 / 871 | 871 / 871 | I2 is never vacuous |

Every question in this corpus has a candidate in more than one tier, so
ownership always has something to decide and an invariant I2 result could not be
vacuous anywhere. The service-order control separates on every question under
the shipped configuration; under the dual configuration it separates on the
questions where the budget binds, which §5.4's "everything fits" counts already
account for.

**No contrast is registered without a bar except C5 at 32,000**, and none may be
given one later.

### 7.2 Surrogate audit — can this pass while the property it certifies is false?

| Claim | Can it pass while false? | Residual, accepted |
|---|---|---|
| "Evidence was delivered" | Yes. Presence is not use — a reader can receive the text and answer wrongly | LV-001 measured 16/16 offline against 1.5/8 live. §9.2. Accepted and named, not repaired here |
| "The floors arm is the committed packers generalized" | Yes, if the reduction held only where the budget does not bind | Not a residual: §3.2 checks it on every question at both budgets under both configurations, and G0 re-checks it |
| "The band is the endpoint's wobble" | Yes, if a ±1% budget nudge is not representative of the noise a real comparison meets | Inherited from TC-001's method, now measured at two budgets by two studies. Accepted; a sham is a sham |
| "Floors are order-invariant" | **Yes — vacuously**, if the check runs on an instrument that cannot register a difference, or on questions where the tiers never overlap | Not a residual: §6.5 registers both controls and §7.1 measures them |
| "The contrast measures allocation" | **No, not entirely.** §3.3's contest key re-ranks the remainder by cosine, which is a second change | Named rather than accepted: C5 is registered to separate them and §6.7 fixes the reading when C1 and C5 disagree |
| "Equal shares is the floor rule" | Yes, if a tier that offers nothing still reserved budget | Not a residual: `test_an_unpopulated_k_tier_does_not_reserve_anything` |
| "A floor is a floor" | **Yes, and it does at 32,000** | Registered in §5.2 rather than left to be found: the recency floor never binds at 32,000, so the name does not describe the behaviour there |

## 8. Gates and registered robustness checks

### 8.1 G0 — the reproduction anchor, committed before the run phase opens

Five of this study's seven arms have committed hit counts, from TC-001 and
TC-002, on this corpus at both budgets and both endpoints. The instrument must
reproduce all twenty cells exactly before it is allowed to measure anything new.

The values are transcribed into the study module rather than read out of the
artifacts, so a corrupted artifact fails the gate instead of redefining it, and
both the freshly computed value and the committed record are compared against
the transcription.

| Budget | Endpoint | `A_FLAT` | `A_N_FIRST` | `A_K_FIRST` | `A_DUAL` | `A_DUAL_RANKED` |
|---:|---|---:|---:|---:|---:|---:|
| 16,000 | complete | 749 | 314 | 461 | 472 | 748 |
| 16,000 | any | 803 | 381 | 519 | 528 | 801 |
| 32,000 | complete | 810 | 633 | 685 | 694 | 811 |
| 32,000 | any | 842 | 687 | 732 | 740 | 843 |

`A_FLAT` and `A_N_FIRST` are TC-001's; `A_K_FIRST`, `A_DUAL` and
`A_DUAL_RANKED` are TC-002's.

G0 also re-runs, on every question at both budgets under both configurations:

1. **the zero-floor reduction** of §3.2, byte-for-byte against
   `pack_stm_payload`, against `build_context`, and against `pack_k_first`;
2. **the invariance controls** of §6.5 — the zero-floor control must separate
   the six service orders on at least one question, and at least one question
   must carry a candidate in two tiers.

A failed G0 stops the study.

### 8.2 What G0 does not establish, stated plainly

It establishes that this instrument reproduces five committed arms and that the
allocator degenerates to two committed packers. It does **not** establish that
equal shares is a good floor vector, that the corpus is representative, or that
ranking a remainder by cosine is the right way to allocate one. Those are §9's
subject and none of them is repaired by a gate.

### 8.3 Wrapper-matched robustness for C3 — no bar

`A_FLAT` renders an empty `recent_context` block; `A_FLOORS` does not, because
its recency floor guarantees recency episodes at the primary budget. §3.4 puts
the difference at 18 characters. The robustness pass re-runs C3 with `A_FLAT`
given 18 fewer characters, paying the difference back.

**It carries no bar and cannot change a disposition.** It is reported beside the
primary, and a disagreement between them is reported as a disagreement rather
than resolved in either direction. C1, C2, C4, C5 and C6 are excluded because
they are wrapper-symmetric already.

## 9. What a result here does not establish

### 9.1 Nothing that authorizes shipping

TC-002's §0 decided this for the arc and the decision is inherited, not
re-opened: an availability result does not ship on its own. `PAPER_002.md` §9.3
is the binding evidence on adoption — a correction with a large, confirmed
availability gain was tested live and rejected on its own registered bar — and
TC-006 owns adoption.

### 9.2 Nothing about answers

LV-001 measured 16 of 16 offline availability against 1.5 of 8 live. An
availability margin is an availability margin.

### 9.3 Nothing about the best floor vector

One rule, zero free parameters, chosen because it is the only vector expressing
"each tier gets a guaranteed share" without a further assumption. A better
vector may exist. Finding it means sweeping a policy level, which under
`AGENTS.md` §5 is a new study requiring escalation, and **no result here
licenses that sweep without one.** In particular, a null C1 is not evidence that
floors cannot work at some other vector, and a positive C1 is not evidence that
equal shares is where the maximum is.

### 9.4 The order this study does not remove

Reserved floors remove the dependence on which tier is **served** first. They do
not, and cannot, remove the dependence on which tier **owns** a candidate that
belongs to more than one, because ownership decides which allowance pays for it.

If I2 fails, the honest statement is: **floors make allocation independent of
service order and leave it dependent on ownership order.** That is narrower than
roadmap §4's "allocation stops depending on order," and the report must say so
in those words rather than reporting the service result alone.

It is not repairable by a different floor vector: any allocator giving tiers
separate allowances must decide which allowance a shared candidate draws on.

**The two levers this study does not combine.** Floors act between tiers.
TC-002 measured the within-tier lever at 111 questions against 45 for the
between-tier one on this corpus. An arm combining floors with a
relevance-ordered K tier is the obvious next configuration and it is **not**
registered here: adding it would make "only the allocation differs" false for
that arm, and §3.5 forbids adding an arm after the run.

### 9.5 Nothing about the recency window's real behaviour

`PAPER_002.md` §3.4 records that no live study ran a true last-*N* window; the
studies ran a rotation and, before that, a locked prefix. Roadmap §9 says the
same of this study in advance: it "measures allocation among tiers as they are,
not as they are documented." Reserving a share of the budget for the recency
tier on a finished transcript, where "the last 32 turns" is an arbitrary slice,
cannot measure what that tier was built to do.

### 9.6 Not confirmatory

Roadmap §0.1. This corpus has been observed by TC-001, TC-001B and TC-002, and
the arms were chosen with their results known. Bars locked before any number
here exists makes this registered; a registered study on an observed corpus is
characterization.

### 9.7 A `D0a` is a power statement, not an equivalence claim

Wherever a contrast lands `D0a`, the correct reading is that this study cannot
separate those two arms on that endpoint at this power. Equivalence needs an
equivalence test with a registered margin, and this study registers none. §5.4's
"everything fits" counts make this concrete at 32,000 under the dual
configuration, where 520 of 871 questions cannot distinguish any two arms.

## 10. Dependency, and the Rule 4 re-read

**Dependency line, as the roadmap states it:** requires the tier boundaries to
be identifiable in the delivered block.
**Satisfied.** `ContextReport` supplies it, and TC-001, TC-001B and TC-002 have
each attributed carried evidence to a tier on all 871 questions — TC-002 for
four configurations at two budgets. This study additionally records, per
question, which tier *owns* each delivered episode and which phase admitted it.
**Expiry:** none — the dependency is already satisfied.

**What this blocks:** nothing.

TC-003 reporting triggers `TC_ARC_ROADMAP.md` Rule 4: every other study's
dependency line is re-read from the roadmap file and logged in
`TC_ARC_DEPENDENCY_LOG.md` with an explicit per-study verdict, in the same
commit as the report and before the next study is registered.

## 11. Artifacts and order

1. Commit Preflight Part 1 and PF4, with their modules, tests and artifacts.
2. Commit **this registration alone**.
3. Commit the study implementation and its tests.
4. Run and commit **G0**.
5. Only after the G0 commit, run the study and commit its artifacts.
6. Commit the report with this file's commit SHA and SHA-256 in its header.
7. Rule 4 re-read, `README.md`, `AGENTS.md` digest, memory.
8. Open the study pull request.

```text
src/analysis/tc003_exploration.py          the allocator, and Preflight Part 1
src/analysis/tc003_reachability.py         PF4
src/analysis/tc003_study.py                the study
scripts/run_tc003_preflight.py
scripts/run_tc003_reachability.py
scripts/run_tc003_study.py
tests/test_tc003_floors.py                 the allocator's behavioural identity
tests/test_tc003_study.py                  the bars, the table, the anchors
experiments/components/tier_cost/artifacts/tc003/preflight/
experiments/components/tier_cost/runs/tc003/g0/
experiments/components/tier_cost/runs/tc003/run/
experiments/components/tier_cost/TC_003_REPORT.md
```

## 12. Authorization

The author directed on August 22, 2026, after TC-002 closed:

> *"This is a good results so far, now I'm interested in TC-003. You can push
> TC-002 up and implement TC-003."*

That authorizes TC-003 as the roadmap scopes it. The standing arms of §3 are
carried under the author's earlier instruction that the dual arm travel with
this arc, which roadmap §1.1 records and `tests/test_dual_arm_standing.py`
holds.
