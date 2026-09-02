# DA-012 Grouped Evidence-Carrier Ranking

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-011 result commit `d215a111`
**Standing:** descriptive grouped ranking exploration on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can DA-004's sealed evidence-blind edge features predict which temporal neighbor
actually carries missing direct evidence, and can that objective prevent the
prior-consumption failures identified by DA-011?

DA-011 showed that 13/16 residual misses have enough initial capacity but their
carriers arrive after earlier links consume it. DA-012 changes only edge order.
DA-009 rendering, DA-010 pair-then-turn payloads, budget and pack behavior remain
fixed.

## 2. Carrier Endpoint and Population

Use the 1,098 primary NF-004 questions and exact 16k direct selection. The model
population contains eligible non-direct edges only from the 163 questions whose
direct context is incomplete.

For each such edge, `CARRIER=1` when the neighbor pair contains at least one
dialogue ID in that question's missing direct evidence; otherwise zero. Multiple
carrier pairs remain independently positive for conjunction questions.

Carrier labels are used only for training and evaluation. At inference, scores
use DA-004's complete sealed feature vector and no answer, evidence identity,
category, outcome, reader, conversation identity, model, embedder, or cache.

## 3. Fixed Grouped Model

Fit the same fixed L2 logistic pipeline as DA-004: all sealed features in their
committed order, training-fold median imputation, training-fold standardization,
penalty 1, no class weighting. Produce leave-one-conversation-out predictions;
the target conversation's carrier labels never enter its model.

Report pooled ROC AUC, average precision, Brier score and every evaluable held-out
conversation AUC. Report `STABLE_CARRIER_PREDICTOR` only if pooled AUC is at
least .65 and every held-out conversation AUC is at least .50.

No feature selection, interaction, nonlinear model, coefficient inspection,
tuning, calibration, threshold, permutation, blend, or refit on target labels is
allowed.

## 4. Fixed Ordering Arms

Apply each order to all eligible edges. Direct-complete questions are retained
for exact outcome totals but cannot gain or lose direct evidence.

- `BENEFIT_ORDER`: exact DA-010 DA-004 grouped benefit score and ties; reproduce
  970 complete.
- `CARRIER_ORDER`: descending grouped carrier probability.
- `NEIGHBOR_COVERAGE`: descending sealed `neighbor_query_coverage`.

All ties use seed direct rank, prior before next, then neighbor identity. Every
arm uses DA-010's exact `PAIR_THEN_TURN` allocator. No admission threshold is
used; each arm traverses all edges with skip-on-overflow.

## 5. Fixed Analysis

Report carrier-label population and groups, model metrics, carrier rank
distributions, complete items, gains/losses versus direct and benefit order,
conversation cells, admissions, characters, residual rescues, conjunction
completion, and exact paired tests.

Every gain must be carried by admitted dialogue IDs. Any direct loss is a stop.
Reproduce direct 935, benefit 970, one-hop oracle 986, DA-004 benefit AUC
.823401708567509 and all sealed populations.

Report `CARRIER_RANK_SIGNAL` descriptively only if the model is
`STABLE_CARRIER_PREDICTOR`, `CARRIER_ORDER` exceeds 970, has zero direct losses,
and no conversation falls below `BENEFIT_ORDER`. Otherwise report
`NO_CARRIER_RANK_SIGNAL`. This is not an adoption bar.

## 6. Preflight Part 1 - Exploration

**Behavioral identity.** Only edge order changes. Direct rendering and payload
actions remain exact DA-010 behavior.

**Name-to-behavior.** Tests must establish carrier label construction, grouped
target exclusion, train-only preprocessing, fixed feature order, stable score
ties, unchanged payload allocation, conjunction labels, and exact causal gains.

**Distribution.** Before evidence access verify sealed hashes, feature schema,
question/edge/group populations and score-pipeline reachability. After the join
report positives, prevalence, evaluable groups and carrier ranks under all arms.

Primary risks are learning corpus-specific evidence annotation style, allowing
question identity leakage across groups, and mistaking grouped spent-data reuse
for fresh validation.

## 7. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify DA-011 result, DA-010 payload/result, DA-009 role,
  DA-004 blind/labels, 26,100 blind and 25,941 primary edges, 1,104/1,098
  questions and six conversations.
- **PF2 Identity:** pass every label, grouping, scoring, ordering and allocator
  test in Section 6.
- **PF3 Ordering:** commit protocol and mechanical preflight before carrier
  labels are constructed.
- **PF4 Reachability:** require positive/negative carrier labels in every group,
  ranking differences among all arms, carrier admissions and overflow skips.
- **PF5 Keys:** preserve every question, group, edge, pair, dialogue, evidence,
  direct, score and action key; reject duplicates or missing joins.
- **PF6 Reproduction:** require 935/970/986, DA-004 labels and AUC, exact benefit
  allocations and zero direct losses.
- **PF7 Absorbing state:** not applicable; require deterministic grouped scores
  and byte-identical result replay.
- **PF8 Length:** score all eligible edges from all direct-incomplete questions;
  evaluate all 1,098 outcomes.
- **PF9 Surrogate audit:** carrier availability is not answer use; grouped target
  exclusion on spent data is not fresh-corpus validation.
- **PF10 Live boundary:** adoption requires locked transfer data, reader,
  latency and prospective criteria.

## 8. Stops and Outputs

Stop on hash mismatch, group leakage, population drift, unevaluable conversation,
benefit replay failure, direct loss, nondeterminism or causal-accounting failure.
Commit mechanical preflight before evidence access, then result, report,
scratchpad and digest. No threshold, blend, reader or adoption is authorized.

