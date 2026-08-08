# Study 009 — Amendment 002

## Arm S Was Not a Recency Baseline. It Was a Locked Prefix.

**Type:** Standalone amendment. **The locked pre-registration is not edited.**
**Amends:** `experiments/study_009/pre_registration.md`, SHA-256 (LF-normalized)
`533ec1c1e51497d1c77b2ab187f72f507f2c2f6e92a6b67b2b1021aeec7483bb`
**Repository:** `contextDecayWindow` · `experiments/study_009/amendments/`
**Status:** Record of fact. **Authorizes no run and moves no bar.**
**Raised:** August 8, 2026, after results, from post-unseal mechanism analysis.
**Evidence:** `experiments/study_009/analysis/n_tier_characterization.json`
**Follows:** `experiments/study_011/amendments/AMENDMENT_002_n_tier_is_not_a_recency_window.md`

---

## 1. What this amendment does

Study 011's Amendment 002 recorded the carried engine's ordering key as
**most recently delivered first**. That is what the key says. It does not say
what the key *does* over a long run, and this amendment records that, because
the answer is not a shade of the same thing.

`StmRetrievalEngine._n_retrieve` did not deliver a recency window, a rotation,
or anything that moved. From turn 11 onward it delivered **the same nine
episodes — source turns 1 through 9 — plus whichever episode had not been
delivered before**, which is always turn *t*−1. It held that for 111
consecutive turns.

**What this does not do, stated first:**

- It does not change Arm S's score, Arm L's score, or the 3.0-point gap.
- It does not confound the S−L contrast. Arm L carries the **identical** tier,
  turn for turn; a test asserts it. S−L still isolates the LTM tier.
- It authorizes no run and moves no bar.
- It does not establish what a correctly-implemented recency window would have
  scored. No arm ever ran one.

What changes is what the baseline **is**. Study 009 exists to ask whether LTM
improves recall over the pure STM architecture. It asked that against an
architecture that was never a recency window.

### 1.1 Legitimacy test, on the same four criteria as Study 011's amendments

| Criterion | Assessment |
|---|---|
| Corrects a measurement | **Yes.** It corrects what the baseline arm is, which is the measurement-unit case §5 of `AGENTS.md` names |
| Fixes a registered contradiction | **Yes.** the pre-registration's **Method** section builds Arm S as "its own minimal composition, not as v9-with-features-off"; the composition it built holds a fixed prefix |
| Makes passing harder or neutral | **Neutral.** No criterion, bar, gate or score is touched |
| Raised before results where possible | **No.** Raised after, from mechanism analysis. §5 below is the audit of why no earlier check caught it |

---

## 2. The mechanism, stated as a closed loop

Three lines of the carried engine, and the third is the one that matters.

1. `_compute_decay` returns **1.0** when `last_retrieved_at is None`. 1.0 is the
   supremum of `exp(-0.1 · hours)`. Never-delivered material therefore sorts
   **first** — the same novelty preference `logical_n_key` has.
2. Everything already delivered sorts by decay **descending**, so the freshest
   delivery outranks the stalest. This is the inverse of `logical_n_key`.
3. `retrieve()` then touches every episode it delivered, **in one call, with one
   timestamp**.

Step 3 closes the loop against step 2. What is in the block is the freshest
thing in the store, so it is selected again, so it is refreshed again. The batch
write leaves its whole set tied on the real key, and the tie is broken by the
order `get_all_episodes_with_embeddings` returns — `turn_number ASC`. So the
block settles on the *oldest* episodes in the store and cannot leave them.

At turn 10 the store holds nine episodes, all never-delivered, all delivered.
At turn 11 they are the nine freshest and the newcomer takes the tenth slot. At
turn 12 the newcomer of turn 11 is tied with them and loses the tie to source
turn, and is never seen again. That is the last turn on which the composition
of the block changes.

## 3. Measured, by replay against the committed logs

The replay imports the engine's cap, reconstructs the ordering from delivery
history, and is checked against what each run logged. **The wall clock drops
out**: `exp(-0.1 · hours_since)` is monotone in `last_retrieved_at`, so ranking
by score is ranking by last touch, with never-touched pinned above. Replay state
advances from the **logged** delivery sets, not the replay's own output, so each
turn is an independent test.

| | Arm S (full) | Arm S (ablation) | Arm L |
|---|---:|---:|---:|
| Turns replayed exactly | 120/120 | 34/34 | 120/120 |
| Block stops changing at turn | 11 | 11 | 11 |
| Source turns held | 1–9 | 1–9 | 1–9 |
| Turns it holds them | 111 | 25 | 111 |
| Mean overlap with a true window of the same size | 0.205 | 0.471 | 0.205 |
| Deliveries older than the cap of 10 | 82.6% | 61.0% | 82.6% |
| Mean age of a delivered episode | 53 turns | 14.4 turns | 53 turns |
| Episodes delivered exactly once | 111 of 120 | 25 of 34 | 111 of 120 |

At every turn from 112 to 121 — the ten turns on which the thirteen rubric
questions are asked — Arm S's recent block held source turns **1, 2, 3, 4, 5, 6,
7, 8, 9** and *t*−1. A last-ten window at turn 120 would have held 110–119. It
held 1–9 and 119.

Episode one was delivered on **all 120 turns**. Episodes 10 through 118 were
delivered **once each**, on the turn after they formed, and never again.

## 4. What the 3.0 measures, and what it does not

Arm L's N tier is identical to Arm S's on every number above, and
`test_the_arms_differ_in_the_ltm_tier_and_not_in_the_n_tier` asserts the two
arms' blocks match turn for turn across all 120 turns. **The contrast is clean.**
Adding the LTM tier to this composition is worth 3.0 points on Q1–Q13, and that
number is not disturbed here.

What is disturbed is the sentence the number is usually carried in. "LTM beats
pure STM by 3.0" reads as *a similarity-and-LTM architecture beats a recency
baseline*. The baseline was one slot of genuine recency out of ten, over a
frozen prefix of the conversation's first nine turns. A reader entitled to the
first reading is not entitled to the second.

Two specific consequences:

- **The Study 004 comparison inherits this.** The pre-registration's **Summary** cites
  Study 004, "where STM-only retrieval beat the LTM architecture 11.0 to 7.0",
  as the only clean STM-vs-LTM comparison ever run. `study_004_full_002` replays
  exactly and locks. Both sides of that 11.0–7.0 carried the locked prefix too.
- **The ablation could not have caught it.** At 35 turns the block still locks at
  turn 11 and holds for 25 turns. Study 011's Amendment 002 observed that 35
  turns is short enough to hide the `logical_n_key` mislabel because its cap is
  32. That does not transfer: this engine's cap is 10, and the ablation shows the
  lock plainly. Nobody looked.

## 5. Reach across the record, and a surrogate audit

The scan replays every committed run directory carrying a store and an N log,
indiscriminately — rehearsals, ablations and failed launches included and
labelled rather than filtered.

| | Count |
|---|---:|
| Run directories scanned | 40 |
| Whose ranking replays exactly | 17 |
| Of those, locking onto the oldest episodes | 12 |
| Carrying the store signature | 8 |

**Every scored live run from Study 004 through Study 010 replays exactly and
locks.** Study 010's arms held source turns 1–9 across **999 logged turns**, at a
mean overlap with a true window of 0.11.

Studies 001–003 do not replay and nothing is derived for them: their logs record
the rendered block in conversation order rather than the ranking, which is a
different unit. Study 002's full run and both Study 003 full runs carry the
**store signature** — the nine oldest episodes with retrieval counts at the turn
count, everything else near one — which is corroboration and not proof, because
the counter is shared with the other tiers. Study 011's four arms do not replay,
which is correct and is asserted by a test: they ran `logical_n_key`.

**The surrogate audit.** Four checks stood between this and the record, and each
passed while the property it certifies was false:

| Check | Why it passed anyway |
|---|---|
| Arm S structural purity gate | It verified the LTM tier was *absent from the import graph*. It said nothing about what the surviving tier selected |
| `N_values.csv` and the delivery counters | The tier delivered ten episodes every turn. Volume was never the failure |
| The 35-turn ablation | It ran past the lock at turn 11 and recorded the result without anyone reading which turns were in it |
| The block name `<recent_context>` | A name is not a check |

The pre-registration names this class itself, in its **Summary**: *"the program's
recurring surrogate failure class operating at the level of study design: the
control became a surrogate for the baseline."* It identified the pattern one level up
and instantiated it one level down in the same document. The baseline it built
to escape a surrogate control was itself a surrogate for a recency window.

## 6. Consequence: a mechanism for the deployed system's inertness

Study 011 recorded that the deployed LTM tier is inert — Arm D scored identically
to Arm A on all thirteen questions — and IC-001 established the proximate cause:
the deployed fill order starves the K tier, delivering zero K episodes at 8/8
probes. What the record did not have was an account of why **un-starving** it
lowered the score rather than raising it.

`logical_n_key` supplies one, and it is quantifiable from the committed Study 011
artifact. Arm D's similarity tier produced **124 candidates across 121 turns**,
of which **95 (76.6%) were episodes the N tier had already nominated**. Only 29
were additive. The tier the fill order starves was, three-quarters of the time,
proposing material the block already held.

The two accounts compose rather than compete, and the order matters:

1. **Duplication** removes about three-quarters of the tier's potential
   contribution before packing is reached at all — a consequence of N being a
   coverage rotation over the whole store.
2. **Starvation** removes most of what is left: Arm D delivered a K-only episode
   on **1 turn out of 121**, and was starved on 18.

D ≡ A follows from the pair. This does not replace the starvation finding; it
explains why relieving starvation did not pay. And it sharpens the ledger
constraint: a candidate mechanism proposing to add breadth is competing with a
baseline that already touches every episode.

**This is Study 011's rotation, not Study 009's locked prefix.** The two engines
fail in opposite directions — one reaches everything and duplicates, the other
reaches almost nothing and repeats — and no inference from either transfers to
the other.

## 7. Consequence: three names, none of them checked

- `<recent_context>` renders a coverage rotation in the deployed engine and a
  frozen prefix in the carried one.
- `_n_retrieve`, on a class called `StmRetrievalEngine`, implements a
  re-delivery preference that converges on the conversation's opening.
- Arm S, registered as the **pure STM architecture** and built structurally to be
  exactly that, is nine fixed episodes and one recent one.

Each is an assertion about behaviour that no test ever evaluated. This is the
same failure as a gate that never ran in its registered position (IC-001): a
claim that passes review because it is written down, not because it was
executed. A name is a claim about behaviour and carries no evidence.

The operational form: **never infer a tier's semantics from its block name, its
class name, or its delivery counts.** Read the ordering key, then replay it
against the committed log before quoting any number about it.

## 8. What this amendment does not establish

- What a correctly-implemented recency window would score, in either direction.
  No arm in the program ever ran one, and the only genuine implementation
  (`episodic._context._recency_window`) has never been in a scored live study.
- What Studies 001–003 did. They do not replay under this rule and nothing is
  claimed about them beyond a corroborating signature on three runs.
- Any revision to Arm S's or Arm L's scores. Both stand.
- Whether the locked prefix helped or hurt Arm S. Turn 114 asks for the two
  formatting rules established "at the very beginning", and the block held turns
  1–9 permanently; whether that was an advantage is not measured here and is not
  claimed.

## 9. Deliverables

- [x] `src/analysis/study_009_n_tier.py` — replay, scan, negative controls
- [x] `scripts/analyze_study_009_n_tier.py`
- [x] `tests/test_study_009_n_tier.py` — 30 tests
- [x] `experiments/study_009/analysis/n_tier_characterization.json`
- [x] This amendment; the locked pre-registration untouched
- [x] `ERRATA.md`, `paper/PAPER_001.md`, `paper/CLAIM_TO_ARTIFACT.md`
- [x] The mechanism ledger constraint and `AGENTS.md` digest
