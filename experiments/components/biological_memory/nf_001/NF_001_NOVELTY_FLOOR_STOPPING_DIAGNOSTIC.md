# NF-001 — Novelty-Floor Stopping Diagnostic

**Document type:** Diagnostic specification
**Status:** `DESIGN ONLY — NOT PRE-REGISTERED — NO IMPLEMENTATION AUTHORIZED`
**Scope:** One question, committed artifacts only, zero model calls, no live run
**Relates to:** `HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md` §6.2
condition 2; `DMR_004_QUERY_OBLIGATION_COMPILER_IMPLEMENTATION_SPEC.md` §12
**Date:** August 12, 2026

## 0. Why this is a diagnostic and not an amendment

The author asked for this as an amendment on this branch. It cannot be one.
`AGENTS.md` §5 permits amendments that correct measurement units or repair
protocol contradictions and states that "adding a factor, policy level, or
budget is a new study and must be escalated." DMR-004 is closed with results
known, and a stopping rule is a new factor, so amending its registration would
be the exact move the rule exists to prevent.

It is also not a study. It adds no component to any shipping path, authorizes
no promotion, and runs entirely on committed candidate streams. It is a
diagnostic in the sense DX-001, DX-002 and RD-001 were: one falsifiable
question, a hard stop, and a characterization as its only possible output.

`PREFLIGHT.md` applies to diagnostics as much as to studies. §6 below is not
optional.

## 1. The question

DMR-004 tested `HYPOTHETICAL_001` §6.2's **first** stopping condition — all
mechanically identifiable obligations have evidence — and it failed. Two
conditions in that section were never built:

> - a step produces no new evidence for an unresolved obligation; or
> - `MAX_RETRIEVAL_STEPS` is reached.

The second is trivial. The first is not, and it is the only one of the three
that does not require parsing the query.

**NF-001 asks:** does the marginal novelty of retrieved evidence identify a
stopping depth that beats fixed depth, on the questions this program is
actually scored on?

Nothing here is about whether novelty-floor stopping is biologically faithful.
Plausibility is not evidence — the reference document's own line.

## 2. Why this is not the same rabbit hole

DMR-004 failed because query text does not fix the evidence obligation for two
thirds of real queries, and closing the gap meant enumerating question formats
one phrase list at a time. A novelty floor reads the retrieval stream, not the
question. It has **no query taxonomy, no marker vocabulary, and no per-format
classes**, so the tail that sank DMR-004 does not exist here.

Its own most likely failure is different and is stated up front in §5.

## 3. Data — committed only

Frozen candidate streams with their ranks, from the committed E005 and IC-001
artifacts, plus the study fact keys for measurement only. Zero model calls,
zero embedding calls, zero new corpora.

Mechanism reads candidate identities, their ranks, and their text. Mechanism
never reads a fact key; the key scores the result and nothing else.
`AGENTS.md` §4: measurement may use the plant key, mechanism may not.

## 4. Mechanism

At retrieval depth *k*, define the marginal novelty of the *k*-th candidate as
the fraction of its content not already covered by the first *k−1*. Stop at the
first *k* where marginal novelty stays below a floor for *w* consecutive
candidates.

Both `floor` and `w` are free parameters and Part 1 must characterize them
before either is locked. Neither may be inherited: `min_event_size` carried
unexamined through three DMR stages and became the binding constraint nobody
had tested.

The content unit is the open design question. Part 1 must show which of
character-level containment, token-set Jaccard, or fact-bearing span overlap
tracks the scored fact curve, **measured rather than assumed** — the read path
renders episodes while ranking scores spans, and this program has confused
those units before.

## 5. The failure this is most likely to have

**A novelty floor stops early exactly when a corpus repeats itself.** Study
010's endurance corpus is 156 distinct pairs across 1,000 episodes — 84% exact
duplicates. A rule that stops when nothing new arrives will stop almost
immediately there, and will look brilliant on a fact curve that plateaued for a
reason that has nothing to do with sufficiency.

Part 1 must therefore measure the duplicate rate **inside each candidate
stream**, not in the corpus, and report the stopping depth separately for
high-duplicate and low-duplicate streams. If the rule's advantage disappears
once duplicates are controlled, that is the finding and the diagnostic stops.

## 6. Preflight

**State:** `NOT RUN`. No run begins before it passes.

| Check | NF-001 required artifact |
|---|---|
| PF1 | Candidate streams present, hash-identified, counted; fact keys separately hashed and reachable only from measurement code |
| PF2 | The novelty statistic verified against its name on a committed stream: a hand-checked trace where the marginal-novelty values are recomputed by a second method |
| PF3 | An import-graph and grep test proving mechanism cannot read a fact key, plus a planted violation that fails |
| PF4 | Reachability **per bar**, both directions, before locking — the check DMR-001 omitted and stopped on |
| PF5 | Stream and candidate identities are content hashes, never ranks or row numbers |
| PF6 | Replay reproduces a committed E005 or IC-001 result by identity and digest before producing any new number |
| PF7 | The rule has no feedback into the store; state that, and bound the stopping depth at the maximum stream length |
| PF8 | States that this detects stopping-depth regret against a frozen candidate order, and cannot detect reader effects, ranking quality, or anything about live behaviour |
| PF9 | Surrogate audit with the degenerate arms: stop-at-1 and never-stop, both computed |
| PF10 | States that a stopping rule alone authorizes no retrieval change, no ablation, and no live run |

## 7. Measures and the registered statistic

The statistic is chosen before any result, and it must be insensitive to how
deep the oracle happens to sit — DMR-001C failed on a macro F1 that rewarded
frequent firing, and DMR-004 barred accuracy for the same class of reason.

**Primary: median regret against the oracle stopping depth**, where regret is
the scored fact count at the rule's depth minus the count at the depth that
maximizes facts for that question, at matched delivery budget.

**Secondary: stopping-depth swing**, the p95:p05 ratio of chosen depth across
questions. A rule that picks the same depth everywhere is fixed depth wearing a
costume — the diagnostic that worked in DMR-001B and DMR-001C, reused because
it worked.

**Controls, all computed:**

| Arm | What it is |
|---|---|
| `FIXED_k` | fixed depth, for a grid of *k* |
| `ORACLE` | the per-question depth that maximizes facts |
| `STOP_AT_1` | the degenerate early arm |
| `NEVER_STOP` | the degenerate late arm |

Raw fact counts are reported and cannot pass anything on their own.

## 8. Stop conditions

The diagnostic stops, and reports, if any of these fire:

1. Median regret is no better than the best `FIXED_k` at matched budget.
2. Stopping-depth swing is below the swing of the oracle depth — the rule is
   not adapting, it is picking a constant.
3. The advantage vanishes once high-duplicate streams are separated (§5).
4. Any parameter setting that passes requires a floor or window tuned per
   question.

## 9. What it can earn

At most: evidence that a query-blind stopping signal exists in the retrieval
stream, on committed candidate orders, at a stated regret against oracle depth.

It cannot earn a route controller, a promotion, an adoption, or a claim about
reader answers. If it survives, the next step is a conversation about whether
DMR-005 should be re-scoped around a retrieval-side sufficiency signal rather
than a query-side one — not an implementation.

## 10. Relationship to the DMR arc

DMR-005's dependency line requires "passing frozen DMR-004 plans". Those do not
exist. NF-001 does not change that and does not unblock DMR-005. It tests
whether a different sufficiency signal is worth designing a stage around, which
is a question the arc cannot currently answer from evidence.
