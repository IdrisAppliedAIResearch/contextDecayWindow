# NF-004 Item-Level Anatomy Exploration

**Status:** `EXPLORATION PROTOCOL - OUTCOMES ALREADY OPEN`
**Date:** August 29, 2026
**Parent result:** NF-004, 140 pair-ranking gains and 48 session-inheritance
rescues at 16,000 candidate-text characters
**Standing:** post-outcome descriptive reanalysis; no confirmatory, adoption, or
reader claim is available
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question and boundary

Characterize NF-004's discordant items and ask whether evidence-blind properties
available at retrieval time predict whether pair ranking helps or session-score
inheritance helps. The result may identify a mechanism hypothesis or conclude
that the available observables do not generalize across conversations.

NF-004 outcomes are already known. This protocol is a design lock for an
exploratory audit, not a pre-registration, and no p-value can restore sealed
standing. LoCoMo is spent. The analysis does not authorize a selector, another
LoCoMo optimization, a live run, or a production change.

## 2. Inputs

- The exact NF-004 LoCoMo corpus, split, adjacent-turn candidates, 16,000-char
  budget, Qwen3 embedding cache, mechanism, and sealed G6 outcome artifact.
- The G6 rows supply only stable item identity and the two binary complete-
  evidence outcomes at label-join time.
- Corpus answers, categories, evidence identities, evidence counts, evidence
  ranks, and source answer text are forbidden to the feature extractor.

The extractor may read question text, candidate text and length, source/session
membership and order, cached question/candidate vectors, score arrays, ranking
orders, and packed candidate identities. These are all available before any
evidence join in the original mechanism.

## 3. Behavioral identity

Session ranking assigns every adjacent-turn pair the maximum own-query cosine
found anywhere in its session, creating source-ordered score plateaus; pair
ranking orders the same candidates by each pair's own cosine; both greedily
skip candidates that overflow the same 16,000-character budget.

The named outcome classes are:

- `PAIR_GAIN`: pair ranking delivers all annotated evidence and session ranking
  does not;
- `SESSION_RESCUE`: session ranking delivers all annotated evidence and pair
  ranking does not;
- `BOTH_PASS` and `BOTH_FAIL`: concordant descriptive classes.

## 4. Evidence-blind feature families

Every scalar is fixed before the extractor is implemented.

1. **Query surface:** characters, whitespace words, unique lowercase-word
   fraction, digit count, and question-mark count.
2. **Own-score shape:** maximum, second maximum, maximum gap, mean, standard
   deviation, p90-p50 spread, and counts within 0.01, 0.03, and 0.05 of the
   maximum.
3. **Session plateau shape:** number of sessions; top and second session maxima;
   their gap; number, characters, own-score mean, own-score standard deviation,
   and own-score range inside the top session; and the source position of the
   best pair inside that session.
4. **Rank disagreement:** Spearman correlation between own scores and inherited
   session scores; mean and maximum absolute rank displacement; and top-10,
   top-25, and top-50 identity overlap.
5. **Packed-set contrast:** selected counts, packed characters, slack, sessions
   touched, Jaccard overlap, pair-only/session-only counts and characters, and
   mean own cosine of each arm's selected, unique, and dropped candidates.
6. **Budget frontier:** own-score minimum among each arm's selected candidates,
   maximum among its unselected candidates, and selected-minus-unselected
   frontier margin.

Conversation identity, source index, and item identity are retained for grouped
evaluation and integrity only. They are never predictor columns. No lexical
feature from candidate contents is used in this pass, avoiding a high-dimensional
post-outcome search over the answer-bearing store.

## 5. Analysis

### 5.1 Anatomy

Report all four class counts and, for every feature, class medians and
interquartile ranges. For `PAIR_GAIN` versus `SESSION_RESCUE`, report pooled AUC,
direction, and AUC separately for every conversation containing both classes.
Also report the ten largest standardized median differences in absolute value.
These are descriptive rankings, not feature-selection claims.

### 5.2 Prediction

The prediction population is the 188 primary discordant items. Positive means
`PAIR_GAIN`; negative means `SESSION_RESCUE`.

- Evaluate one multivariable model by leave-one-conversation-out prediction.
- Within each outer training fold, median-impute and z-standardize from training
  data only.
- Fit L2 logistic regression. Select lambda from
  `{0.01, 0.1, 1, 10, 100}` by inner leave-one-conversation-out AUC, breaking
  ties toward larger lambda.
- Report pooled out-of-fold ROC AUC, average precision, Brier score, and each
  held-out conversation's AUC where both labels exist.
- Compare against the no-feature training-prevalence probability baseline.
- Run 10,000 deterministic permutations of labels within conversation and
  rerun the complete nested procedure. Report `(1 + exceedances) / 10001` for
  out-of-fold AUC.

The model carries a useful cross-conversation signal only descriptively if
pooled out-of-fold AUC is at least 0.65, permutation p is at most 0.05, and no
evaluable held-out conversation has AUC below 0.50. Otherwise report
`NO_STABLE_EVIDENCE_BLIND_PREDICTOR`. This label is an exploratory reporting
rule, not a registered disposition.

### 5.3 Sensitivity

Repeat pooled out-of-fold AUC for each feature family removed in turn. Report
only the fixed family ablations above. Do not add interactions, nonlinear
models, thresholds, subgroups, budgets, endpoints, or features after labels are
joined.

## 6. Preflight Part 1 - Exploration

NF-004's committed traces establish that both arms use identical candidates and
packing policy, while ranking differs exactly as stated in Section 3. At 16k,
both stores bind: median packed characters are 15,986 and 15,988. Pair ranking
moves median best-evidence rank from 9 to 2 but still loses 48 items, proving
both discordant classes exist. All six conversations have positive net results,
but that does not establish within-conversation predictability.

Degenerate states to test before label access: single-session stores; one-item
sessions; tied scores; zero unique candidates between arms; no unselected item;
constant predictor columns; outer or inner folds with one label; and a planted
attempt by the feature module to import the measurement module or G6 artifact.

The main surrogate risk is an impressive pooled AUC driven by conversation
identity. Grouped outer evaluation and per-conversation AUC are binding parts of
the report. A second risk is a high AUC with poor probability quality under the
140:48 class imbalance; average precision and Brier score are reported beside
AUC.

## 7. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify file hashes, corpus bytes, six holdout conversations,
  1,098 primary rows, 2,749 cache entries, and zero cache misses.
- **PF2 Identity:** reproduce both NF-004 16k ranking and packed payloads before
  extracting features.
- **PF3 Order:** seal evidence-blind feature rows before the process that imports
  G6 outcomes; the joined analysis must reject an unsealed feature file.
- **PF4 Reachability:** 140 positive and 48 negative discordances make AUC and
  grouped evaluation reachable; record conversations lacking both labels.
- **PF5 Keys:** use NF-004 canonical comparison keys and reject duplicates,
  missing keys, or population drift.
- **PF6 Reproduction:** recompute 843/935 and 140/48 exactly after the join.
- **PF7 Absorbing state:** full-store fit makes both ranking arms identical;
  this analysis remains fixed at the binding registered 16k budget.
- **PF8 Length:** use all 1,098 primary items and all 188 discordances.
- **PF9 Surrogate audit:** pooled fit, in-sample fit, or conversation prediction
  can look good while a new conversation fails; only grouped out-of-fold
  predictions enter the reporting rule.
- **PF10 Live boundary:** evidence availability is not answer use. Any reader or
  adoption claim requires a new corpus and prospective live registration.

## 8. Outputs and stops

Write a preflight/feature artifact, joined result artifact, and report. Stop
without prediction results on any hash mismatch, cache miss, mechanism replay
failure, duplicate key, early label access, missing primary row, nonfinite
feature, nondeterministic replay, or outcome-count mismatch. Preserve every
negative and inconsistent result; do not tune after the join.
