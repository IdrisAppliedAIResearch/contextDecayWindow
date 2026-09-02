# Aspect v3 - Thesis Draft

**Status:** `DRAFT - not a pre-registration; nothing here is registered or authorized`
**Date:** September 2, 2026
**Owner:** taking ownership of the Aspect v3 direction
**Predecessors:** TC-007/008/010/011 (ASPECT-v1 origin) · HH-003 (its only live test) ·
DA-001…101 + HH-004/005 (the v2 attempt) · LV-009 (renderer evidence) ·
NF-004 anatomy and DA-004 (predictor precedents)
**Companion:** `experiments/audits/da_arc/DA_ARC_HH005_POST_MORTEM.md`

---

## 1. What is actually deployed

The shipped read path is `episodic-chat` 0.2.0, `EpisodeStore.context` →
`build_chat_context` → `retrieve_long_term`. Three channels, in this order:

1. **Additive recency.** The latest `recency_window_n=32` complete episodes,
   rendered *outside* the retrieval budget. Never subject to admission.
2. **CC80 ranking.** Hybrid dense/BM25 at frozen `0.8/0.2`, `k1=1.2`, `b=0.75`,
   producing a full permutation of the store with scores.
3. **Long-term allocation** under `retrieval_budget_chars=32000`, in one of two
   modes:

   - `aspect_enabled=False` — **the shipped default.** `_full_cc80`: pack the
     CC80 order, exact serialized cost, skip-on-overflow.
   - `aspect_enabled=True` — `_protected_aspect`, a 50/50 split at
     `aspect_share=0.5`:
     `[semantic ≤16k] + [ASPECT spread ≤16k] + [returned semantic slack → 32k]`

ASPECT-v1 itself (`_aspect.py`, "Frozen TC-011 static ASPECT") is **greedy
cost-normalized weighted max-coverage over facets**:

- Six deterministic facet families from spaCy `en_core_web_sm` 3.8.0 —
  `entity:`, `date:`, `number:`, `event:` (verb lemmas), `relation:`
  (head:dep:subtree over seven object dependencies), `noun:` (noun chunks).
- Facet IDF = `log((N+1)/(df+1)) + 1`.
- A facet's covered value is `max` over selected episodes of
  `cc80_score[ep] × idf[facet]`.
- Each step picks `argmax(marginal_gain / additive_weight(episode))`, ties broken
  toward better CC80 rank. Seeded by the semantic half's coverage. Stops on
  no-fit or non-positive marginal.

Measured behaviour on HH-003 (n=1540, ASPECT on): median 41 semantic + 37 aspect
episodes, `retrieval_chars_delivered` median 31,925 of 32,000 — the budget is
essentially full. Returned semantic slack is negligible: median 1, mean 0.6,
max 3.

### Two facts about the incumbent that the programme has not internalized

**ASPECT-v1's live benefit has never been established.** HH-003 is its only live
test: 46 gains, 32 losses, net **+14**, `p=.140538`. That is the entire evidential
basis for the arm that DA spent 101 studies trying to beat and that HH-005 treats
as the bar. It does not clear a conventional bar and no directional bar was
registered.

**ASPECT-v1 costs 92× the default path.** HH-003 median retrieval latency:

| Arm | median latency |
|---|---:|
| `A_EPISODIC` (CC80, ASPECT off) | 27.4 ms |
| `A_EPISODIC_ASPECT` (ASPECT on) | **2,522.7 ms** |

The cause is in the code, not the algorithm. `_protected_aspect` accepts an
optional `facet_bundle`, and **the deployed path never passes it** —
`_chat_context.py` calls `retrieve_long_term` without it, so
`prepare_facets(episodes, ...)` runs spaCy over **the entire store on every
query**. Facets are a pure function of episode text and carry no query
dependence. Nothing about them needs to be computed at read time.

---

## 2. What DA did

101 studies, August 29 to September 1, in four days. The programme was: take
NF-004's adjacent-turn pair candidates, treat each as a node in a temporal chain
within its source session, and follow explicit links to derivative context that
direct pair-ranking misses — then make that affordable by encoding it compactly.

The arc's trajectory, in its own document titles:

| Phase | Studies | Concern |
|---|---|---|
| Link feasibility | DA-001…007 | temporal vs event expansion, displacement, reserved headroom |
| Cross-corpus | DA-013…018 | LongMemEval transfer, phrase dictionaries |
| Compact encoding | DA-020…060 | atomic composition, dependency frontier, varint backrefs, cursors, postings |
| Parse and capacity | DA-070…096 | signature lattice, optimal sentinel parse, packet fallback, child streams |
| Freeze and runtime | DA-098…101 | frozen budget replay, indexed codec, flat suffix state |

It ended where it aimed: **DA-098** raised exact evidence availability from
pair-ranking's 1,024/1,098 to **1,068/1,098** at 32k — 44 gains, **0 losses**,
`p=1.14e-13`, with only 30 items still missing, all attributed to `FIT_OVERFLOW`.
**DA-101** preserved that exact allocation at 59.9 ms p50. On its own terms the
arc succeeded completely.

Then HH-004 decoded DA-098 and put it in front of a reader alone: **606/842**,
losing to every episodic control. HH-005 corrected the composition —
`[semantic ≤16k] + [DA-v2 derivative ≤16k]` — and scored **654/842** at 32k
against ASPECT-v1's **670**: 32 gains, 48 losses, net **−16**, `p=.0929`.

---

## 3. What DA got wrong

The full audit is in the post-mortem. Four findings, compressed:

1. **It never tested its own hypothesis.** All 101 studies declare
   `Planned model calls: 0`. Zero reader contact for the entire arc. HH-004, the
   first reader contact, cost **$1.7434**.
2. **Its headline metric could not express harm.** `ARCH_32` was built as an
   immutable `ARCH_16` prefix plus admissions under a *doubled* budget.
   Availability is monotone in what you pack; the "0 losses" was guaranteed by
   construction and carried no quality information.
3. **The incumbent was never a control.** Zero of 101 DA documents mention
   ASPECT. The arc optimized *addition vs pair-ranking on availability*; HH-005
   decided *substitution vs ASPECT-v1 on judged accuracy*. Three substitutions.
4. **The surrogate risk was logged and never gated.** 92 of 101 studies carry
   reader-caveat language, 24 formalize it as preflight PF9/PF10, none acted.

To that I add one finding from reading the HH-005 builder, and one negative
check that clears a suspicion:

**The arm changed the renderer as well as the allocator.** ASPECT-v1's members
arrive as `<episode turn="N">` blocks. DA-v2's arrive as
`<member index="i">` blocks in a `<derivative_context_v2>` channel — a different
tag, a different granularity (individual turns, not adjacent-turn pairs), and no
turn anchoring. HH-005 therefore cannot separate *what was selected* from *how it
was presented*, and **LV-009 is direct evidence that the second one matters**:
changing the renderer from pairwise to compact community, holding retrieval
constant, cost 49 gains against 80 losses, net −31 (−2.01 points). Some unknown
share of HH-005's 48 losses is renderer, not allocator.

**The slack confound is not material.** DA-v2's arm also dropped the returned
semantic slack channel. I measured it across all 1,540 HH-003 ASPECT items:
median 1 episode, mean 0.6, max 3. It does not account for the −16.

---

## 4. The fact that reframes the problem

Set the two decisive contrasts side by side. Same system, same corpus, same
measure on each side.

| | Offline: exact evidence availability | Live: judged answer correctness |
|---|---|---|
| **TC-011 / HH-003** | CC80 **771/819** beats ASPECT **749/810** | ASPECT **1205** beats CC80 **1191** (+14) |
| **DA-098 / HH-005** | DA-v2 **1068** beats pair **1024** (+44, 0 losses) | DA-v2 **654** loses to ASPECT **670** (−16) |

**Availability has now pointed the wrong way twice, in both directions.**

TC-011's registered disposition was `NO_CANDIDATE` with CC80 fallback — ASPECT
was the *least harmful* of four spread objectives, all of which lost to plain
CC80 on availability. ASPECT shipped anyway as an opt-in path, and when it was
finally measured live it won. DA-v2 did the opposite: it dominated on
availability by a margin no study in this programme has matched, and lost live.

This is not "availability is an incomplete proxy." An incomplete proxy is
uninformative. This proxy has been **actively misleading in both directions on
the only two occasions it has been checked against a reader**. Every allocator
decision in the TC and DA arcs — including the decision to ship ASPECT-v1 and the
decision to spend four days on DA — was made on a measure with a 0-for-2 record.

**And the mechanism is unmeasured.** Nobody knows why ASPECT-v1 wins live. HH-003
was its first and only live test and was not designed to explain anything; it
registered no mechanism analysis. The obvious guesses do not survive contact with
the data — ASPECT-on delivers *fewer* episodes than ASPECT-off (109 vs 114
median), and TC-011 measured its evidence *breadth* as lower than CC80's (15/23
vs 17/24). It is not more diverse and it is not denser. It wins for a reason
nobody has written down.

---

## 5. Thesis

> **The binding constraint on this system is reader utility, and the programme has
> never measured it. Every allocator to date — ASPECT-v1 included — has been
> selected on evidence availability, a measure with a 0-for-2 record against live
> outcomes. Aspect v3 therefore does not begin by proposing an allocator. It
> begins by building the missing measurement from evidence that has already been
> paid for, and only then allocates against it.**

Three claims, each falsifiable:

**C1 — Reader outcomes are predictable from pack-level context features where
availability is not.** The programme has one strong precedent and one warning.
DA-004 predicted *helpful* pack perturbations at grouped OOF **AUC .823** (all
six conversations .800–.960) from whole-pack blind features — but its *harm*
model was chance at **.504**. NF-004 item anatomy, using 58 **item-local**
features, reached only **AUC .576** (`p=.139`) and was registered
`NO_STABLE_PREDICTOR`. The shape that worked was pack-level, not item-local. The
label in every one of those studies was an *availability* discordance. No study
has ever used a **reader** discordance as the label.

**C2 — The useful part of ASPECT-v1 is small, identifiable, and separable from
its cost.** Its live margin is +14 of 1,540 at `p=.14`, for 2,522.7 ms. If the
margin is real it is carried by a specific and probably small subset of its ~37
admitted episodes per query. Identify that subset and the same benefit should be
obtainable at a fraction of the budget and the latency.

**C3 — DA's derivative channel is complementary, not competitive.** Its 32
rescues in HH-005 are items ASPECT-v1 misses. They were paid for by 48
displacements because the arm *substituted*. The additive shape — ASPECT-v1
retained, derivative context admitted only into headroom it earns — has never
been tested against ASPECT-v1 on reader accuracy.

---

## 6. What Aspect v3 is

Not an allocator, at first. A measurement, then an allocator constrained by it.

**The diagnostic corpus already exists and is already paid for.** Every context,
prediction and judgement below is sealed and committed:

| Contrast | Population | Discordant items |
|---|---|---:|
| HH-003 ASPECT-v1 vs CC80 | 1,540 | 78 (46 / 32) |
| HH-005 DA-v2 32k vs ASPECT-v1 | 842 | 80 (32 / 48) |
| HH-005 DA-v2 16k vs ASPECT-v1 | 842 | 73 (26 / 47) |
| HH-005 32k vs 16k | 842 | 49 (27 / 22) |
| HH-004 DA-only vs ASPECT-v1 | 842 | 184 (60 / 124) |

That is **464 discordant item–contrast pairs** with full context provenance —
fewer distinct items, since an item recurs across contrasts, and four further
HH-004 control contrasts are available on top. Analysing all of it needs **zero
model calls**. The arc that could not afford a reader was sitting next to a
reader-labelled corpus the whole time.

**Design constraints, taken from what the programme already knows:**

- **Hold the renderer fixed.** `<episode turn="N">` blocks, unchanged. LV-009 and
  HH-005 both changed presentation and selection together and neither can
  attribute its loss. v3 changes one thing at a time.
- **Additive, not substitutive.** ASPECT-v1 stays in the arm as the retained
  control path until something beats it on judged accuracy.
- **The decision contrast on day one.** Every AV study compares against
  ASPECT-v1, substitution or addition as the design requires, with a reader
  endpoint. No study in this arc reports availability as a primary.
- **Spend the reader early.** HH-004's rate puts a 100-item reader pilot well
  under a dollar. There is no budget argument for deferring it.

---

## 7. Proposed first studies

Draft only. Each needs its own pre-registration before any paid call.

**AV-001 — Reader-outcome anatomy.** *Zero model calls; analysis of sealed
artifacts.* Take the discordant items above. Build pack-level features in
DA-004's winning shape — coverage, redundancy, positional, facet-family and
budget-utilization statistics over the *whole delivered context*, not per
candidate. Fit grouped out-of-fold by conversation, with a permutation null, on
two labels separately: **rescue** and **harm**. Report AUC for each. Registered
bar: beat NF-004 anatomy's `.576` on the harm label, which is the one DA-004
could not fit at `.504`.
*This is the study that decides whether the thesis is workable.*

**AV-002 — ASPECT-v1 attribution.** *Splits into a zero-call half and a
cache-dependent half; see §7.1.* For each of HH-003's ASPECT rescues, identify
which admitted episodes carry the answer evidence and where they sit in ASPECT's
greedy admission order. Question: is the +14 carried by the first few admissions
or spread across all ~37? If the answer is "the first five", C2 holds and
`aspect_share=0.5` is 7× larger than it needs to be.

Two corrections to an earlier draft of this study. **The evidence-annotated
population is smaller than the contrast.** HH-003 spans ten conversations;
NF-004's evidence identities cover only its six holdout conversations, which is
848 of 1,540 items. Of the 46 rescues, **30** fall inside that coverage, and of
the 32 losses, **15**. AV-002 analyses 30 rescues, not 46. **And the greedy
`marginal` values are not sealed** — HH-003's `detail` carries `aspect_count` and
`coverage_count` as scalars and no trace — so any question about marginal gains
or about the minimum retaining aspect share requires re-running
`_protected_aspect`, which is not a zero-call operation. The membership-and-order
question is answerable offline; the marginal-and-counterfactual question is not.

**AV-003 — Write-time facet cache.** *Engineering, no research risk.* Compute
facets on append, store beside the episode vector, pass `facet_bundle` through
`build_chat_context`. Gate on **byte-identical** allocation against HH-003's
sealed ASPECT contexts (`119a3152…`) across all 1,540 items — this must change
nothing but latency. Target: 2,522.7 ms → under 100 ms. Independent of whether
the thesis survives AV-001, and worth doing either way.

### 7.1 What "offline" actually means here, and what is missing

Asked directly whether AV-001 and AV-002 need a model or an embedder. The honest
answer is *some of each*, and it depends on the feature, not on the study.

**Committed and sufficient on its own:**

- **Reader outcome labels.** `judged_r1.json` per arm. These are self-sufficient:
  the HH-003 contrast reproduces from them exactly at 46 gains / 32 losses /
  net +14.
- **The full rendered context** per item, in `contexts.json`.
- **Channel membership.** `_protected_aspect` renders
  `[recency][initial semantic][aspect][returned slack]` in that order, and every
  segment size is in `detail`, so positional slicing recovers which delivered
  episodes were ASPECT admissions. This is exactly how `hh005_contexts.py`
  reconstructed the semantic half.
- **Greedy admission order** within the aspect segment, since packing preserves
  order. Skipped-on-overflow candidates are invisible, which is a real limit.
- **spaCy facet extraction.** Deterministic local NLP, not a call in this
  programme's accounting — TC-011 ran `REGISTERED-OFFLINE` while using it.

**Not in the repository:**

- **The embedding cache.** `nf004_holdout_embeddings.db` — 2,749 entries,
  1024-dim float32, 13.3 MB — exists only at
  `C:\Users\muzaf\PycharmProjects\...`. `*.db` is gitignored at line 28, and
  only the digest manifest is committed. The LoCoMo corpus is the same story:
  `hh005_contexts.py` reads `C:\Users\muzaf\Downloads\locomo10.json`.
- **The ASPECT `marginal` trace**, as noted above.

**So the split is:**

| | Needs | Status |
|---|---|---|
| AV-001, text / structural / positional / facet features | repo only | genuinely zero-call |
| AV-001, vector redundancy features | embedding cache | cache *read*, or 2,749 re-embeds |
| AV-002, membership and admission order | repo only | genuinely zero-call |
| AV-002, marginal gains, minimum aspect share | re-run `_protected_aspect` → CC80 → vectors | not zero-call |
| AV-003 | byte-identical replay of HH-003 allocation | needs the cache |
| AV-004 | paid pilot | model calls by design |

Supplying the `.db` converts most of this from "embedder calls" to "cache reads
with zero misses," which is the accounting every DA study used. Without it, the
vector-dependent half of AV-001 and all of AV-002's counterfactual half are
blocked, and the text-only half still runs.

### 7.2 Why this is not the DA arc again

The obvious objection is that I have just criticized 101 zero-call studies and
proposed starting with two more. The distinction is in the **label**, not the
call count.

DA's studies were offline *and* their label was a surrogate: "is the exact
evidence present in the pack," which no reader ever confirmed. AV-001 and AV-002
are offline analyses whose label **is the reader outcome** — `judge_label` from a
paid run that already happened. The reader has been spent; this is reading what
it produced. Offline analysis of reader labels is not the same operation as
offline optimization of a reader-free proxy.

That said, one real risk survives, and it should be named rather than argued
away. AV-001 is post-hoc on a fixed corpus, so whatever it finds is a
**hypothesis, not a mechanism**. If its model is never confirmed prospectively, I
will have built a nicer surrogate rather than escaped the trap. AV-004 is
therefore not optional — it is the study that makes AV-001 mean anything.

Applying to this arc the trip condition the post-mortem recommends for others:

> **No more than two consecutive zero-call AV studies before a live check.**
> AV-001 and AV-002 spend that allowance. AV-004 is then mandatory before any
> further offline work, and a null AV-001 stops the arc rather than licensing
> AV-003 and a third analysis.

**AV-004 — Additive derivative headroom, live.** *Paid; ~100-item pilot first.*
The contrast the DA arc never ran: ASPECT-v1 fully retained, DA-098's derivative
members admitted only into reserved headroom, `<episode>` renderer throughout,
compared against unmodified ASPECT-v1 on judged accuracy. Prior:
DA-005/006/007 found reserved headroom lossy — but against pair-ranking, on
availability, under all three substitutions named in §3. Gated on AV-001
producing a usable harm model; without one, this is DA's mistake again with a
different allocator.

---

## 8. What would falsify this

Stated now, before any result:

- **AV-001 returns AUC ≈ .55 on harm with a null permutation test.** Then reader
  outcomes are as unpredictable as availability outcomes, the measurement
  premise fails, and Aspect v3 should stop rather than proceed to AV-004. This
  is the most likely single failure and it is cheap to reach.
- **AV-002 finds the +14 spread evenly across all 37 admissions.** Then C2 is
  wrong, there is no small useful subset, and the 92× cost is intrinsic rather
  than incidental.
- **ASPECT-v1's +14 fails to replicate.** It sits at `p=.14` on one run. A
  replication that lands near zero would mean the incumbent is noise, and the
  correct action is to ship `aspect_enabled=False` — which is already the default
  — and close the aspect line entirely rather than build a v3.

That last one deserves to be said plainly: **the honest possibility is that there
should be no Aspect v3.** The default path is 92× faster and within noise of the
incumbent on the only live comparison that exists. Any v3 has to clear
ASPECT-v1, and ASPECT-v1 has not yet cleared having no aspect layer at all. I
would rather establish that in AV-001 and AV-002 for zero dollars than discover
it after another hundred studies.

---

## 9. Non-goals

- No compact-wire or pointer-interpretation work. DA-020 through DA-096 closed
  the encoding question, and HH-004 showed encoding was never the bottleneck.
- No renderer changes. LV-009 retained pairwise; v3 inherits that.
- No new corpus. LoCoMo is spent and every AV study above is either analysis of
  sealed artifacts or a small paid pilot on the existing 842-item overlap.
- No sweeps of `aspect_share`, CC80 weights, or BM25 parameters. Those are frozen
  in `EpisodicConfig` with explicit guards, and nothing here proposes unfreezing
  them.
