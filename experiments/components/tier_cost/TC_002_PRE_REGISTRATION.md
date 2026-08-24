# TC-002 — Does the fill-order result hold off its original corpus?

**Status:** `PRE-REGISTERED, NOT RUN`
**Date:** August 22, 2026
**Branch:** `study/tc-arc-tier-cost`
**Arc:** `TC_ARC_ROADMAP.md` §3. That file is design-only; **this document
governs TC-002**, and where the two disagree the disagreement is a defect in
the roadmap.
**Standing sought:** `REGISTERED-OFFLINE` — bars locked before any arm's hit
count exists, zero generative calls, replayable against a retained embedding
cache, on a corpus this programme has already observed. Capped as
characterization; **not** confirmation.
**Integrity anchor:** the commit containing this file, before implementation.

---

## 0. What this is, and what it is not

EC-002 changed one thing in an offline replay of 500 LongMemEval stores — the
order in which unique episode identities are offered to the exact serializer —
and any-evidence-session recall rose from **109 to 261 of 470**, with **152
gains and zero losses**. The library still packs recency first.

`PAPER_002.md` §9.3 records what happened next. The same correction was tested
live and **rejected on its own registered bar**: the similarity-first arm scored
**7.0 against the deployed arm's 8.0**. That −1.0 margin sits inside the
programme's 3.0-point instrument band, so it is not demonstrated in either
direction, and this programme's registration forbids citing the band to revive
the rejected correction.

So the honest statement of the situation is: **a large, confirmed gain in
whether the evidence arrives, and no demonstrated gain in whether the reader
answers.** This study addresses only the first clause, and only its generality.

**What it is.** A transfer test. EC-002's manipulation, EC-002's endpoint,
EC-002's budget, EC-002's code — on a corpus EC-002 did not use.

**What it is not.**

- **Not a shipping decision, whichever way it lands.** Roadmap §10 lists
  "whether TC-002's result, if positive, ships immediately or waits for TC-003"
  as an open decision to be made before the run. **It is decided here: it does
  not ship on this result.** §9.3's live rejection is the binding evidence on
  adoption, this study does not address adoption, and TC-006 owns it.
  Registering that now is the point of deciding it now — so that a positive
  number cannot become an argument later.
- **Not confirmatory, and it cannot be.** Roadmap §0.1: LongMemEval is
  exhausted and LoCoMo is spent three times over. No sealed external corpus
  remains to this programme.
- **Not a retraction of EC-002 if it lands null.** Roadmap §3: "A null result
  here does not retract EC-002; it bounds it to its corpus, which is a result."
- **Not a re-run of EC-002.** §3.1 and §8.2 state exactly what is established
  about the manipulation's identity, and by what means.

## 1. The questions

**Q1 — the transfer question, and the study's headline.** On a corpus EC-002
did not use, does giving K-threshold candidates admission priority over the
recency window raise evidence availability?

**Q2 — the ceiling question.** TC-001 found a flat cosine ranking ahead of the
shipped tiered stack by 435 questions on complete evidence delivery. Does the
one-line reorder close that gap?

**Q3 — reorder against removal.** TC-001B found that removing the recency tier
outright is worth 158 questions. Is deprioritizing the tier the same repair as
deleting it, or a weaker one?

**Q4 — reorder against removal plus ranking.** TC-001B found that offering the
K tier best-first is worth a further 276. Does the reorder reach that?

Q3 and Q4 exist because the author's standing instruction after TC-001B is that
the dual arm travels with this arc. `src/analysis/tc_standing_arms.py` is where
that instruction lives, roadmap §1.1 is the convention, and
`tests/test_dual_arm_standing.py` is what holds it.

## 2. Corpus, unit, budget, endpoint — inherited and frozen

Every input below is TC-001's, at the digests TC-001 and TC-001B both ran
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
| Packer | `episodic._packing`, exact serialized cost, `DROP_POLICY` unchanged |
| Selector | E005 `A3_l0.1_r0.0_k16`, full-store pool |
| Seed | 5005 |

**Budget.** Primary **32,000 characters**; secondary **16,000**.

This is the one place TC-002 departs from TC-001 and TC-001B, which used 16,000
as primary. The reason is the question. EC-002's registered budget is 32,000 and
its result is a result at 32,000; a transfer test that also changes the budget
is testing two things. 16,000 is carried as a registered secondary because it is
the arc's other budget and because both prior studies report there.

**Endpoint.** Primary **any-evidence delivery**; secondary **complete-evidence
delivery**.

This is the second departure, for the same reason. EC-002's primary was
any-evidence-session recall; TC-001 and TC-001B used complete evidence. The
transfer claim is about EC-002's endpoint, so any-evidence leads and complete
evidence is reported in full alongside it at both budgets.

Evidence availability is candidate identity against LoCoMo's `evidence` dialogue
ids. Zero inference, no judge, no reader.

**The primary population is 871 questions**, the any-evidence population. The
complete-evidence secondary runs over 868.

## 3. Arms

Five, all over identical candidate identities, identical vectors, the identical
renderer and the identical packer.

| Arm | What it is |
|---|---|
| **`A_FLAT`** | `CdwArm`'s path: rank every candidate by cosine, pack to budget. TC-001's reference arm, carried as a standing arm |
| **`A_N_FIRST`** | `build_context` as shipped: recency, then K, then coverage. **This is TC-001's `A_TIERED` under the name the fill-order question gives it**, and it is the same code at the same config |
| **`A_K_FIRST`** | EC-002's registered counterfactual: K, then recency, then coverage, render tiers preserved. `analysis.ec002_k_first_packing.build_k_first_context`, imported unmodified |
| **`A_DUAL`** | `build_context` with `recency_window_n=0`. Standing arm from TC-001B |
| **`A_DUAL_RANKED`** | `A_DUAL` with the K tier offered best-first. Standing arm from TC-001B |

### 3.1 `A_K_FIRST` is EC-002's arm, and here is what establishes that

EC-002's runner, `scripts/run_ec002_k_first_packing.py`, calls
`repository_gate()`, which raises unless the current branch is
`ec/002-k-first-packing`. It cannot be invoked at this HEAD, and modifying it to
make it invokable would falsify the `script_sha256` its own committed
`source_integrity.json` records.

What is established instead is stronger for the identity question: **every file
on the K-first path is byte-identical to the revision that produced EC-002's
committed result.** The check is `git diff` against `caa19f52`, the commit
EC-002's A1 `run_header.json` records as HEAD, over:

```text
src/analysis/ec002_k_first_packing.py
src/analysis/ec001_longmemeval.py
episodic/src/episodic/_context.py
episodic/src/episodic/_packing.py
episodic/src/episodic/_render.py
episodic/src/episodic/_selection.py
```

An empty diff on all six is the pass. Part 1 records it under `provenance` and
G0 re-checks it. **A non-empty diff on any of them stops the study**, because
then the arm is not EC-002's arm and the transfer claim has nothing to
transfer.

One provenance defect is disclosed rather than repaired. EC-002's
`source_integrity.json` records `script_sha256_after` = `f23164ea…` for its
runner, and the file's committed content at `caa19f52` hashes to neither its LF
nor its CRLF form today. The `git diff` above is empty for that path, so the
*content* is unchanged; the recorded digest was taken on working-tree bytes
whose line endings this checkout does not reproduce — the two-conventions
problem `.gitattributes` documents. It is stated here because a reader checking
that digest will find it does not verify, and because nothing in TC-002 depends
on it: TC-002 does not invoke that runner.

### 3.2 One clustering pass, two fill orders

`A_N_FIRST` and `A_K_FIRST` differ only in admission order, so they must be
offered identical candidates in identical within-tier order. That is guaranteed
by construction rather than by care: `analysis.tc002_exploration.pack_both`
builds EC-002's own `CandidateState` **once** and hands it to both committed
packers — `episodic._packing.pack_stm_payload` for N-first and
`analysis.ec002_k_first_packing.pack_k_first` for K-first.

Part 1 holds that optimization to the two shipped entry points on every question
at both budgets under both configurations: `pack_both`'s N-first payload must
equal `build_context` byte for byte, and its K-first payload must equal
`build_k_first_context` byte for byte, with tier counts agreeing against each
`ContextReport`. **3,484 comparisons, all passing.** One failure is a stop.

### 3.3 The wrapper asymmetry, and which contrasts it touches

The renderer collapses an empty block to `<recent_context/>` (17 characters) and
spends 35 on a non-empty one, so an arm that delivers any recency episode pays
**18 characters** its counterpart does not.

| Contrast | Recency block, left arm | Recency block, right arm | Asymmetric? |
|---|---|---|---|
| **C1** `A_K_FIRST` vs `A_N_FIRST` | non-empty | non-empty | **no** |
| **C2** `A_K_FIRST` vs `A_FLAT` | non-empty | empty | yes |
| **C3** `A_DUAL` vs `A_K_FIRST` | empty | non-empty | yes |
| **C4** `A_DUAL_RANKED` vs `A_K_FIRST` | empty | non-empty | yes |

**The primary contrast is wrapper-symmetric by construction**, which TC-001
could not say of its own primary. §8.3 registers a matched robustness check for
the other three. C1 is excluded from that check, because lowering one of its
arms' budgets would introduce the asymmetry it does not have.

One qualification, measured rather than assumed: `A_K_FIRST`'s recency block is
non-empty on 379 of 871 questions at 16,000 and on 594 of 871 at 32,000. The
asymmetry in C2, C3 and C4 is therefore present on some questions and absent on
others, which is a further reason to check it rather than argue it.

### 3.4 No arm may be added after the run

Five arms, four contrasts, both fixed here. AGENTS.md §7 forbids adding an arm
after observing a result, and TC-001B's escalation amendment is the precedent
for what happens instead: a new arm is a new registration.

## 4. Endpoints and pre-specified cuts

**Primary.** Any-evidence delivery at 32,000 characters over 871 questions.

**Secondary, all registered here and none chosen afterwards.**

1. Complete-evidence delivery at 32,000 over 868 questions.
2. Both endpoints at 16,000.
3. Per conversation (four) and per category (five), on the primary endpoint.
4. Delivered episodes and delivered characters, as distributions, per arm.
5. Delivered composition by tier — recency, K, coverage — per arm.
6. Which tier carried the evidence when it arrived, per arm.
7. For every contrast's discordant pairs: the flat-cosine rank of the
   worst-ranked evidence episode. TC-001 and TC-001B both used this cut and it
   is what identified store-order delivery as the carrier of TC-001's deficit.
8. Per-question wall clock per arm.

## 5. Preflight Part 1 — what the arms actually do

Artifact: `artifacts/tc002/preflight/tc002_preflight_part1.json`, schema
`tc002-preflight-part1-v1`, committed at `d1357803`. Zero model calls; **2,247
cache hits and 0 misses** in read-only mode.

### 5.1 Behavioral identity, in one falsifiable sentence each

- **`A_N_FIRST`** offers the recency window's episodes to the packer before the
  K tier's, so under a binding budget the window's members take the block first.
- **`A_K_FIRST`** offers the same episodes in the order K, recency, coverage,
  and places each admitted episode in the render block its tier membership
  assigns rather than the one its admission order would suggest.
- **`A_DUAL`** has no recency tier to order.
- **`A_DUAL_RANKED`** has no recency tier and offers the K tier best-first.
- **`A_FLAT`** has no tiers.

### 5.2 Name-to-behavior — is "K-first" only a fill order?

The registered manipulation is admission order *between the recency tier and the
K tier*. Remove the recency tier and the manipulation has no subject, so the two
paths must produce identical bytes. Part 1 asserts exactly that:

> `build_k_first_context` at `recency_window_n=0` equals `build_context` at
> `recency_window_n=0`, byte for byte, on **1,742 of 1,742** — every question at
> both budgets.

Three further name checks, all measured:

| Claim | 16,000 | 32,000 |
|---|---|---|
| A K-admitted recency episode still renders inside `recent_context` | **871 / 871** | **871 / 871** |
| K-first never delivers fewer K episodes than N-first | **0 violations** | **0 violations** |
| K-first delivers *more* K episodes than N-first | 751 / 871 | 447 / 871 |
| K-first pays for that in recency episodes | 751 / 871 | 447 / 871 |
| The K tier is ever empty | 0 / 871 | 0 / 871 |

The fourth row is the mechanism in one line: on every question where K-first
gains a K episode it loses a recency one, and on no question does it gain a K
episode for free.

### 5.3 Distributions, not summaries

Delivered composition, median per question:

| Budget | Arm | recency | K | coverage | episodes | characters |
|---:|---|---:|---:|---:|---:|---:|
| 16,000 | `A_N_FIRST` | 32 | 22 | 0 | 54 | 15,961 |
| 16,000 | `A_K_FIRST` | **0** | **51** | 0 | 55 | 15,967 |
| 16,000 | `A_DUAL` | 0 | 52 | 0 | 56 | 15,965 |
| 16,000 | `A_DUAL_RANKED` | 0 | 50 | 0 | 54 | 15,966 |
| 16,000 | `A_FLAT` | — | — | — | 54 | 15,969 |
| 32,000 | `A_N_FIRST` | 32 | 64 | 1 | 109 | 31,961 |
| 32,000 | `A_K_FIRST` | **30** | **76** | 1 | 110 | 31,961 |
| 32,000 | `A_DUAL` | 0 | 84 | 23 | 111 | 31,968 |
| 32,000 | `A_DUAL_RANKED` | 0 | 83 | 23 | 111 | 31,969 |
| 32,000 | `A_FLAT` | — | — | — | 111 | 31,972 |

Two things the medians say that a mean would hide.

**The reorder is drastic at 16,000 and mild at 32,000.** Median delivered
recency falls 32 → 0 at the tighter budget and 32 → 30 at the looser one. At
16,000 the recency window is emptied on 492 of 871 questions; at 32,000, on 277.
The same manipulation is a different intervention at the two budgets, and this
study's primary is the milder one.

**Reordering does not free the coverage selector; removing the tier does.** The
questions where coverage delivers nothing move 722 → 738 under the reorder at
16,000 — it gets slightly *worse* — while `A_DUAL` moves them to 571. At 32,000
the same shape: 420 → 431 under the reorder, 326 under removal. Coverage sits
last in the fill order in every arm, so promoting K past recency does not reach
it.

### 5.4 Degenerate and absorbing states

No path in any arm has feedback: each is a pure function of (episodes, query,
budget, config). What can go wrong here is inertness — a manipulation that
changes nothing — and on this corpus that is a live hazard rather than a
formality.

| Budget | Payload byte-identical under both fill orders | Blocks truncated |
|---:|---:|---:|
| 16,000 | **120 / 871** (13.8%) | 871 / 871 |
| 32,000 | **424 / 871** (48.7%) | 871 / 871 |

**At the primary budget the manipulation cannot move 48.7% of the population.**
The budget still binds on every question — every block is truncated at both
budgets — but on nearly half of them the same episodes survive either order.
This is registered here, before the run, because it bounds the primary contrast
from above in a way no post-hoc reading may treat as a surprise. §7.1 shows the
remaining 447 questions leave every bar reachable.

### 5.5 Cost

Per question at 32,000, median over 40 questions per conversation, through each
arm's own entry point:

| Arm | p50 (ms) | p95 (ms) |
|---|---:|---:|
| `A_FLAT` | 24.5 – 28.0 | 25.5 – 28.9 |
| `A_N_FIRST` | 103.8 – 112.9 | 120.1 – 133.7 |
| `A_K_FIRST` | 104.5 – 113.7 | 120.8 – 137.7 |
| `A_DUAL` | 101.7 – 110.2 | 120.9 – 137.1 |
| `A_DUAL_RANKED` | 102.0 – 109.8 | 118.7 – 127.3 |

Reordering the fill costs **1 to 3 ms** against the shipped path. Every
selector arm costs four times the flat path, which is the clustering, and
TC-005 owns it.

## 6. Bars — locked here, before any arm's hit count exists

### 6.1 The null band, measured

TC-001's method, kept: compare each arm **against itself** at a budget nudged by
±0.5% and ±1%, and record only the paired gains and losses. A budget moved by
half a percent carries no mechanism claim, so whatever paired movement it
produces is what this endpoint does at a packing boundary rather than what an
architecture does. No arm's absolute hit count is recorded.

TC-001B's correction is kept: **both endpoints are measured**. One further
correction is made here: TC-002's primary budget is 32,000, and a band measured
at 16,000 is not this study's band, so the band is measured at **both** budgets.

Worst |net| over the four perturbations:

| Budget | Arm | any | complete |
|---:|---|---:|---:|
| 16,000 | `A_N_FIRST` | 4 | 4 |
| 16,000 | `A_K_FIRST` | 3 | 3 |
| 16,000 | `A_DUAL`, `A_DUAL_RANKED` | *3 (TC-001B)* | *3 (TC-001B)* |
| 16,000 | `A_FLAT`, `A_N_FIRST` | *4 (TC-001)* | — |
| 32,000 | `A_N_FIRST` | 6 | **7** |
| 32,000 | `A_K_FIRST` | 5 | 5 |
| 32,000 | `A_DUAL` | 4 | 4 |
| 32,000 | `A_DUAL_RANKED` | 0 | 1 |

**B = 7 questions at 32,000. B = 4 questions at 16,000.**

Each is the maximum over every value measured at that budget, inherited values
included, floored at TC-001's 4. **The primary contrast is judged against
B = 7.**

Three consequences, all registered before any contrast number exists.

**The band is budget-dependent and this study is the first to show it.** TC-001
and TC-001B both measured at 16,000 and got 4 and 3. At 32,000 the shipped
N-first arm moves 7 questions under a 1% budget nudge — nearly twice as much.
Had TC-002 inherited a band, it would have used a bar 43% too narrow at its own
primary budget.

**A band may not shrink.** It cannot shrink because a quieter arm joined the
comparison, and it cannot shrink because a budget at which arms are quieter was
added. This clause is why B at 16,000 is 4 rather than 3, and it was written
before the 32,000 numbers were read.

**Per-budget rather than a single maximum, and why that is not the loose
choice.** Applying 7 at 16,000 would be conservative; applying 4 at 32,000 would
be wrong. The band is a property of the endpoint at a budget, which is exactly
what the measurement shows. Both values are fixed here, neither is chosen after
a contrast is computed, and the primary uses the larger one.

**The quietest arm in this arc is `A_DUAL_RANKED`**, at 0 to 1 questions. The
noisiest is the shipped configuration. Nothing follows from that for any bar —
it is recorded because a band is an instrument property and this is what the
instrument does.

The sham perturbations run over the **871** questions with at least one resolved
evidence id. That is the primary population exactly, and a three-question
superset of the complete-evidence secondary's 868.

### 6.2 The statistic

Per question, paired. For a contrast `X vs Y`: `gains` = X delivers the
endpoint's evidence and Y does not; `losses` = the reverse; `ties` = both or
neither; `net = gains − losses`.

One-sided exact binomial (sign test) on the `d = gains + losses` discordant
pairs at `p = 0.5`:

- `p₊ = Σ_{i=gains}^{d} C(d,i) / 2^d` for the X direction
- `p₋ = Σ_{i=losses}^{d} C(d,i) / 2^d` for the Y direction

**Multiplicity.** Four registered contrasts, so Bonferroni across the family, at
the same divisor TC-001B used:

| | Per contrast |
|---|---:|
| α, "wins" tier | **0.0025** |
| α, "carries signal" tier | **0.025** |

Applied to all four contrasts including the primary, and registered before any
p-value exists. **The Bonferroni divisor stays at 4**; a family divisor may not
shrink after a Preflight number has been read.

### 6.3 Dispositions — both tiers registered before the run, per AGENTS.md §9.3

The same six-branch table applies to each contrast `X vs Y`, exhaustive over the
real line:

| ID | Condition | Verdict |
|---|---|---|
| **D1** | `net ≥ B` and `p₊ ≤ 0.0025` | **X_WINS** |
| **D2** | `net ≥ B` and `0.0025 < p₊ ≤ 0.025` | **X_CARRIES_SIGNAL** — justifies a successor, not an adoption |
| **D3** | `net ≤ −B` and `p₋ ≤ 0.0025` | **Y_WINS** |
| **D4** | `net ≤ −B` and `0.0025 < p₋ ≤ 0.025` | **Y_CARRIES_SIGNAL** |
| **D0a** | `\|net\| < B` | **NO_DIFFERENCE_ESTABLISHED — inside the band.** Explicitly *not* a win for whichever arm is simpler |
| **D0b** | `\|net\| ≥ B` and both `p₊ > 0.025` and `p₋ > 0.025` | **NO_DIFFERENCE_ESTABLISHED — outside the band, not separable** |

Instantiated:

| Contrast | X | Y | X wins is called | Y wins is called |
|---|---|---|---|---|
| **C1** | `A_K_FIRST` | `A_N_FIRST` | `K_FIRST_WINS` | `N_FIRST_WINS` |
| **C2** | `A_K_FIRST` | `A_FLAT` | `K_FIRST_WINS` | `FLAT_WINS` |
| **C3** | `A_DUAL` | `A_K_FIRST` | `DUAL_WINS` | `K_FIRST_WINS` |
| **C4** | `A_DUAL_RANKED` | `A_K_FIRST` | `RANKED_WINS` | `K_FIRST_WINS` |

**All four contrasts carry bars.** §7.1 shows every branch of the table is
reachable for each of them at both budgets, so unlike TC-001B's C3 none is
registered `DESCRIPTIVE`.

### 6.4 What the study concludes, written before it can be read

**C1 is the headline, whatever it says.**

- **C1 = `K_FIRST_WINS`** → EC-002's availability gain transfers off its
  original corpus. It bounds EC-002 upward, and it authorizes nothing: §0 and §9
  both forbid reading it as a shipping decision.
- **C1 = `N_FIRST_WINS`** → the fill-order effect reverses on this corpus, which
  bounds EC-002 to its own and is a stronger constraint than a null.
- **C1 = `NO_DIFFERENCE_ESTABLISHED`** → EC-002's gain is not demonstrated off
  its corpus at this power. Roadmap §3's own wording applies: this bounds
  EC-002, it does not retract it.

C2, C3 and C4 are reported with their dispositions in every case. **No
combination of them replaces C1 as the headline.**

## 7. Preflight Part 2 — checklist

| # | Check | Answer |
|---|---|---|
| **PF1** | Inputs exist | `locomo10.json` and `locomo_dev_embeddings.db`, both digest-asserted in §2, both already used by TC-001 and TC-001B at the same digests. Part 1 recorded 2,247 hits and **0 misses** in read-only mode, so this corpus costs no model call. Every source file's SHA-256 is recorded in the run header |
| **PF2** | Mechanism identity | §5.1, §5.2, and the three proven identities of §3.2 — 3,484 comparisons plus 1,742 collapse checks. §3.1's byte-identity check establishes that the arm is EC-002's arm |
| **PF3** | Gate ordering enforced | **G0** is a separate committed phase (§8.1). The run phase refuses to compute any arm's availability until `g0_reproduction.json` exists, is git-tracked, and reports `PASS` |
| **PF4** | Thresholds achievable | §7.1 |
| **PF5** | Comparison keys stable | Inherited from TC-001 unchanged: candidates key on `PairCandidate.identity`, questions on the canonical QA record's SHA-256 plus a duplicate ordinal, delivered episodes on the renderer's `turn` attribute. No uuid, path, timestamp or run-generated identifier enters any comparison |
| **PF6** | Reproduction anchor | §8.1 for the instrument, §3.1 for the manipulation, and §8.2 states what neither of them covers |
| **PF7** | Absorbing-state proof | §5.4. No feedback in any path; the inertness check that can fail is run on every question at both budgets and reported |
| **PF8** | Ablation length adequate | Not applicable: full-population offline replay over all 871 questions, not a sampled ablation. What it cannot detect is behavior that emerges past 1,365 candidates — TC-005's question |
| **PF9** | Surrogate audit | §7.2 |
| **PF10** | Live-evaluation requirement | §9.1, §9.2 |

### 7.1 PF4 — reachable, and failable, with the direction withheld

A sign test is decided by its discordant pairs; a contrast whose arms never
disagree cannot fire a bar in either direction, which is exactly the defect
DMR-001 locked and TC-001B's C3 was registered around. The probe is
`src/analysis/tc002_reachability.py`; its artifact is
`tc002_preflight_pf4_reachability.json`, and the module refuses to write a
directional key, so the split that decides each contrast is not readable from
it.

Discordant pairs, **primary endpoint (any evidence)**:

| Contrast | 16,000 | 32,000 | Best attainable one-sided *p* at 32,000 |
|---|---:|---:|---:|
| **C1** `A_K_FIRST` vs `A_N_FIRST` | 270 | 115 | 2.41 × 10⁻³⁵ |
| **C2** `A_K_FIRST` vs `A_FLAT` | 308 | 126 | 1.18 × 10⁻³⁸ |
| **C3** `A_DUAL` vs `A_K_FIRST` | 9 | **10** | 9.77 × 10⁻⁴ |
| **C4** `A_DUAL_RANKED` vs `A_K_FIRST` | 306 | 125 | 2.35 × 10⁻³⁸ |

On the complete-evidence secondary the counts are 265/120, 318/139, 13/15 and
315/140.

**Every branch is reachable for every contrast, at both budgets.** For C1, C2
and C4 that is obvious at three-figure discordant counts. For C3 it is not, and
the arithmetic is recorded rather than assumed. At 10 discordant pairs the
attainable `|net|` values are 0, 2, 4, 6, 8, 10 — parity forbids the odd ones —
so against `B = 7`:

| `|net|` | one-sided *p* | Branch |
|---:|---:|---|
| 10 | 9.77 × 10⁻⁴ | **D1 / D3** — reachable |
| 8 | 1.07 × 10⁻² | **D2 / D4** — reachable |
| ≤ 6 | — | **D0a** — reachable |

All six branches can fire. **C3's bar is reachable and thin**, and that is
stated now rather than discovered later: it needs 9 of its 10 discordant pairs
to fall the same way to reach `D2`, and all 10 to reach `D1`. A `D0a` on C3 is
therefore a statement about this study's power on that contrast, not evidence
that the two arms are alike. §9.6 repeats that where a reader will meet it.

**No contrast is registered without a bar**, and none may be given one later.

### 7.2 Surrogate audit — can this pass while the property it certifies is false?

| Claim | Can it pass while false? | Residual, accepted |
|---|---|---|
| "Evidence was delivered" | Yes. Presence is not use — a reader can receive the text and answer wrongly | LV-001 measured 16/16 offline against 1.5/8 live. §9.2. Accepted and named, not repaired here |
| "The manipulation is EC-002's" | Yes, if EC-002's pipeline drifted in a way `git diff` cannot see — an environment or dependency change | §8.2. Accepted: this study does not re-run EC-002 and says so |
| "The band is the endpoint's wobble" | Yes, if a ±1% budget nudge is not representative of the noise a real comparison meets | Inherited from TC-001's method and now measured at two budgets, which showed the band is budget-dependent. Accepted; a sham is a sham |
| "The contrast measures fill order" | Only if both arms see identical candidates in identical within-tier order | Not a residual: §3.2 proves it on 3,484 comparisons rather than arranging it |
| "C3 separates `A_DUAL` from `A_K_FIRST`" | **No — it can fail while the arms genuinely differ.** 10 discordant pairs is thin | §7.1 and §9.6. Registered before the run |
| "K-first is only a fill order" | Yes, if the function also changed candidate sets or render tiers | Not a residual: §5.2 measures both, at 1,742 and 871/871 |

## 8. Gates and registered robustness checks

### 8.1 G0 — the reproduction anchor, committed before the run phase opens

`A_N_FIRST` **is** TC-001's `A_TIERED`, and `A_FLAT` is TC-001's `A_FLAT`. So
this study's instrument must reproduce TC-001's committed table exactly before
it is allowed to measure anything new. The values are transcribed here rather
than read out of the artifact, so a corrupted artifact fails the gate instead of
redefining it:

| Budget | Endpoint | flat | tiered | gains | losses | net |
|---:|---|---:|---:|---:|---:|---:|
| 16,000 | complete | 749 | 314 | 8 | 443 | −435 |
| 16,000 | any | 803 | 381 | 8 | 430 | −422 |
| 32,000 | complete | 810 | 633 | 7 | 184 | −177 |
| 32,000 | any | 842 | 687 | 9 | 164 | −155 |

Both the freshly computed values and TC-001's committed
`runs/tc001/run/summary.json` are compared against this table. G0 runs as a
separate phase, writes `runs/tc002/g0/g0_reproduction.json`, and **is committed
before the run phase executes**. The run phase refuses to open an arm until that
artifact exists, is git-tracked, and reports `PASS`.

G0 also carries §3.1's provenance check: a non-empty `git diff` on any of the
six EC-002 files stops the study.

### 8.2 What G0 does not establish, stated plainly

G0 proves this instrument reproduces **TC-001** exactly. It does not re-run
EC-002 and does not re-derive EC-002's 152. The identity of the manipulation is
established statically by §3.1's byte-identity check, and the limitation is
recorded rather than papered over: if EC-002's own pipeline had drifted in a way
invisible to `git diff` — an environment change, a dependency change — this
study would not detect it. The reason it is not re-run is mechanical and is
given in §3.1: its runner refuses to execute off its own branch, and making it
execute would falsify its committed integrity record.

### 8.3 Wrapper-matched robustness for C2, C3 and C4 — no bar

One further pass at the primary budget with `A_K_FIRST` charged
`32,000 − 18 = 31,982` characters, so that the arm carrying a non-empty
`recent_context` block pays the same fixed wrapper as the arms that do not.
Reported for C2, C3 and C4. **C1 is excluded**, because it is symmetric already
and the adjustment would break that.

This check carries **no bar**. It is reported as agreeing or not agreeing with
the primary pass, and a disagreement is a finding to state, not a verdict to
substitute.

## 9. What a result here does not establish

### 9.1 Nothing that authorizes shipping the order change

Decided in §0 and repeated here because it is the decision most likely to be
argued with a number on the table. §9.3 of `PAPER_002.md` is the binding
evidence on adoption. A positive C1 makes the availability claim more general;
it does not make the adoption claim true, and the two came apart once already in
this programme's own record.

### 9.2 Nothing about answers

LV-001 measured 16 of 16 offline availability against 1.5 of 8 live. An
availability margin is an availability margin. TC-006 owns the reader, and its
own first task is establishing whether its instrument can resolve a margin at
all.

### 9.3 Nothing about the recency window's real behaviour

`PAPER_002.md` §3.4 records that no live study ran a true last-*N* window; the
studies ran a rotation and, before that, a locked prefix. This study measures
allocation between tiers as they are, on a finished transcript where "the last
32 turns" is an arbitrary slice. It cannot measure what the recency tier was
built to do, and a result against that tier is not a result against its purpose.

### 9.4 Nothing that transfers further

Four conversations of one dialogue style. A transfer from LongMemEval to LoCoMo
is one transfer, and §5.3 already shows the manipulation is a different
intervention at the two budgets of the same corpus.

### 9.5 Not confirmatory

Roadmap §0.1. This corpus has been observed by TC-001 and TC-001B, and the arms
were chosen with their results known. Bars locked before any number here exists
makes this registered; a registered study on an observed corpus is
characterization.

### 9.6 A `D0a` on C3 is a power statement, not an equivalence claim

C3 has 10 discordant pairs at the primary and needs 8 of the 10 to fall one way
to fire anything. If it lands `D0a`, the correct reading is that this study
cannot separate `A_DUAL` from `A_K_FIRST` on this endpoint at this power.
Equivalence needs an equivalence test with a registered margin, and this study
registers none.

## 10. Dependency, and the Rule 4 re-read

**Dependency line, as the roadmap states it:** requires a second store with
evidence labels where both orders can be replayed over frozen candidate
identities.
**Satisfied.** LoCoMo development supplies it, and TC-001 and TC-001B have both
demonstrated replay over frozen candidate identities on it. Part 1 demonstrates
the specific clause — both orders — on 3,484 comparisons.
**Expiry:** none — the dependency is already satisfied.

**What this blocks:** nothing. Explicitly, it does not gate shipping the order
change (§9.1).

TC-002 reporting triggers `TC_ARC_ROADMAP.md` Rule 4: every other study's
dependency line is re-read from the roadmap file and logged in
`TC_ARC_DEPENDENCY_LOG.md` with an explicit per-study verdict, in the same
commit as the report and before the next study is registered.

## 11. Artifacts and order

1. Commit Preflight Part 1 and PF4, with their modules and artifacts. *(Done at
   `d1357803`.)*
2. Commit **this registration alone**.
3. Commit the study implementation and its tests.
4. Run and commit **G0**.
5. Only after the G0 commit, run the study and commit its artifacts.
6. Commit the report with this file's commit SHA and SHA-256 in its header.
7. Rule 4 re-read, `README.md`, `AGENTS.md` digest, memory.
8. Open the study pull request.

```text
src/analysis/tc002_exploration.py          Preflight Part 1
src/analysis/tc002_reachability.py         PF4
src/analysis/tc_standing_arms.py           the standing arms
src/analysis/tc002_study.py                the study
scripts/run_tc002_preflight.py
scripts/run_tc002_reachability.py
scripts/run_tc002_study.py
tests/test_tc002_study.py
tests/test_dual_arm_standing.py
experiments/components/tier_cost/artifacts/tc002/preflight/
experiments/components/tier_cost/runs/tc002/g0/
experiments/components/tier_cost/runs/tc002/run/
experiments/components/tier_cost/TC_002_REPORT.md
```

## 12. Authorization

The author directed on August 22, 2026, immediately after TC-001B closed:

> *"Sounds good, lets move on to TC-002. I want the dual arm to be part of the
> test suite moving forward."*

The first clause authorizes TC-002 as the roadmap scopes it. The second is
implemented as §3's standing arms, `src/analysis/tc_standing_arms.py`, roadmap
§1.1, and `tests/test_dual_arm_standing.py` — and it is why C3 and C4 exist.
