# Aspect v3 - Thesis Draft

**Status:** `DRAFT - not a pre-registration; nothing here is registered or authorized`
**Date:** September 2, 2026
**Owner:** taking ownership of the Aspect v3 direction
**Predecessors:** TC-007/008/010/011 (ASPECT-v1 origin) · HH-003 (its only live test) ·
DA-001…101 + HH-004/005 (the v2 attempt) · LV-009 (renderer evidence) ·
NF-004 anatomy and DA-004 (predictor precedents)
**Companion:** `experiments/audits/da_arc/DA_ARC_HH005_POST_MORTEM.md`
**Reader:** local `Qwen3.8-27B-UD-Q4_K_XL` on the LV-009 llama.cpp stack, not the paid API

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

## 6.5 Reader: the local Qwen3.8 stack, not the paid API

Adopted at the programme owner's direction, and it changes the arc's shape rather
than just its cost line.

**The registered stack already exists.** LV-009 runs it: `Qwen3.8-27B-UD-Q4_K_XL.gguf`
(SHA-256 `bee238bb…`) on a direct llama.cpp server (binary SHA-256 `125e0938…`),
raw `/completion`, reasoning disabled, streaming disabled, one request at a time,
no speculative decoding, launched with
`--ctx-size 65536 --parallel 1 --cache-type-k q8_0 --cache-type-v q8_0
--flash-attn on --jinja --metrics --no-context-shift`, fully GPU-resident on the
RTX 5090 with residency gated before and after every phase. The client primitive
is `src/analysis/lv009_runtime.py::complete`, and it already accepts a
temperature argument.

**Measured throughput, from LV-009's own committed rows:**

| Phase | Calls | Median | Mean | Total |
|---|---:|---:|---:|---:|
| Reader (9k–13.4k token prompts) | 7,944 | 2.99 s | 3.46 s | **7.64 h** |
| Judge (3 passes) | 18,480 | 0.52 s | 0.60 s | **3.09 h** |

**Context is safe.** HH-003 prompts run 11,897 tokens median, 12,360 max, against
a 65,536-token window. Ample headroom; no truncation risk.

### Why this reorders the arc

With a free reader, "reuse the sealed comparator to save money" stops being a
constraint — and that constraint is the source of three caveats the HH line has
carried from the start. Both arms can be run fresh, same reader, same day. So the
arc should **open with a live study**, not close with one.

### What it costs, stated plainly

- **External comparability is gone.** Every HH number is `gpt-4o-mini-2024-07-18`,
  and the HH arc exists to sit on the Mem0/LoCoMo published scale. A Qwen3.8
  result cannot be placed on that scale or compared to any published benchmark.
  Local for internal decisions; if an external claim is ever needed, that specific
  run still costs API money. This is a scope trade, not a free lunch.
- **Same-model judging.** Qwen3.8 judged by Qwen3.8, as LV-009's own claim
  boundary flags. Not a regression — HH used gpt-4o-mini for both roles — but not
  an improvement either, and no result may imply otherwise.
- **Sampling noise, and the deviation I am proposing.** LV-009 registered
  temperature `.6` with one sample per arm and states it "cannot estimate
  per-question reader stability." HH ran at **temperature 0**. For AV-001 a noisy
  label is poison: fitting a harm model to sampling noise produces a confident
  model of nothing. **AV studies should therefore run the reader greedy at
  temperature 0**, deviating from LV-009's `.6`. `complete()` already handles it
  (it switches `top_p` to `.9` off the `.6` path). This also matches the HH
  condition, which makes the replication below a cleaner comparison. Registering
  this deviation, with this reason, is a precondition of AV-000.
- **It does not run here.** This container has no GPU and the `.gguf` is not in
  the repository. I write the harness and the pre-registration; the run happens on
  the 5090.

## 7. The plan: live arms only

Revised at the programme owner's direction — *prove the architecture works in
live runs; the availability chase has been fruitless*. That is the right call,
and for a reason worth writing down: **offline analysis is a cost-reduction
technique for expensive evaluation.** It earns its place when each live
measurement costs money and time. When a live measurement costs three hours of
GPU and nothing else, the analysis stops paying for itself — you stop modelling
what the reader would say and ask it.

So AV-001 and AV-002 are struck as gating studies. Every question they were going
to answer analytically becomes a live arm instead, which is both cheaper in
calendar time and strictly better evidence.

### 7.1 The new binding constraint is statistical, not financial

Removing the cost of evaluation does not remove all constraints; it promotes the
next one. If twenty variants are run against ASPECT-v1 on the same 1,540 items
and the best is shipped, the winner is selected on noise. Free evaluation makes
this *easier* to do by accident, not harder.

The corpus already contains its own guard. HH-003 spans ten LoCoMo conversations.
NF-004's holdout — and therefore the entire DA arc — used six of them. The other
four were never selected on by any NF or DA study:

| Split | Conversations | Items | Status |
|---|---|---:|---|
| **Development** | conv-26, 30, 43, 44, 49, 50 | 848 | already selected on by NF-004 and DA; no further loss |
| **Confirmation** | conv-41, 42, 47, 48 | 692 | untouched by every availability study in the programme |

Both sit inside HH-003's 1,540 with sealed baselines, and both get fresh Qwen3.8
labels from AV-000. **Sweep on the 848. Confirm the winner, and only the winner,
on the 692.** Arms are registered before the run; the development sweep carries
Holm correction at familywise `.01`, as LV-009 used.

### 7.2 AV-000 — Does the incumbent work at all?

*Live · local · ~4.5 h · runs first.*

Re-answer and re-judge HH-003's ASPECT-on and ASPECT-off arms across all 1,540
items on the registered Qwen3.8 stack at temperature 0, three-pass majority
judging, blind surface, answers sealed before judging. LV-009's protocol
unchanged except for temperature.

3,080 reader calls at ~3.46 s ≈ **3.0 h**; 9,240 judge calls at ~0.60 s ≈
**1.5 h**.

This is the study that decides whether there is anything to improve on. **If
ASPECT-v1's +14 does not replicate, the honest answer to "does the architecture
work" is no**, and the correct action is to ship `aspect_enabled=False` — already
the default — and close the aspect line rather than sweep variants against a
control that is itself noise. Everything below is conditional on AV-000 landing
positive.

### 7.3 AV-001 — The live arm sweep

*Live · local · ~6.2 h on the development split.*

Five arms, registered before the run, all built on the frozen semantic half and
the unchanged `<episode turn="N">` renderer, all judged against each other on the
848 development items:

| Arm | What it tests |
|---|---|
| `CC80` — aspect off | Control. The shipped default. |
| `ASPECT_050` | The incumbent, unchanged. |
| `ASPECT_025` | Is half the budget more share than the benefit needs? |
| `ASPECT_0125` | The same question, pushed. |
| `ASPECT_050_DA_HEADROOM` | ASPECT-v1 fully retained, DA-098 derivative members admitted only into leftover headroom. **The additive shape the DA arc never tested.** |

Per arm on 848 items: 848 reader ≈ 0.82 h, 2,544 judge ≈ 0.42 h. Five arms ≈
**6.2 h** — one overnight run.

The share arms replace what was going to be an offline attribution study, and
answer it better: instead of inferring from a greedy trace which admissions carry
the +14, the reader is asked directly what happens when they are removed. The
headroom arm is the one contrast in this whole programme that has never been run
in any form — additive rather than substitutive, against the incumbent rather
than pair-ranking, on accuracy rather than availability.

### 7.4 AV-002 — Confirmation

*Live · local · ~2 h.*

The single winning arm from AV-001's sweep plus `CC80`, on the **692 held-out
items** no availability study has ever touched. 1,384 reader calls ≈ 1.3 h,
4,152 judge ≈ 0.7 h.

No arm ships on a development-split result. A winner that does not survive
confirmation was noise, and saying so is the point of holding the split back.

### 7.5 AV-003 — Write-time facet cache

*Engineering; no research risk; independent of everything above.*

Compute facets on append, store beside the episode vector, thread `facet_bundle`
through `build_chat_context`. Gate on byte-identical allocation against HH-003's
sealed contexts (`119a3152…`) across all 1,540 items — this must change nothing
but latency. Target 2,522.7 ms → under 100 ms. Worth doing whichever way AV-000
lands, because it is the difference between an aspect path that can ship and one
that cannot.

### 7.6 Total schedule

| | Hours |
|---|---:|
| AV-000 landscape replication | 4.5 |
| AV-001 five-arm sweep, development split | 6.2 |
| AV-002 confirmation, held-out split | 2.0 |
| **Total live GPU time** | **~12.7** |

Two overnight runs, zero dollars, and every number in it comes from a reader.
For comparison, the DA arc spent four days and 101 studies without producing one.

### 7.7 What is no longer in the plan

- **No offline anatomy study as a gate.** Analysis of AV-000's output is free and
  may still happen, but it decides nothing and blocks nothing.
- **No availability endpoint anywhere.** No AV study reports exact evidence
  availability as a primary, a secondary, or a promotion criterion.
- **No compact-wire or encoding work.** Closed by DA-020…096 and shown irrelevant
  by HH-004.
- **No renderer changes.** LV-009 retained pairwise; v3 inherits that and holds
  the renderer fixed so that a result attributes to selection.

## 8. What would falsify this

Stated now, before any result:

- **No arm in the AV-001 sweep beats `ASPECT_050` after Holm correction.** Then
  the incumbent is already the best available point in this design space, and the
  useful output of v3 is AV-003's latency fix plus a recorded negative.
- **`ASPECT_025` and `ASPECT_0125` match `ASPECT_050`.** Not a falsification —
  a win. It would mean the benefit is carried by a small prefix of admissions and
  the protected share can shrink, taking most of the cost with it.
- **The AV-001 winner does not survive AV-002's held-out confirmation.** Then it
  was noise, the sweep overfit the development split, and nothing ships.
- **ASPECT-v1's +14 fails to replicate under AV-000.** It sits at `p=.14` on one
  run. A replication that lands near zero would mean the incumbent is noise, and
  the correct action is to ship `aspect_enabled=False` — which is already the
  default — and close the aspect line entirely rather than build a v3. Under the
  local reader this test costs about three hours and no money, which is why it
  now runs first rather than last.

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
