# TC-009 safe-substitution signal probe

**Type:** descriptive post-run feasibility diagnostic; not TC-010  
**Status:** design lock before implementation  
**Date:** 2026-08-23  
**Parent:** `TC_009_REPORT.md`; accepted TC-009 question-level and frozen-selection artifacts

## 1. Question and boundary

Before registering another selector, test whether evidence-blind properties of
TC-009's 32k selected-set changes distinguish questions where dynamic spread
adds required evidence from questions where it removes required evidence.

This probe cannot select an architecture, tune a threshold, change TC-009's
verdict, authorize reader calls, or claim generalization. LoCoMo development is
used and labels are already open. A positive result is only a hypothesis worth
testing on a new registration/corpus; a negative result closes this frozen
feature list on these deltas.

## 2. Frozen population and labels

- Use all 868 eligible TC-009 questions at exactly 32,000 characters.
- Features are produced from the accepted label-blind
  `frozen_selections.jsonl.gz`, the committed blind manifest and its read-only
  vector cache. The feature artifact must exist and be hash-recorded before
  `per_question.csv` is imported.
- `gain`: dynamic delivers more required identities than dense control.
- `loss`: dynamic delivers fewer required identities than dense control.
- `tie`: equal required-identity count.
- Complete-evidence direction is secondary and reported without changing the
  primary label.

No row is removed because a selected-set delta is empty or a feature is
unfavorable. Undefined set summaries receive an explicit missing flag and a
fixed numeric sentinel of zero; missingness is itself reported.

## 3. Frozen evidence-blind features

For `incoming = dynamic_selected - dense_selected`,
`outgoing = dense_selected - dynamic_selected`, and
`retained = their intersection`, calculate:

1. `query_margin_best`: best incoming query cosine minus best outgoing cosine;
2. `query_margin_worst`: worst incoming cosine minus worst outgoing cosine;
3. `incoming_novelty_max/mean`: one minus each incoming candidate's maximum
   cosine to retained candidates;
4. `outgoing_redundancy_max/mean`: each outgoing candidate's maximum cosine to
   retained candidates;
5. `incoming_dense_rank_best/mean` with sign reversed so larger is predicted
   safer;
6. `outgoing_dense_rank_worst/mean`, where larger is predicted safer;
7. represented-session delta, selected-candidate-count delta and payload-char
   delta, all oriented so larger is predicted safer;
8. maximum and mean dynamic accumulated penalty among incoming candidates,
   sign reversed so smaller penalties are predicted safer.

Cosines use the committed float32 vectors and the same unit normalization as
the carried dense route. No learned combination, coefficient fitting, feature
selection, threshold sweep, text inspection, lexical feature or evidence field
is allowed.

## 4. Frozen descriptive signal rule

Evaluate each feature independently in its registered direction.

A feature is `DESCRIPTIVE_SIGNAL` only if all hold:

1. average precision over all 868 questions is at least 3x gain prevalence;
2. ROC AUC on gain-versus-loss questions is at least `.70`;
3. every source conversation containing both a gain and loss has AUC `>.50`;
4. its top 20 questions contain at least two gains; and
5. it is finite on all non-missing rows and its missing flag alone does not
   satisfy items 1-4.

If no feature passes, disposition is `NO_POSITIVE_SIGNAL`. Otherwise it is
`DESCRIPTIVE_SIGNAL`, naming every passer. No multiplicity-adjusted inference
or confirmatory p-value is claimed.

## 5. Preflight — mandatory before the label join

Part 1 must record the frozen input hashes/cardinalities, selected-set delta
sizes and feature distributions without importing evidence. It must verify in
one falsifiable sentence that the extractor compares accepted dynamic-only and
dense-only 32k candidates and never reruns either selector.

- **PF1:** hash/count frozen selections, blind manifest, vector manifest/cache
  and per-question labels; labels are counted only by a separate preflight
  process after feature extraction.
- **PF2:** replay selected ids/payload digests against TC-009 and verify feature
  names against calculations on a planted two-candidate trace.
- **PF3:** prove feature artifact closure before label-module import with an
  execution trace and planted early-import failure.
- **PF4:** demonstrate all five signal clauses and both dispositions are
  reachable on synthetic feature/label rows before running real labels.
- **PF5:** join only by TC-009 question content identity.
- **PF6:** reproduce all 1,742 TC-009 control/dynamic payload identities.
- **PF7:** not applicable; no feedback mechanism is run.
- **PF8:** four source conversations can expose direction reversal but cannot
  estimate transfer to a new corpus.
- **PF9:** a high AUC can still be an exhausted-corpus artifact and cannot
  certify safe substitution; record prevalence, AP, top-20 precision and every
  conversation direction.
- **PF10:** availability only; reader evaluation would require a separate
  registration even after a signal.

Any Preflight failure stops before label join. Run with one thread, explicit
UTF-8, zero cache misses, zero embedding calls and zero LLM/generative calls.

## 6. Artifacts

Commit Preflight before the probe result. The result must include the frozen
feature table, feature SHA-256, label join audit, full metric table,
conversation metrics, exact top-20 question identities, missingness, call
audit and disposition.
