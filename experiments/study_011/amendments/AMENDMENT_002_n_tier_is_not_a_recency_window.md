# Study 011 — Amendment 002

## The N Tier Is Not a Recency Window, and Arm A Is Not Study 009 Arm S

**Type:** Standalone amendment. **The locked pre-registration is not edited.**
**Amends:** `experiments/study_011/pre_registration.md`, SHA-256 `350d9763691c93b2e057cc0c10bdd7f19d8a78c7e169f9e40ef0571d69e5e7f4`
**Repository:** `contextDecayWindow` · `experiments/study_011/amendments/`
**Status:** Record of fact. **Authorizes no run and moves no bar.**
**Raised:** August 8, 2026, after results, from post-unseal mechanism analysis.
**Evidence:** `experiments/study_011/analysis/n_tier_characterization.json`

---

## 1. What this amendment does

It corrects a name. The pre-registration describes the N tier as a
**recency window** and Arm A as **"STM only"**, replicating Study 009 Arm S. The
mechanism does not implement a recency window and Arm A does not replicate Arm S.

**What it does not do, stated first because of what Amendment 001 had to state:**

- It does not change B1's outcome. **B1 fired. Arm C 7.0 against Arm D 8.0. The
  packing correction is not adopted.**
- It does not change any score, any gate result, or any committed number.
- It authorizes no run. Nothing here needs a phase.
- It is not a rescue. Correcting the name of the tier Arm C shares with Arm D
  cannot move a contrast in which both arms have it.

What it changes is what the registered contrasts *mean*, which is a separate thing
from what they measured, and it is recorded here because the pre-registration's own
rule forbids reconciling a fact with a framing silently.

### 1.1 Legitimacy test, applied on the same four criteria as Amendment 001

| Criterion | Assessment |
|---|---|
| Corrects a measurement | **Yes.** It corrects what the measured quantity is called, which is the measurement-unit case §5 of `AGENTS.md` names |
| Fixes a registered contradiction | **Yes.** §3 names a mechanism the code does not implement |
| Makes passing harder or neutral | **Neutral.** No criterion, bar, or score is touched; the failing verdict stands |
| Raised before results where possible | **No.** Raised after, from mechanism analysis, which is the stage at which it becomes visible. The pre-test in §4 could have caught it and did not — see §5 |

---

## 2. The trigger

Study 011's report attributes Arm C's loss to fill order. A follow-up question
asked when the LTM tier is called at all, and whether the STM tier prevents signal
from reaching it. Answering it required reading the ordering key rather than the
block name, and the key does not do what the block name says.

## 3. What the tier actually selects

The ordering key is `logical_n_key` in `src/memory/context_matched_stm.py:260`.
It sorts **every episode in the store** by

```
(has ever been delivered, turn last delivered, source turn, id)   ascending
```

Never-delivered episodes sort first. Among those already delivered, the one
delivered longest ago sorts first. Source turn enters only as a third-level
tiebreak, and it enters **ascending** — oldest first, the opposite of recency.

This is a least-recently-delivered coverage rotation over the whole store. The
block it renders into is named `<recent_context>`, and that name is the only place
recency appears.

### 3.1 Measured, not asserted

`src/analysis/study_011_n_tier.py` replays the ranking by importing `logical_n_key`
from the deployed engine and applying it to store state reconstructed from
`retrieval_events`, then compares the result to the candidate ids the live runs
logged. **The replay reproduces the live ranking on 120 of 120 testable turns in
every arm that has an N tier** (A, C, D; turn 1 has an empty store). The analysis
withholds every downstream number when the replay fails, and a test proves it does.

Against a genuine recency window of the same size:

| | Arm A | Arm C | Arm D |
|---|---:|---:|---:|
| Mean overlap of delivered set with a true recency window | 0.29 | 0.29 | 0.29 |
| Share of deliveries older than the cap of 32 turns | 36.3% | 35.7% | 36.1% |
| Episodes of the reachable store ever delivered | 120/120 | 120/120 | 120/120 |
| Deliveries per episode, min–max | 1–44 | 1–44 | 1–44 |

A window of 32 cannot deliver anything older than 32 turns; over a third of every
arm's deliveries are. A window never reaches the head of the store; this reaches
all of it.

At turn 120, Arm A delivered source turns **18, 37, 49, 65, 66, 88, 103, 119**. A
recency window would have delivered 112 through 119.

### 3.2 Why the label survived eleven studies

Two measurements explain it, and neither is a coincidence.

**The label is true early.** The candidate list equals a recency window on exactly
**32 turns** — exactly the turns on which the store still fits inside the cap of 32.
After turn 33 it never equals one again. Anyone who checked the tier during a short
run, an ablation, or a 35-turn gate saw a recency window, because at that length it
is one.

**The first line is always recent.** The tier delivered the immediately preceding
turn at **9 of 9 probes**. That episode is the one thing in the store that has never
been delivered, so the novelty term at the head of the key admits it every time.
The block opens on the previous turn and then rotates through the archive, which is
what a recency window looks like if you read the top of it.

---

## 4. What this changes about the arms

| Registered as | Actually |
|---|---|
| **Arm A — STM only**, "recency window, N = 32" | A least-recently-delivered coverage rotation over the entire store, with similarity disabled |
| **Arm D — the deployed configuration**, "recency-first packing" | Correct as to deployment and packing order; the tier filled first is the rotation, not a window |
| **C vs A** — "the marginal contribution of the similarity tier" | The marginal contribution of similarity **over a whole-store rotation that already reaches everything**, which is a far harder baseline than a window |
| **A vs B** — "which tier carries more alone" | Coverage rotation against similarity, not recency against similarity |
| **C vs D** | **Unaffected.** Both arms carry the identical tier; the contrast is fill order, as reported |

**Arm B's registered hazard stands.** With N disabled the model genuinely does not
see the preceding turn, because the rotation was the only thing delivering it.

### 4.1 Arm A does not replicate Study 009 Arm S

The pre-registration's §3 says Arm A "Replicates Study 009 Arm S under corrected
accounting." It does not, and the difference is mechanism rather than accounting.

`src/study/study_009_runner.py:140` constructs `StmRetrievalEngine`.
`src/study/retrieval_bakeoff_tier6_runner.py:70` constructs
`ContextMatchedStmRetrievalEngine`. These rank differently. Probed on one store
built so that three candidate readings give three different answers:

| Engine | Cap | Orders by |
|---|---:|---|
| `StmRetrievalEngine._n_retrieve` — Study 009 | 10 | **most** recently delivered first |
| `logical_n_key` — Study 011 | 32 | **least** recently delivered first |

The older engine scores `exp(-0.1 × hours since last delivery)` and sorts
descending, so a fresh delivery scores near 1 and a stale one near 0: it
re-delivers what it just delivered. The newer key sorts the same quantity
ascending and does the opposite. Both put never-delivered material first; below
that they are inverses.

Neither is a recency window. **They are also not each other.** Any reading of
Study 011 Arm A as a replication of Study 009 Arm S is withdrawn. §6 adds a third
ordering, in the extracted library, which is the only genuine window of the three.

---

## 5. Surrogate audit

The failure here is the one `AGENTS.md` §3 names: a check that passes while the
property it certifies is false.

| Check | Certified | Why it passed anyway |
|---|---|---|
| The pre-test in §4, that "both mechanisms demonstrably deliver" | that each tier works | It counted deliveries. A rotation delivers, so the count passed; what was delivered was never characterized |
| Ablation at 35 turns | the mechanism at scale | For 32 of those turns the tier **is** a window. The ablation could not see the difference |
| Block name `<recent_context>` | the tier's semantics | A rendering label, carried into the pre-registration as if it were a specification |
| Delivery counts throughout the arc | retrieval behaviour | Counts are unit-blind, which is the trap already recorded as "rescale caps when granularity changes" |

**Accepted residual.** This amendment establishes what the tier selects on the
Study 011 corpus at cap 32 and budget 32,000. It does not establish that a
correctly-implemented recency window would score better or worse. **Nothing here
licenses that claim**, and per LV-001 a mechanism that changes delivery has not
improved anything until it changes answers.

---

## 6. Scope beyond Study 011

The mislabel is not confined to this study, and it is not one mechanism
mislabelled twice. **Three different mechanisms in this repository are all called
the recency window, and only one of them is one.**

| Path | Cap | Orders by | Where it ran |
|---|---:|---|---|
| `StmRetrievalEngine._n_retrieve` | 10 | most recently delivered first | Study 009 and earlier live runs |
| `logical_n_key` | 32 | least recently delivered first | Corrected Tier 6, Study 010, Study 011 live runs |
| `episodic._context._recency_window` | 32 | **the last N in conversation order** | The extracted library; EC-002, CC-003, CC-005 |

The three orderings are probed on one store built so each reading gives a
different answer, and the probe is committed with the artifact.

**The only correct recency window in the program is in the component that no
scored live study ran.** `src/memory/context_matched_stm.py` imports the library's
packer and renderer and nothing else; the library's context composition is a
separate path. The paper's description of the surviving component as "an
append-only verbatim store, a recency window, similarity retrieval, and a
coverage objective" is therefore **accurate about the library**. What does not
hold is the implied continuity: the measured arc did not run that recency path.

Two consequences follow, and both are recorded rather than resolved here.

**Study 009's 3.0-point S-vs-L contrast** — the arc's "clean architectural
number" — was measured with most-recently-delivered ordering at cap 10. This
amendment does not re-read the result. It records that the mechanism is not the
one the report names, and that establishing what the contrast measured is its own
work.

**EC-002 and IC-001 are not the same contrast on two corpora.** EC-002 imports
`_recency_window` from the library, so both its arms pack K against a genuine
window; IC-001 replays frozen candidate identities from a deployed run, so both
of its arms pack K against the rotation. Each comparison is internally valid —
within each, the tier is held fixed and only the order changes — and EC-002's
152-gains-zero-losses stands as a statement about the library. Reading the two as
replications of one another does not hold, because the tier K is being packed
against differs between them.

`PAPER_001.md` and the mechanism ledger are corrected in this branch;
`ERRATA.md` carries the entry.

---

## 7. Deliverables

- [x] Characterization module with replay identity as a precondition, and tests
- [x] `n_tier_characterization.json` committed over all four arms
- [x] Engine ordering probe committed; Arm A / Arm S non-equivalence established
- [x] This amendment
- [x] Study 011 report §3.2
- [x] `ERRATA.md` entry for the architecture description
- [x] `PAPER_001.md` and the mechanism ledger corrected
- [x] `README.md`, `AGENTS.md` digest, memory

---

*Raised August 8, 2026, from post-unseal mechanism analysis of Study 011. B1's
verdict is unchanged: A 8.0, B 7.5, C 7.0, D 8.0; the packing correction is not
adopted. Amendment 001 remains DRAFT and unauthorized, and nothing here depends
on it.*
