# TC-001B — Does relevance plus coverage earn its place, with recency removed?

**Document type:** Study pre-registration
**Status:** `REGISTERED — bars locked before any arm's availability was computed`
**Standing sought:** `REGISTERED-OFFLINE` — pre-registered, zero generative calls,
replayable against a retained embedding cache, on a corpus already observed.
Capped as characterization, and capped further by §9.1: the arms were chosen
after TC-001's result was known.
**Date:** August 22, 2026
**Branch:** `study/tc-arc-tier-cost`
**Escalated from:** `amendments/AMENDMENT_001_dual_arm_escalation.md`, which
records the author instruction and why `AGENTS.md` §5 forbids answering it
inside TC-001.
**Predecessors:** TC-001 (`TC_001_REPORT.md`), HH-002, EC-002, IC-001, DR-002,
LV-001.

---

## 0. What this is, and what it is not

TC-001 asked whether the shipped four-tier stack beats a flat cosine ranking on
evidence delivery, and answered **`D3 FLAT_WINS`** — 749 questions against 314,
net −435, p = 6.98 × 10⁻¹²⁰. Its §3 attributed **61% of the tiered arm's
delivered characters** to the recency window, and its §5 recorded the obvious
objection to reading that as a verdict on the architecture:

> LoCoMo asks questions about a whole finished conversation, so a recency window
> is close to worthless here **by construction** — its 61% budget share buys
> almost nothing on this corpus and might buy a great deal on a live continuing
> conversation, which is the setting the tier was built for.

**This study removes the recency tier and repeats the measurement.** If the
tiered architecture's remaining machinery — the K-threshold similarity path and
the A3 coverage selector — earns its place, this is where it shows.

It is **not** a rescue of TC-001's losing arm: TC-001's verdict stands, its bars
are untouched, and this document cannot change either. It is **not** a tuning
study; the two removed-recency arms are the only two registered and no third may
be added after the run. It is **not** a reader study, and it is **not** a
deployment recommendation: `EpisodicConfig.recency_window_n` stays at 32 whatever
this finds, because a delivery result on a corpus with no live continuation
cannot decide the tier's fate in the setting it was built for.

## 1. The questions

Four contrasts, all paired, all over the same 868 questions:

| | Contrast | What it asks |
|---|---|---|
| **C1** | `A_DUAL` vs `A_FLAT` | **The primary.** With recency gone, does relevance plus coverage deliver evidence more often than a flat cosine ranking? |
| **C2** | `A_DUAL` vs `A_TIERED` | What did the recency tier cost on this corpus? |
| **C3** | `A_DUAL_RANKED` vs `A_FLAT` | The same as C1, with TC-001 §4's store-order defect removed from the K tier. **`DESCRIPTIVE`, no bar** — §7.1 found its bar unreachable before the lock |
| **C4** | `A_DUAL_RANKED` vs `A_DUAL` | What did that defect cost? |

**C1 is the headline, whatever it says.** Registered here so that C3 cannot be
promoted to the headline afterwards if it happens to read better. C1 measures the
mechanism as it is shipped, minus one tier; C3 measures a mechanism that has
never been shipped.

## 2. Corpus, unit, budget — inherited and frozen

Everything in this section is TC-001's, unchanged, and Amendment 001 §3.2 binds
this study to it. Any departure is a defect in this study, not a licence.

**Corpus.** LoCoMo development: `conv-41`, `conv-42`, `conv-47`, `conv-48` per
`experiments/external/locomo/LOCOMO_CORPUS_LOCK.md`. 1,365 adjacent-turn pairs,
882 question records, **871** unique by content, **868** with fully resolvable
evidence and no unresolved ids.

**Unit.** The adjacent-turn pair, keyed on `PairCandidate.identity`.

**Vectors.** The CC-006-protected cache `locomo_dev_embeddings.db`, opened
read-only with its file and content digests asserted. A miss raises rather than
embedding. Zero model calls; a `ModelCallGuard` replaces every entry point that
could load or query the carried model with a raise.

**Budgets.** **16,000 characters primary**, 32,000 secondary with no bars. Exact
serialized cost (DR-001 renderer), `DROP_POLICY =
"marginal_gain_order_skip_on_overflow"`.

**The population is spent.** LoCoMo development was opened by NF-003, NF-004,
HH-001, HH-002 and TC-001. Nothing here can be `CONFIRMATORY` and §9 says so
again at the end.

## 3. Arms

All four are offered identical candidate identities, identical vectors, the
identical DR-001 renderer, the identical `pack_stm_payload` with the identical
drop policy, and the identical budget. **The only thing that differs is which
candidates each arm hands the packer, and in what order.**

| Arm | Construction | New code |
|---|---|---|
| `A_FLAT` | Cosine descending over the whole store, packed to budget. TC-001's flat arm, byte for byte | none |
| `A_TIERED` | `episodic.build_context` as shipped: recency N=32, then K ≥ 0.48, then A3 coverage over the full pool, packed N-first | none |
| `A_DUAL` | `episodic.build_context` with `EpisodicConfig(recency_window_n=0)`. Relevance and coverage only | **none** — one config field |
| `A_DUAL_RANKED` | `A_DUAL` with the K tier offered to the packer in cosine order rather than store order | `compose_context`, §3.1 |

`A_FLAT` and `A_TIERED` are present as **anchors, not as fresh measurements**.
§8.1 requires them to reproduce TC-001's committed numbers exactly; if they do
not, this study stops.

### 3.1 Why `A_DUAL` needs no new mechanism code, and `A_DUAL_RANKED` does

`_recency_window` already returns `[]` for `n <= 0`, and `EpisodicConfig`
already validates `recency_window_n >= 0`. `A_DUAL` is therefore the shipped
function with one field set to zero — not a reimplementation, not a fork, and
not a branch that only this study can reach.

`A_DUAL_RANKED` cannot be built that way, because the ordering it changes is a
line **inside** `build_context`:

```python
k_hits = [e for e in episodes if relevance_by_id[str(e["id"])] >= config.k_threshold]
```

and `episodic/src/episodic/_context.py` is SHA-256 pinned inside TC-001's
committed run header. Editing it would falsify a committed record. So
`compose_context` restates the composition locally with `k_order` as its only
addition, and **the Preflight holds it to the original**: with
`k_order="store"`, `compose_context` must equal `build_context` byte for byte
and tier count for tier count on every question, at both budgets, under both
configurations — 3,484 comparisons. **One mismatch stops the study.** A
restatement proven equal to the original is measurable; one merely believed
equal is not.

### 3.2 The wrapper asymmetry, and where it now applies

TC-001 §3.1 registered an 18-character asymmetry: the flat arm's empty
`recent_context` block costs a 52-character wrapper against the tiered arm's 70.

**`A_DUAL` renders an empty `recent_context` block too, so C1 — the primary
contrast — is wrapper-symmetric at 52 characters against 52.** The asymmetry
that TC-001 had to check by robustness does not exist in this study's primary,
and the same is true of C3 and C4.

It does exist in **C2**, where `A_DUAL` is 18 characters cheaper than
`A_TIERED`, in `A_DUAL`'s favour. §8.2 registers the matched check for C2 alone.

### 3.3 No arm may be added after the run

`AGENTS.md` §7. Four arms, four contrasts, registered here. A fifth
configuration suggested by these results is a new study with its own
registration — as this one is for TC-001.

## 4. Endpoints

Evidence availability, read off the delivered block by candidate identity. No
inference, no judge, no reader, no string matching against an answer key.
Delivered episodes are recovered from the payload by the renderer's own
`<episode turn="N">` attribute.

**Primary — complete evidence delivery.** Whether *every* pair carrying one of a
question's resolved evidence dialogue ids is present in the delivered block.
Population: the **868** questions with at least one resolved id and none
unresolved.

**Secondary, no bars:**

- Any-evidence delivery over all **871** questions with ≥1 resolved id.
- Both endpoints at the 32,000-character budget.
- **Delivered composition by tier** for `A_TIERED`, `A_DUAL` and
  `A_DUAL_RANKED` — recency, K and coverage counts — and, when evidence
  arrived, which tier carried it. TC-001 §3 found coverage carried evidence on
  **8 of 871** questions and was the sole carrier on 3, with the recency tier
  holding 61% of the characters. Whether coverage does more when it is not
  starved is the descriptive question this study is best placed to answer, and
  it is named here before it is measured.
- Delivered episodes and characters per arm, as distributions.
- Per-conversation (4) and per-LoCoMo-category (5) breakdowns of every contrast.
- **The discordant pairs of C1, pre-specified.** For each pair, the flat cosine
  rank of the question's worst-ranked evidence episode, and which tier of
  `A_DUAL` carried the evidence when it arrived. TC-001 found the losing side's
  worst-ranked evidence at cosine rank p50 3 and its 8 gains at ranks 90–227;
  the same cut is registered here before this study's split is known.

## 5. Preflight Part 1 — what the arms actually do

Run before this document was written, artifact
`artifacts/tc001b/preflight/tc001b_preflight_part1.json`. It contains **no arm's
absolute availability and no cross-arm contrast**, for the reason §6.1 gives.

### 5.1 Behavioral identity, in one falsifiable sentence each

- `A_DUAL` delivers **no** episode that `A_TIERED` would have counted as
  recency, because `_recency_window` returns `[]` at N=0. Checked, not assumed.
- `A_DUAL_RANKED` differs from `A_DUAL` **only** when the K tier is binding: if
  every K hit fits, both deliver the same set and only the order inside the
  block differs. **Measured: identical delivered sets on 286 of 871 questions**,
  so the two arms differ on 585 — the ceiling on C4's discordant count, and
  comfortably above it.
- `compose_context(k_order="store")` **is** `build_context` (§3.1). **Measured:
  3,484 of 3,484 comparisons byte-identical and tier-count identical, across
  both budgets and both configurations. The gate passed.**

### 5.2 Name-to-behavior — including order, which TC-001 did not ask

TC-001's report records its own Preflight gap in §4:

> Its name-to-behavior check confirmed *which* candidates each tier holds …
> and never asked *in what order each tier offers them*. That is the same class
> of gap as the N-tier mislabel this programme spent eleven studies not
> noticing.

This Preflight asks it directly. For every question with at least three
delivered K episodes it checks whether `A_DUAL`'s delivered K prefix is in store
order, whether it is in relevance order, and whether `A_DUAL_RANKED`'s is in
relevance order. The claim "`A_DUAL_RANKED` offers K best-first" is therefore a
measured property of the delivered block, not a description of the code.

**Measured, over the 865 questions with at least three delivered K episodes:**

| Delivered K prefix is in… | `A_DUAL` | `A_DUAL_RANKED` |
|---|---:|---:|
| store order | **865 / 865** | — |
| relevance order | **1 / 865** | **864 / 865** |

TC-001 §4's finding is therefore confirmed *before* this study's bars are
locked rather than discovered after its verdict, and `A_DUAL_RANKED` does what
its name says. The single question where the ranked arm's prefix is not in
relevance order is a tie in the K ordering key and is recorded rather than
tidied away.

### 5.3 Distributions, not summaries

Delivered episodes, delivered characters, and the recency/K/coverage split for
all four arms, as full distributions (min, p25, p50, p75, max, mean, and the
count of zeros) over all 871 questions at 16,000 characters. The medians and
means, which show what removing the tier does to the budget's shape:

| Arm | Episodes p50 | Chars p50 | Recency p50 | K p50 | Coverage mean |
|---|---:|---:|---:|---:|---:|
| `A_FLAT` | 54 | 15,969 | — | — | — |
| `A_TIERED` | 54 | 15,961 | 32 | 22 | 1.39 |
| `A_DUAL` | 56 | 15,965 | **0** | **52** | **8.37** |
| `A_DUAL_RANKED` | 54 | 15,966 | 0 | 50 | 8.37 |

All four arms fill essentially the same number of characters. What the recency
tier held is redistributed to K and, to a much smaller extent, to coverage. No
arm's availability appears in this table or anywhere else in the Part 1
artifact.

### 5.4 Degenerate and absorbing states

Counted explicitly for `A_DUAL`: questions where it delivers zero episodes, zero
K episodes, zero coverage episodes, and where K leaves no room for coverage at
all. TC-001 found the shipped arm delivering nothing from coverage on 722 of 871
questions; if `A_DUAL` is in the same state, the study still runs, but the
report says so rather than describing a two-tier arm that is really one.

**Measured for `A_DUAL`:** zero episodes on **0** questions, zero K episodes on
**0**, zero coverage episodes on **571 of 871**, and K leaves no room for
coverage on the same **571**. So `A_DUAL` is a two-tier arm on 300 questions and
a one-tier arm on 571 — better than `A_TIERED`'s 722, and still the majority.
The report must describe it that way, and §4's composition secondary is where
that lands.

Neither path has feedback: no output of one question influences another. There
is no absorbing state to prove absent, and the constant-output check that *can*
fail is run on every question.

### 5.5 Cost

Per-question wall clock for both new arms at this corpus's pool sizes (323–355
episodes), alongside TC-001's measurement of the flat and tiered paths.

**Measured, p50 milliseconds per question:** `A_DUAL` 91.6–97.0,
`A_DUAL_RANKED` 90.9–96.0, against TC-001's `A_TIERED` 89.5–102.3 and `A_FLAT`
13.4–15.9. **Removing the recency tier buys no latency back.** The coverage
selector's clustering dominates the path, exactly as `PAPER_002.md` §10's 81%
figure predicts, and both new arms remain roughly 6× the flat path. This is
recorded here so that no delivery result below can be mistaken for a cost
result; §9.4 says the same thing about the other direction.

## 6. Bars — locked here, before any arm's hit count exists

### 6.1 The null band, measured

TC-001's method: compare each arm **against itself** at a budget nudged by
±0.5% and ±1%, and record only the paired gains and losses. A budget moved by
half a percent carries no mechanism claim, so whatever paired movement it
produces is what this endpoint does at a packing boundary rather than what an
architecture does. No arm's absolute hit count is recorded.

**One correction to TC-001's procedure.** TC-001 measured its band on the
any-evidence endpoint and applied it to the complete-evidence primary — recorded
in Amendment 001 §5, where it changes nothing at a margin of 435 against 4.
**This study measures the band on both endpoints** and takes the maximum.

| Arm | Endpoint | Worst \|net\| over the four perturbations |
|---|---|---:|
| `A_DUAL` | complete | **3** |
| `A_DUAL` | any | 3 |
| `A_DUAL_RANKED` | complete | 1 |
| `A_DUAL_RANKED` | any | 2 |
| `A_FLAT`, `A_TIERED` | any (TC-001) | 4 |

**B = 4 questions**, the maximum over all four arms and both
endpoints.

The two new arms are **quieter** than the flat and tiered arms TC-001 measured,
not louder: their worst sham movement is 3 questions against the inherited 4.
The floor clause registered before the measurement was read therefore decides
the value — *if the maximum over the new arms had been below the inherited 4, B
would still be 4, because a band cannot shrink because a quieter arm joined the
comparison.* It did, and B is 4, which is also TC-001's band; the two studies
are on the same scale by measurement rather than by assumption.

One population note, inherited from TC-001 §6.1 with the same consequence. The
sham perturbations run over the **871** questions with at least one resolved
evidence id, a three-question superset of the 868-question complete-evidence
population. At |net| ≤ 3 the difference cannot change B.

### 6.2 The statistic

Per question, paired. For a contrast `X vs Y`: `gains` = X delivers complete
evidence and Y does not; `losses` = the reverse; `ties` = both or neither;
`net = gains − losses`.

One-sided exact binomial (sign test) on the `d = gains + losses` discordant
pairs at `p = 0.5`:

- `p₊ = Σ_{i=gains}^{d} C(d,i) / 2^d` for the X direction
- `p₋ = Σ_{i=losses}^{d} C(d,i) / 2^d` for the Y direction

**Multiplicity.** Four registered contrasts, so Bonferroni across the family:

| | TC-001 | TC-001B, per contrast |
|---|---:|---:|
| α, "wins" tier | 0.01 | **0.0025** |
| α, "carries signal" tier | 0.10 | **0.025** |

Applied to all four contrasts including the primary. This is the conservative
direction — it makes "no difference established" easier to reach, not harder —
and it is registered before any p-value exists.

**The divisor stays at 4 even though §7.1 leaves only three contrasts carrying
bars.** Three would give a looser 0.00333, and a family divisor may not shrink
after a Preflight number has been read.

### 6.3 Dispositions — both tiers registered before the run, per AGENTS.md §9.3

The same six-branch table applies to each contrast `X vs Y`, exhaustive over the
real line:

| ID | Condition | Verdict |
|---|---|---|
| **D1** | `net ≥ B` and `p₊ ≤ 0.0025` | **X_WINS** |
| **D2** | `net ≥ B` and `0.0025 < p₊ ≤ 0.025` | **X_CARRIES_SIGNAL** — justifies a successor, not an adoption |
| **D3** | `net ≤ −B` and `p₋ ≤ 0.0025` | **Y_WINS** |
| **D4** | `net ≤ −B` and `0.0025 < p₋ ≤ 0.025` | **Y_CARRIES_SIGNAL** |
| **D0a** | `\|net\| < B` | **NO_DIFFERENCE_ESTABLISHED — inside the band.** Explicitly *not* a win for the simpler arm |
| **D0b** | `\|net\| ≥ B` and both `p₊ > 0.025` and `p₋ > 0.025` | **NO_DIFFERENCE_ESTABLISHED — outside the band, not separable** |

Instantiated:

| Contrast | X | Y | X wins is called | Y wins is called |
|---|---|---|---|---|
| **C1** | `A_DUAL` | `A_FLAT` | `DUAL_WINS` | `FLAT_WINS` |
| **C2** | `A_DUAL` | `A_TIERED` | `DUAL_WINS` | `TIERED_WINS` |
| **C3** | `A_DUAL_RANKED` | `A_FLAT` | *no bar — `DESCRIPTIVE`, §7.1* | *no bar* |
| **C4** | `A_DUAL_RANKED` | `A_DUAL` | `RANKED_WINS` | `DUAL_WINS` |

### 6.4 What the study concludes, written before it can be read

Registered so the headline is not chosen after the fact:

- **C1 = `DUAL_WINS`** → on this corpus at this budget, relevance plus coverage
  beats a flat ranking once recency is removed, and TC-001's verdict is
  attributable to the recency tier. This does **not** authorize deleting the
  tier; §9 and Amendment 001 §4 both forbid it.
- **C1 = `FLAT_WINS`** → removing recency is not sufficient. The flat arm's
  advantage in TC-001 survives the confound its own report named.
- **C1 = `NO_DIFFERENCE_ESTABLISHED`** → the dual arm is not separable from the
  flat arm on this endpoint at this power, and C2's margin is then the only
  quantity this study establishes.

C2, C3 and C4 are reported with their dispositions in every case. **No
combination of them replaces C1 as the headline.**

## 7. Preflight Part 2 — checklist

| # | Check | Answer |
|---|---|---|
| **PF1** | Inputs exist | `locomo10.json` and `locomo_dev_embeddings.db`, both digest-asserted, both already used by TC-001 at the same digests. Part 1 recorded its hits and **0 misses** in read-only mode, so this corpus costs no model call. Every source file's SHA-256 is recorded in the run header |
| **PF2** | Mechanism identity | §5.1, §5.2. Includes the ordering check TC-001's Preflight omitted, and the 3,484-comparison identity gate of §3.1 |
| **PF3** | Gate ordering enforced | **G0** is a separate committed phase (§8.1). The run phase refuses to compute any arm's availability until `g0_reproduction.json` exists, is git-tracked, and reports `PASS` |
| **PF4** | Thresholds achievable | §7.1 |
| **PF5** | Comparison keys stable | Inherited from TC-001 unchanged: candidates key on `PairCandidate.identity`, questions on the canonical QA record's SHA-256 plus a duplicate ordinal, delivered episodes on the renderer's `turn` attribute. No uuid, path, timestamp or run-generated identifier enters any comparison |
| **PF6** | Reproduction anchor | §8.1. G0 reproduces TC-001's committed primary and secondary tables from the same dataset and cache, by value and not by count alone |
| **PF7** | Absorbing-state proof | §5.4. No feedback in any path; the constant-output check that can fail is run on every question |
| **PF8** | Ablation length adequate | Not applicable: full-population offline replay over all 868 evaluable questions, not a sampled ablation. What it cannot detect is behavior that emerges past 1,365 candidates — TC-005's question |
| **PF9** | Surrogate audit | §7.2 |
| **PF10** | Live-evaluation requirement | §9 |

### 7.1 PF4 — reachable, and failable, with the direction withheld

A sign test is decided by its discordant pairs; a contrast whose arms never
disagree cannot fire a bar in either direction, which is exactly the defect
DMR-001 locked. The probe
(`artifacts/tc001b/preflight/tc001b_preflight_pf4_reachability.json`) computes
**the discordant count only**. It does not compute which way the pairs fall, and
`_forbid_direction` walks the artifact and raises on any key named `gains`,
`losses`, `net`, `winner`, `direction`, or ending in `_hits`, `_only`, `_wins`.
A count with no direction cannot favour an arm, so it is safe to read before the
lock and is exactly what PF4 needs.

| Contrast | Discordant pairs, complete endpoint, 16,000 | Smallest reachable one-sided p |
|---|---:|---:|
| **C1** `A_DUAL` vs `A_FLAT` | 305 | 1.53 × 10⁻⁹² |
| **C2** `A_DUAL` vs `A_TIERED` | 278 | 2.06 × 10⁻⁸⁴ |
| **C3** `A_DUAL_RANKED` vs `A_FLAT` | **3** | **0.125** |
| **C4** `A_DUAL_RANKED` vs `A_DUAL` | 302 | 1.23 × 10⁻⁹¹ |

**C1, C2 and C4 are reachable and failable.** Each has enough discordant pairs
that a bar at either α can fire in either direction, and enough that it can also
fail to fire.

**C3 is not, and this is exactly the defect PF4 exists to catch.** Three
discordant pairs put its best attainable one-sided p at **0.125** — above α
(0.0025) *and* above the signal α (0.025) — and `|net| ≤ 3 < B = 4` means the
only branch of §6.3 it can ever reach is `D0a`. A bar there would be
unreachable by construction, which is DMR-001's locked defect repeated with the
lesson in front of me.

**C3 therefore carries no bar and is registered `DESCRIPTIVE`.** Its gains,
losses, net, discordant count and exact p are reported like any other contrast;
no disposition is attached to it and none may be read into it afterwards. Note
what the count does and does not say: 3 discordant pairs out of 868 means
`A_DUAL_RANKED` and `A_FLAT` reach the same complete-evidence outcome on 865
questions. It does **not** say which arm the three fall to, and this probe
refuses to compute that.

**The Bonferroni divisor stays at 4** (§6.2), even though only three contrasts
now carry bars and three would give a looser 0.00333. A family divisor may not
shrink after a Preflight number has been read. The stricter threshold costs
nothing here and removes any question about the direction of the adjustment.

### 7.2 Surrogate audit — can this pass while the property it certifies is false?

Two residuals, inherited from TC-001 and unchanged:

- **Evidence present is not evidence used.** A delivered block containing the
  answer-bearing pair does not mean a reader would find or use it. LV-001
  measured 16 of 16 offline availability against 1.5 of 8 live. Every number in
  this study is an availability number.
- **A hit says nothing about what surrounds it.** Two arms can both deliver a
  question's evidence with very different amounts of distractor text around it,
  and this endpoint scores them identically.

One residual is new and belongs to this study:

- **The identity gate certifies equality under `k_order="store"`, not
  correctness under `k_order="relevance"`.** It proves `compose_context` is
  `build_context` when told to behave like it. It cannot prove that the ranked
  variant's behavior is the *right* counterfactual for TC-001 §4's finding —
  only that it differs from the shipped one in exactly one registered way.

## 8. Gates and registered robustness checks

### 8.1 G0 — the reproduction anchor, committed before the run phase opens

G0 re-runs `A_FLAT` and `A_TIERED` at both budgets and requires **exact**
agreement with TC-001's committed `runs/tc001/run/summary.json`:

| Endpoint | Budget | `A_FLAT` | `A_TIERED` | gains / losses | net |
|---|---:|---:|---:|---:|---:|
| complete | 16,000 | 749 | 314 | 8 / 443 | −435 |
| any | 16,000 | 803 | 381 | 8 / 430 | −422 |
| complete | 32,000 | 810 | 633 | 7 / 184 | −177 |
| any | 32,000 | 842 | 687 | 9 / 164 | −155 |

**A failed G0 stops TC-001B.** If the two anchor arms do not reproduce, this
study's new arms are being measured by a different instrument than the one that
produced the result it is responding to, and nothing it reports would be
comparable.

### 8.2 Wrapper-matched robustness for C2 — no bar

C2 compares an arm with a 52-character wrapper against one with 70 (§3.2). The
check repeats C2 with `A_DUAL` charged the missing 18 characters — budget
15,982 against `A_TIERED`'s 16,000 — and reports whether C2's disposition moves.
It carries no bar and cannot change C2's registered disposition; it is reported
either way.

C1, C3 and C4 need no such check and none is registered for them.

## 9. What a result here does not establish

### 9.1 The arms were chosen after TC-001's result was known

This is the cap that matters and it is stated first. TC-001's report is public
and its §3, §4 and §5 are what suggested both new arms. Bars are locked here
before any of this study's numbers exist, which is what makes it registered
rather than exploratory — but a registered study built on an observed result is
characterization, and no outcome here is `CONFIRMATORY`. There is no sealed
corpus left to this programme to make it one.

### 9.2 Nothing about answers

Availability is not a verdict. LV-001: 16 of 16 offline against 1.5 of 8 live.
The live evaluation this endpoint requires is TC-006's, and TC-006's own first
task is establishing whether its instrument can resolve a margin at all.

### 9.3 Nothing that authorizes changing a default

Whatever C1 and C2 say, `recency_window_n` stays at 32. The reason is the same
one TC-001 gave and it is not weakened by removing the tier: **this corpus has
no live continuation**, so it cannot measure what the recency tier was built to
do. A tier that is worthless on a finished transcript may be essential on a
running one. Measuring that needs a corpus this programme does not have.

### 9.4 Nothing about the coverage selector's cost

`PAPER_002.md` §10 measures clustering at 81% of selection latency and rising.
If coverage delivers more here than it did in TC-001, that is a delivery
finding, not a cost-benefit finding. TC-005 owns the cost side.

### 9.5 Nothing that transfers

Four conversations of one dialogue style, 156 distinct episodes repeated across
the corpus. TC-002 owns transfer.

## 10. Dependency and the Rule 4 re-read

**Dependency line.** Requires a store with per-item evidence labels where all
four arms can be replayed over identical frozen candidate identities. Satisfied
today by LoCoMo development and demonstrated by TC-001.
**Expiry:** none.

**What this blocks:** nothing. Under `TC_ARC_ROADMAP.md` Rule 2 no study may
depend on a stage, and no TC study's dependency line names this one.

**Rule 4.** TC-001B reporting a verdict triggers the arc dependency re-read.
Every other study's dependency line is re-read from the roadmap file and logged
in `TC_ARC_DEPENDENCY_LOG.md` with an explicit per-study verdict before the next
study registers.
