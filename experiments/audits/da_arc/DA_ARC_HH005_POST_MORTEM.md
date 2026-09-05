# Post-Mortem - the DA arc and its HH-004/HH-005 live validation

**Status:** `POST-MORTEM - no result moves`
**Date:** September 2, 2026
**Scope:** DA-001 through DA-101, HH-004, HH-005 (PR #91)
**Standing:** process audit. This document re-reads committed artifacts. It runs
nothing, re-scores nothing, and changes no registered disposition.

---

## 1. What happened

Between August 29 and September 1, 2026, the DA arc ran 101 studies to build a
linked derivative-context allocator. On September 1 the frozen product of that
arc was put in front of a reader for the first time, twice:

| Arm | n=842 | Score |
|---|---:|---:|
| `A_RAG` | 383 | 45.49% |
| DA-098 decoded, alone (HH-004) | 606 | 71.97% |
| `A_FULL` full context | 622 | 73.87% |
| Semantic + DA-v2, 16k (HH-005) | 649 | 77.08% |
| **`A_EPISODIC` (no aspect layer at all)** | **655** | **77.79%** |
| Semantic + DA-v2, 32k (HH-005) | 654 | 77.67% |
| **`A_EPISODIC_ASPECT` = ASPECT-v1 (incumbent)** | **670** | **79.57%** |

Against ASPECT-v1, DA-v2 at 32k traded 32 gains for 48 losses: net **-16**
(two-sided p=`.0929`). At 16k it traded 26 for 47: net **-21** (p=`.0186`).
Doubling the retrieval allowance moved 49 answers and bought net **+5**
(p=`.568`).

The blunt reading: the arc's output lands one item below the plain episodic
baseline that has **no aspect layer of any kind**. After 101 studies, the
derivative aspect channel is worth approximately nothing over not having one,
and is measurably worse than the ASPECT-v1 it was built to replace.

The disappointment is warranted. What follows is why it was structurally
predictable, and what the arc nevertheless bought.

---

## 2. Root cause 1 - the arc never once tested its own hypothesis

Every DA study document carries a planned-call declaration. Across all 101
studies, without exception:

```
Planned embedding calls: 0
Planned model calls:     0
```

101 of 101. Zero reader contact for the entire arc. The first time a language
model saw a DA payload was HH-004, after the architecture was frozen.

The arc's success measure was **exact evidence availability** - whether the
correct source member is present in the packed context. That is a mechanical,
offline property. The thing the programme actually cares about is whether the
reader answers correctly. The arc optimized the first for four days and
discovered on day four that it does not carry the second.

HH-004's recorded model cost was **$1.7434**. A reader check of this class was
available for under two dollars at any point in the arc.

---

## 3. Root cause 2 - the surrogate could not express harm

DA-098's headline is what licensed promotion to a paid benchmark:

```
ARCH_32 vs PAIR_32:  44 gains,  0 losses,  p = 1.14e-13
ARCH_32 vs ARCH_16:  82 gains,  0 losses,  p = 4.14e-25
```

Zero losses, twice, at overwhelming significance. That reads as a strictly
dominant architecture. It is not. It is the shape of the measure.

`ARCH_32` was constructed as the **immutable `ARCH_16` member sequence plus
admissions under a doubled budget**. DA-098's own protocol states it: "No
existing member may be removed, replaced, reordered or recharged." Evidence
availability is monotone in what you pack - adding members can only add
evidence. A zero-loss result was guaranteed by construction before the study
ran, and carries no information about quality.

Reader accuracy is **not** monotone in what you pack. Added members are
distractors as readily as evidence. HH-004 says this outright: DA-098 reached
the mechanical one-hop evidence ceiling and *still* lost 64 items to
episodic-aspect, and lost to plain full-context dumping. Availability was
necessary. It was never close to sufficient.

Every "N gains / 0 losses" result in this arc should be read as a capacity
measurement, not a quality one.

---

## 4. Root cause 3 - the incumbent was never a control

This is the finding I would act on first.

**Zero of the 101 DA study documents mention ASPECT at all.** Not ASPECT-v1,
not the deployed configuration, not HH-003. The arc's controls were, uniformly,
NF-004 pair-ranking: `DIRECT`, `PAIR_16`, `PAIR_32`.

So the arc spent 101 studies establishing that its allocator beats pair-ranking,
under an *expanded* budget, on *availability*. HH-005 then asked the only
question that could authorize adoption: does it beat **ASPECT-v1**, as a
**substitution at fixed budget**, on **answer accuracy**?

Different comparator, different operation, different measure. Three
substitutions between what was optimized and what was decided:

| | Arc optimized | HH-005 decided |
|---|---|---|
| Comparator | pair-ranking | ASPECT-v1 (incumbent) |
| Operation | addition under expanded budget | substitution at fixed budget |
| Measure | exact evidence availability | judged answer correctness |

Addition under a growing budget cannot lose. Substitution at a fixed budget
must displace something, and displacement is exactly where the 48 losses came
from. The arc never ran a single contrast in the shape of the decision it was
building toward.

---

## 5. Root cause 4 - the risk was logged 27 times and gated zero times

The arc was not ignorant of any of this. It wrote the warning down, repeatedly,
in its own words:

> "cosine is not utility, and availability is not reader use."
> "evidence availability is not answer use, and median rank can hide..."
> "**PF9 Surrogate audit:** availability is not answer use..."
> "**PF10 Live boundary:** no reader, adoption, latency, fresh-validation..."

- **92 of 101** studies carry reader-caveat language.
- **27 of 101** state explicitly that availability is not reader use.
- **24 of 101** formalize it as standing preflight items PF9 and PF10.
- **0 of 101** ever acted on it.

The arc had a working stop mechanism and used it five times: DA-003 and DA-006
on `STOPPED_AT_CAUSAL_ACCOUNTING`, DA-005 and DA-019 on `STOPPED_AT_PF4`, DA-027
on `STOPPED_AT_BLIND_NO_EXPANSION`. Those all fired on *mechanical* blockers: a
codec that could not admit, a causal credit assignment that was wrong. Every one
of them stopped the study it was in.

Nothing was ever wired to the surrogate risk. PF9 was a disclaimer printed at
the top of the page, not a gate with a trip condition. The programme's own
integrity apparatus was pointed at the wrong failure mode: it rigorously
guaranteed that the arc measured what it said it measured, and had nothing to
say about whether that was worth measuring 101 times in a row.

This is the difference between a caveat and a control. A caveat protects the
claim. A control protects the direction.

---

## 6. Secondary findings

**HH-004 answered a question nobody asked.** It was intended as the aspect-v2
test and ran as a DA-only ablation with the semantic channel deleted entirely.
It is retained as a valid ablation - and it is genuinely informative, since
restoring the semantic half recovered 5.7 points - but a paid benchmark run and
a full pre-registration cycle went to a composition that was not the hypothesis.
The corrective now exists as a test assertion in `tests/test_hh005.py`:

```python
assert not detail["aspect_v1_included"]
```

That check is the right one. It was written after the error, not before it.

**The composition error has no ERRATA entry.** It is documented in exactly one
sentence, in `HH_005_FINDINGS.md` §Reading, plus the PR body. `ERRATA.md` is
untouched by PR #91. This repository maintains a detailed errata log for
precisely this class of event - a registered study that did not do what it was
registered to do. HH-004 currently stands in the tree with status
`COMPLETE - CHARACTERIZED` and no marker anywhere in its own directory that it
missed its intent. A reader arriving at `experiments/comparisons/hh_004/` in six
months has no way to learn this.

**The arc has no per-study audit trail.** PR #91 is 865 files and 435,272
insertions in **one commit**. For comparison, LV-009 - a single study - landed
across 14. The stated reason is a rewritten `main` history, which is a real
constraint, but the effect is that 101 studies, two paid benchmarks, and an
amendment lock now share one commit boundary. Nothing can be bisected,
attributed, or reverted independently.

**The arc kept building after the answer was in.** DA-099, DA-100 and DA-101 are
all dated September 1 - the same day as HH-004 and HH-005. DA-101 drove codec
latency to 59.9 ms p50 chasing a 25 ms production tier, and closes with "Reader
use remains untested." That work was optimizing the deployment characteristics
of an allocator that the same day's benchmark said not to deploy.

---

## 7. What the arc actually bought

The result is disappointing. The arc is not worthless, and a post-mortem that
implied otherwise would be its own kind of error.

- **The availability ceiling is solved.** 1,068 of 1,098 at 32k, with all 30
  remaining misses attributed to a single cause (`FIT_OVERFLOW`). That is a
  closed problem with a named residual.
- **The exact codec works and is fast.** DA-101 preserves the exact 1,098-row
  allocation at 59.9/76.9/85.9 ms (p50/p95/max), passing the 200 ms tier.
  Byte-identical replay holds across the arc. This is reusable engineering that
  survives the negative result intact.
- **The derivative channel finds real evidence.** The 32 rescues in HH-005 are
  not noise - they are items ASPECT-v1 misses and DA-v2 gets. The mechanism is
  live. The problem is that it substitutes rather than supplements.
- **The negative result is trustworthy, and that is not free.** Answers sealed
  before judging, blind surfaces, zero malformed judgements, zero failed items,
  byte-identical replay, four watchdog restarts recovered by stable key. Because
  the integrity discipline held, "-16, p=.0929" is a fact about the architecture
  rather than a fact about the harness. Most disappointing results are
  ambiguous. This one is clean, which is why it can be acted on immediately.

The arc's failure was one of direction, not of execution. Execution was
excellent throughout.

---

## 8. What HH-005 licenses next

HH-005 names the successor condition precisely: *"preserve the frozen semantic
half and directly target the 32 DA rescues without incurring the 48 v1 losses."*

The structural reading of §4 sharpens that. The losses come from
**substitution** - DA-v2 replaced ASPECT-v1's half, and displaced 48 items that
ASPECT-v1 was getting right. The arc never tested the additive shape:
ASPECT-v1 retained, with derivative context admitted only into reserved
headroom.

That contrast has a prior. DA-005, DA-006 and DA-007 all studied reserved
headroom; DA-007 closed the question as `NO_PROTECTED_CAPACITY_SIGNAL` with a
best case of net -43. But those studies reserved headroom against *pair-ranking*
on *availability*, under the same three substitutions identified in §4. Whether reserved headroom is lossy
against ASPECT-v1 on reader accuracy is an open and different question, and it
is the cheapest informative next run available.

Before any successor arc:

1. **Register the decision contrast on day one.** The first study of an arc
   should run the same comparator, the same operation, and as close to the same
   measure as the arc's terminal decision will use. If the terminal decision is
   substitution against ASPECT-v1 on judged accuracy, study 001 compares against
   ASPECT-v1 and substitutes.
2. **Put a reader in the loop early and cheaply.** Not at full population - a
   100-item pilot at HH-004's per-item rate is well under a dollar. Budget was
   never the constraint; the constraint was that no stage of the arc was
   defined to require it.
3. **Give PF9 a trip condition.** "Availability is not reader use" should not be
   printable more than N times without a reader run. The arc already knows how
   to stop itself - `STOPPED_AT_*` works. Wire it to this.
4. **Distrust zero-loss results in monotone measures.** Any nested or
   append-only design evaluated on a monotone metric should report the
   structural floor alongside the observed result, so "0 losses" is read as
   "0 losses, as guaranteed by construction."
5. **File the HH-004 erratum**, and add a status marker in
   `experiments/comparisons/hh_004/` recording that the run is a valid ablation
   but not the registered intent.

---

## 9. Disposition

No registered result changes. `NO_ASPECT_V2_IMPROVEMENT` stands, ASPECT-v1 is
retained, and no adoption is authorized by any artifact reviewed here.

The four days were not spent proving that linked derivative context is useless.
They were spent proving that **availability was the wrong objective**, and
buying a fast exact codec on the way. That is a real finding, arrived at
expensively. The recommendations above are about arriving at the next one for
under two dollars and one afternoon.
