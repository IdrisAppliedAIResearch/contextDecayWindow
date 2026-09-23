# AF-PRE-009 Amendment 001 (pre-interpretation, registered before any case is read)

The registered run reproduced 56/120 exactly and attributed the 64 misses as
`{E1:10, E2:0, E3:0, E4-near:7, E4-far:11, E5:36}`. Two features of that table were not
anticipated and one of them is ambiguous in a way that changes the conclusion, so a second
mechanical measurement is added **before** any interpretation or case reading. No category
boundary above is moved; this addendum only sub-partitions E5/E3 with new mechanical tests.

**The ambiguity.** E3 (gold lacks the answer value, prediction has it) came back **empty**, while
E5 (neither turn has it) holds 36. Two very different stories fit both facts:
(a) the model is not finding answers anywhere — it has no signal on those items; or
(b) the answer value is not in *any* turn of the conversation, so no ranker over turn text
could ever be right, and the item is unanswerable at the turn level.
These imply different next probes (more/better training data vs a different candidate unit), so
they must be separated by measurement, not by preference.

## Mechanical sub-tests (added, computed on committed data only, no model, no readers)

Priority-ordered over the same 64 misses, with the frozen answer-presence rule from the plan:

- **X4 ANSWER-AT-GOLD.** Gold contains the answer value (= the E4 items; kept for completeness).
- **X3 ANSWER-ELSEWHERE-IN-TEXT.** Gold does not, but some turn's text does — including the
  predicted turn or a turn between gold and prediction. A textually available target existed and
  the reranker did not take it.
- **X2 ANSWER-IN-SESSION-HEADER.** No turn contains the answer value, but a
  `conversation.session_N_date_time` header does. LoCoMo puts dates in session metadata, and
  `arms.load_conversations` drops it: the information needed is outside the candidate unit that
  every AF-PRE arm ranks.
- **X1 ANSWER-NOWHERE.** No turn and no session header contains the answer value — the item is
  not solvable by any turn-level method (answers that are counts, comparisons, yes/no, or
  paraphrases), so the ceiling of every reranker on that item is 0.

Pre-registered interpretation rule (fixed now): if X1+X2 ≥ 18 (more than a quarter of the 64,
and more than half of E5), the limiting factor of the *current* probe sequence is the
**candidate unit** (turn text without session metadata) and no further ranking or training probe
on turn text has a reachable bar above ~70/120. If X1+X2 < 18 and X3 ≥ 18, the loss is a
ranking/comprehension failure on textually solvable items and a training-side probe stays live.
Between the two, both are reported and no single-factor claim is made.

## Also recorded (association test, no model)

Fisher exact on the registered 2×2 (answer present at gold × item correct), reported with the
odds ratio, so the answer-presence association is a tested number rather than a narrative.
