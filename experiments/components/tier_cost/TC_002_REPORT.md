# TC-002 Report — the fill-order gain transfers, and it is the small lever

**Pre-registration:** `TC_002_PRE_REGISTRATION.md`, commit
`1ab6f3ed4963119442b820db58b892d92ccbdda5`, SHA-256
`172d26a99059c5d4bd1e70df16356591da16dfbe19190f146ab2d8aaf7dff043`
**Execution commit:** `361ac4764afbd4d0871760b9646dd7da798cb27a`
**Standing:** `REGISTERED-OFFLINE` — bars locked first, zero generative calls,
replayable against a retained embedding cache, on a corpus this programme has
already observed. Capped as characterization; **not** confirmation.
**Disposition (C1, the registered headline):** **D1 — `K_FIRST_WINS`**
**Date:** August 22, 2026
**Artifacts:** `runs/tc002/g0/`, `runs/tc002/run/`, `artifacts/tc002/preflight/`

---

## 1. The verdict

EC-002 gave K-threshold candidates admission priority over the recency window
on 500 LongMemEval stores and moved any-evidence-session recall from **109 to
261 of 470** — 152 gains, zero losses. Roadmap §3 asked whether that
availability gain holds off its original corpus.

**It does.** At EC-002's own budget and endpoint, on four LoCoMo development
conversations EC-002 never saw:

| Contrast | | Any evidence, 871 questions | gains / losses | net | *p* | Disposition |
|---|---|---:|---:|---:|---:|---|
| **C1** | `A_K_FIRST` vs `A_N_FIRST` | **732** vs **687** | 80 / 35 | **+45** | 1.64 × 10⁻⁵ | **D1 `K_FIRST_WINS`** |
| **C2** | `A_K_FIRST` vs `A_FLAT` | 732 vs **842** | 8 / 118 | **−110** | 1.58 × 10⁻²⁶ | **D3 `FLAT_WINS`** |
| **C3** | `A_DUAL` vs `A_K_FIRST` | **740** vs 732 | 9 / 1 | **+8** | 1.07 × 10⁻² | **D2 `DUAL_WINS_CARRIES_SIGNAL`** |
| **C4** | `A_DUAL_RANKED` vs `A_K_FIRST` | **843** vs 732 | 118 / 7 | **+111** | 1.99 × 10⁻²⁷ | **D1 `RANKED_WINS`** |

32,000 characters, band **B = 7**, α = 0.0025 (Bonferroni over four).

**The other three contrasts say what the transfer is worth.** Reordering the
fill recovers 45 questions and leaves the shipped stack's reordered form 110
behind a flat cosine ranking. Offering the K tier its own members best-first is
worth **111** — two and a half times as much — and lands within one question of
the flat arm.

```
A_N_FIRST      687
  +45  admission order between the recency tier and K   (C1, D1)
A_K_FIRST      732
  +111 the order the K tier offers its own members      (C4, D1)
A_DUAL_RANKED  843        A_FLAT 842
```

## 2. The two repairs fix disjoint questions

This is the part that does not follow from the totals.

**C2's 118 losses and C4's 118 gains are the identical 118 questions** — a
complete overlap, question id for question id. C2's 8 gains contain 7 of C4's 8
losses. So the questions where the reordered stack still trails the flat arm
are exactly the questions that ranking the K tier rescues.

**C1's 80 gains overlap none of them.** Zero of 80.

Reordering the fill and re-ranking the tier are not two attempts at the same
repair. They address separate populations, and the arm that does both arrives
where the flat arm already was.

## 3. What each contrast's discordant pairs were

Every cut below was registered in §4 before the split was known.

| | n | Worst-ranked evidence, flat cosine rank | Which tier carried it |
|---|---:|---|---|
| **C1 gains** | 80 | p50 **3**, p25 1, p75 17, max 160 | K, on 80 of 80 |
| **C1 losses** | 35 | p50 **3**, p25 1, p75 18, max 185 | **recency, on 35 of 35** |
| **C3 gains** | 9 | p50 **85**, p25 76, max 195 | **coverage, on 9 of 9** |
| **C3 losses** | 1 | 170 | recency |
| **C4 gains** | 118 | p50 5, p25 1, max 274 | K on 109, coverage on 9 |
| **C4 losses** | 7 | p50 227, p25 120, max 316 | K on 6, recency on 1 |

**The reorder's entire cost is the recency tier's own carried evidence.** All
35 questions K-first loses are questions where the recency window happened to
hold the answer, and nothing else did. Its 80 gains are questions where
high-cosine evidence — median rank 3, inside the top handful — was being
crowded out of a binding budget by that window. Both sides of the trade sit at
the same median rank, which is what makes it a trade rather than a repair: the
recency window was accidentally carrying evidence that also ranks high.

**The coverage selector's entire measured advantage is deep-rank evidence.**
C3's nine gains are carried by coverage alone, at median cosine rank **85** —
far outside anything a ranking arm reaches at this budget. That is nine
questions out of 871, and it is the only place in this study where the
component earns something no other path supplies.

## 4. Magnitude does not transfer the way direction does

EC-002 moved any-evidence recall **32.3 percentage points**. This study moves
it **5.2** at the matched budget:

| | Corpus | Budget | Before → after | Points |
|---|---|---:|---|---:|
| EC-002 | LongMemEval-S, 470 answerable | 32,000 | 109 → 261 | **+32.3** |
| TC-002 | LoCoMo dev, 871 | 32,000 | 687 → 732 | **+5.2** |
| TC-002 | LoCoMo dev, 871 | 16,000 | 381 → 519 | **+15.8** |

The direction, the significance and the zero-loss-dominance all transfer; the
size does not. Preflight recorded why before the run: at 32,000 on this corpus
the two fill orders deliver a **byte-identical payload on 424 of 871
questions**, and median delivered recency falls only 32 → 30. At 16,000 the
same manipulation empties the recency window on 492 of 871 and median delivered
recency falls 32 → 0. The same one-line change is a different intervention at
the two budgets.

**No cross-corpus law is offered for that, and one may not be.** The obvious
story — EC-002's budget was more binding relative to its stores, which deliver
a median 17 episodes against this corpus's 110 — is exactly the shape of the
claim `DO_NOT_WRITE.md` #32 already refuted: *"the cross-corpus binding-ratio
law → refuted. Seven overlapping cells have opposite signs."* The two budgets
here are one corpus, and one corpus is not a law.

## 5. It is not one cut

Every breakdown registered in §4 runs the same way, and none was chosen after
the fact.

**C1 is positive in all four conversations and non-negative in all five
categories.** It reaches its bar in one conversation and one category, which is
what an 871-question effect of +45 does when it is cut into strata of 42 to
387.

| Conversation | C1 | C2 | C3 | C4 |
|---|---:|---:|---:|---:|
| `conv-41` (n=193) | +8 | −16 | +4 | +17 |
| `conv-42` (n=260) | +4 | −47 | +1 | +47 |
| `conv-47` (n=190) | +7 | −16 | +2 | +16 |
| `conv-48` (n=228) | **+26** | −31 | +1 | +31 |

| Category | n | C1 | C2 | C3 | C4 |
|---|---:|---:|---:|---:|---:|
| 1 | 109 | +6 | −4 | 0 | +4 |
| 2 | 143 | 0 | −12 | +3 | +12 |
| 3 | 42 | +1 | −1 | +1 | +2 |
| 4 | 387 | **+31** | −64 | +1 | +64 |
| 5 | 190 | +7 | −29 | +3 | +29 |

**The complete-evidence secondary agrees on every contrast:** C1 685 vs 633
(+52), C2 685 vs 810 (−125), C3 694 vs 685 (+9), C4 811 vs 685 (+126). All four
dispositions are the primary's, C3's `D2` included.

**The 16,000-character secondary agrees and is larger throughout:** C1 519 vs
381 (+138), C2 519 vs 803 (−284), C3 528 vs 519 (+9, and `D1` there against a
band of 4), C4 801 vs 519 (+282).

**The registered robustness check** (§8.3, `A_K_FIRST` charged the 18
characters it pays for a non-empty `recent_context` block) reproduces C2, C3
and C4 **exactly**: same hit counts, same gains and losses, same dispositions.
`A_K_FIRST`'s delivered characters fall p50 31,961 → 31,942, so the check ran.
C1 needed none: both its arms carry a non-empty recency block, so the primary
contrast is wrapper-symmetric by construction — which TC-001 could not say of
its own primary.

## 6. The band is a property of the budget, and this is the first study to show it

TC-001 measured its null band at 16,000 and got 4. TC-001B measured it at
16,000 and got 3. TC-002's primary is 32,000, so it measured there too:

| Budget | Noisiest arm under a ±1% sham budget nudge | Worst \|net\| |
|---:|---|---:|
| 16,000 | `A_N_FIRST` | 4 |
| 32,000 | `A_N_FIRST` | **7** |
| 32,000 | `A_DUAL_RANKED` | **0–1** |

**Had this study inherited a band it would have run its primary against a bar
43% too narrow.** The registration fixes B = 7 at 32,000 and B = 4 at 16,000,
each the maximum over every value measured at that budget with the inherited
ones included, and `verdict()` requires the band as an argument rather than
defaulting to one — a default is how the wrong band gets used silently.

**And on this data it changed nothing.** Recomputing every contrast at both
budgets and both endpoints against B = 4 instead of B = 7 returns the same
disposition in all eight cells. It moves four stratum readings, and every one of
those moves is between `D0a` and `D0b` — two labels that both say *no difference
established*. So the wider band cost this study no conclusion.

That is the result, not a disappointment about it. A band is measured so a
margin can be trusted, and the margins here are 45, 110 and 111 against a bar
of 7. The finding worth carrying forward is that **the band is budget-dependent
at all**, which no prior study in this arc was positioned to see, and which a
study with a smaller margin would have been decided by.

The quietest arm measured anywhere in this arc is `A_DUAL_RANKED`, at 0 to 1
questions. The noisiest is the shipped configuration.

## 7. What this does not establish

Restated from §9 of the registration, unchanged by the result.

- **Nothing that authorizes shipping the order change.** This was decided in
  the registration §0 *before* the number existed, precisely so a positive C1
  could not become the argument. `PAPER_002.md` §9.3 records that the same
  correction was tested live and **rejected on its own registered bar** — 7.0
  against 8.0 — and that the −1.0 margin is inside the 3.0-point instrument
  band and may not be cited to revive it. A more general availability claim is
  not an adoption claim.
- **Nothing about answers.** LV-001 measured 16 of 16 offline availability
  against 1.5 of 8 live. TC-006 owns the reader.
- **Nothing about the recency window's real behaviour.** §3.4 records that no
  live study ran a true last-*N* window. On a finished transcript "the last 32
  turns" is an arbitrary slice, and §3's finding that the reorder's whole cost
  is recency-carried evidence is a statement about that slice, not about a
  recency window doing what it was built for.
- **Nothing that transfers further.** One transfer, from LongMemEval to LoCoMo,
  and §4 shows the manipulation is already a different intervention at two
  budgets of the same corpus.
- **Not confirmatory.** Roadmap §0.1: no sealed external corpus remains to this
  programme. The arms were chosen with TC-001's and TC-001B's results known.
- **C3's `D2` is a signal, not an adoption.** Nine gains against one loss on
  ten discordant pairs. §9.3 of `AGENTS.md` registers that tier for exactly
  this: it justifies a successor, and nothing else. PF4 predicted the discordant
  count would be 10 before the bars were locked; it was 10.

One thing the study **can** now retire: `TC_ARC_ROADMAP.md` §10 listed
"whether TC-002's result, if positive, ships immediately or waits for TC-003"
as an open decision. It was decided in the registration and the answer stands
with a positive result on the table: it does not ship on this result.

## 8. Preflight, as it actually went

| # | Outcome |
|---|---|
| `PF1` | Pass. 2,247 cache hits, 0 misses; dataset, cache and every source file hashed in the run header |
| `PF2` | **Pass, on three proven identities.** `build_candidate_state` + `pack_stm_payload` equals `build_context`, and + `pack_k_first` equals `build_k_first_context`, on 3,484 comparisons. `build_k_first_context` at `recency_window_n=0` equals `build_context` at `recency_window_n=0` on 1,742 of 1,742 — with no recency tier the manipulation has no subject, so "K-first" is a fill order and nothing else |
| `PF3` | Pass. G0 committed at `361ac476` before the run phase opened any arm; re-checked in code |
| `PF4` | Pass, with the direction withheld. C1 115, C2 126, C3 **10**, C4 125 discordant pairs at the primary — all reachable and failable. C3's thin bar was registered as a power statement before the run, and the count it predicted was the count observed |
| `PF5` | Pass. Inherited from TC-001 unchanged |
| `PF6` | Pass on the instrument, **partial on the manipulation, and said so before the run.** G0 reproduces TC-001's committed tables on all four rows. EC-002 itself is not re-run — its runner refuses to execute off its own branch — so the manipulation's identity rests on `git diff` against `caa19f52` being empty on all six files of the K-first path. §8.2 of the registration states what that does not cover |
| `PF7` | Not applicable and demonstrated so: no path has feedback. The inertness check that *can* fail was run on every question and reported: 424 of 871 at the primary budget |
| `PF8` | Not applicable: full-population replay over all 871 questions |
| `PF9` | Six residuals recorded in §7.2 of the registration. Three stand after the run: presence is not use; `git diff` cannot see an environment drift in EC-002's pipeline; and a ±1% sham is a sham |
| `PF10` | Stated in the registration and restated in §7 |

**One provenance defect disclosed rather than repaired.** EC-002's
`source_integrity.json` records `script_sha256_after` = `f23164ea…` for its
runner, and the committed content at `caa19f52` hashes to neither its LF nor
its CRLF form today. `git diff` is empty for that path, so the content is
unchanged and the digest was taken on working-tree bytes whose line endings
this checkout does not reproduce. Nothing in TC-002 depends on it, because
TC-002 does not invoke that runner — but a reader checking that digest will
find it does not verify, and should know why.

## 9. Cost

Per question at 32,000 characters, over pools of 323 to 355:

| Arm | p50 (ms) |
|---|---:|
| `A_FLAT` | 24.5 – 28.0 |
| `A_N_FIRST` | 103.8 – 112.9 |
| `A_K_FIRST` | 104.5 – 113.7 |
| `A_DUAL` | 101.7 – 110.2 |
| `A_DUAL_RANKED` | 102.0 – 109.8 |

**Reordering the fill costs 1 to 3 ms.** It is the cheapest change this arc has
measured, and C1 says it buys 45 questions. Every selector arm still costs four
times the flat path, which is the clustering, and TC-005 owns that.

## 10. Rule 4 — the dependency re-read

TC-002 has reported, so `TC_ARC_ROADMAP.md` Rule 4 fires: every other study's
dependency line is re-read from the file and logged in
`TC_ARC_DEPENDENCY_LOG.md` with an explicit per-study verdict, **before the
next study is registered**. That log is updated in the same commit as this
report.

**Nothing is blocked.** No TC study depends on this one's verdict — Rule 2
forbids a dependency that names a stage — and a verdict cannot block anything: a
`BLOCKED` entry is valid only when it names a missing artifact.

**What changes how two studies should be read, which is not the same as being
blocked.** **TC-003** proposes reserved floors so allocation stops depending on
tier order. This study measured what changing the order alone is worth on this
corpus — 45 questions — against 111 for changing the order *within* a tier.
Floors address the first quantity. **TC-005**'s latency target belongs to a
component that this study finds carries a question's evidence alone on nine of
871, all of them at median cosine rank 85.

## 11. The dual arm, as a standing arm

The author's instruction opening this study was that the dual arm travel with
the arc from here on. It did, and it earned its place twice: C3 is the only
contrast that isolates deletion from deprioritization, and C4 supplies the
111-question comparison that turns C1's +45 from a result into a proportion.

The convention is `TC_ARC_ROADMAP.md` §1.1, the registry is
`src/analysis/tc_standing_arms.py`, and `tests/test_dual_arm_standing.py` holds
each arm's behavioural identity — 22 tests that name no budget, no bar and no
corpus, so an inherited arm that drifts fails a test rather than quietly
changing what a prior study's number meant.

The roadmap section also registers the cost: two extra arms are two extra
contrasts and a wider Bonferroni family, and a standing arm that is not worth a
divisor may be reported descriptively instead. TC-002 spent the divisor on
both. It was not what held C3 to `D2` — its *p* is 0.0107, which fails even
TC-001's uncorrected α of 0.01, narrowly. Ten discordant pairs is what held it
there, and PF4 said so before the run.
