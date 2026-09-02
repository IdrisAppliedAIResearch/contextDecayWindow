# DA-004 Evidence-Blind Pack Perturbation Exploration

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 29, 2026
**Parent:** DA-003 stop commit `584c8bf0`
**Standing:** descriptive signal search on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can evidence-blind properties of the complete packing perturbation predict
whether admitting one temporal edge helps or harms exact evidence delivery?

DA-003 showed that the action is not the neighbor alone. Skip-on-overflow can
change which later candidates fit. DA-004 therefore treats every candidate
newly admitted and displaced by the one-edge counterfactual as the indivisible
decision object.

This spent-corpus exploration cannot select a gate, threshold, seed depth,
reader, production policy, or adoption decision.

## 2. Locked Inputs and Population

Use DA-003's committed 26,100 blind edge rows at SHA-256
`0d669cc7a0b2da9b0bfa7439fdd7c182ee4ea6f60a0bf6e0c8fdf79567b02c5c`,
DA-002's committed blind candidate provenance, and the byte-locked LoCoMo
candidate text. Do not open an embedding cache or invoke an embedder or model.

Retain DA-003's one-edge unit, top-16 first-emitter population, direct order,
counterfactual order, exact 16k packer, and primary eligibility. For each edge:

- `ADDED` is every counterfactual-selected identity absent from `DIRECT`;
- `DISPLACED` is every direct-selected identity absent from the counterfactual;
- the neighbor is one member of `ADDED` when admitted, but receives no special
  causal credit for the action outcome.

## 3. Fixed Blind Features

Carry all 35 sealed DA-003 edge features unchanged, then add the following
whole-perturbation features. Text uses DA-003's lowercase ASCII alphanumeric
tokenization and candidate-corpus IDF.

### 3.1 Added set

- count and characters;
- own-query cosine sum, mean, minimum, maximum, and character-weighted mean;
- IDF-weighted query coverage of the union of all added texts;
- matched query-token count, numeric-token count, and four-digit-year count;
- same count, characters, score sum, and query coverage excluding the neighbor.

### 3.2 Displaced set

- count and characters;
- own-query cosine sum, mean, minimum, maximum, and character-weighted mean;
- IDF-weighted query coverage of the union of all displaced texts;
- matched query-token count, numeric-token count, and four-digit-year count.

### 3.3 Perturbation balance

- added minus displaced count, characters, score sum, score mean, and query
  coverage;
- added-to-displaced ratios for characters, score sum, and query coverage,
  using denominator `max(value, 1e-9)`;
- selected-set Jaccard and changed-identity count;
- neighbor share of added characters and added score sum, with zero for an
  empty added set.

No feature uses answers, evidence identities, evidence counts, categories,
outcomes, reader judgments, or conversation identity as a predictor.

## 4. Fixed Analysis

After the blind perturbation rows and SHA-256 are committed, join NF-004 exact
evidence and primary eligibility.

- `BENEFIT`: counterfactual complete and `DIRECT` incomplete;
- `HARM`: `DIRECT` complete and counterfactual incomplete;
- `NEUTRAL`: neither transition.

The causal check is set-level: every benefit must have at least one missing
direct evidence identity in `ADDED`; every harm must have at least one direct
evidence identity in `DISPLACED`. Report neighbor-carried versus downstream-
carried benefits descriptively, but fit no subgroup model.

For every feature and each endpoint, report raw larger-is-positive pooled and
per-conversation AUC. Report p10/p50/p90 by all three labels.

Fit one fixed L2 logistic model with penalty 1 separately for `BENEFIT` and
`HARM`, using every feature. Evaluate by leave-one-conversation-out prediction;
median imputation and z-standardization are fitted on training conversations
only. Report pooled ROC AUC, average precision, Brier score, and each evaluable
conversation AUC. No tuning, class weighting, permutation, feature selection,
interaction, nonlinear model, threshold, or ablation is allowed.

Report `NEW_SIGNAL_PRESENT` descriptively for an endpoint only when pooled AUC
is at least .65 and every evaluable held-out conversation AUC is at least .50.
Otherwise report `NO_STABLE_PACK_SIGNAL`. This is not an adoption bar.

## 5. Preflight Part 1 - Exploration

**Behavioral identity.** One edge perturbs a stateful exact pack. Its action is
the full identity delta between direct and counterfactual selected sets, not
the promoted neighbor in isolation.

**Name-to-behavior.** Tests must establish exact set differences, downstream
admission, neighbor exclusion, score and character aggregation, union query
coverage, empty-set values, balance arithmetic, and identity Jaccard.

**Distribution.** Preserve all conversations and directions; report empty
added/displaced sets, neighbor overflow, no downstream addition, multiple
downstream additions, zero query coverage, and zero-denominator ratios.

The primary surrogate risk is a high perturbation score caused by repeated
question words without answer information. A second is classifying displaced
low-cosine content as expendable when it carries evidence.

## 6. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify DA-003 and DA-002 artifact hashes, locked corpus bytes,
  26,100 edges, 1,104 questions, and six conversations.
- **PF2 Identity:** pass every name-to-behavior and degenerate test in Section 5.
- **PF3 Ordering:** commit this protocol before implementation and commit blind
  perturbation rows before the analysis imports evidence.
- **PF4 Reachability:** after join require benefit, harm, neutral, neighbor-
  carried benefit, and downstream-carried benefit.
- **PF5 Keys:** reject duplicate or missing question, seed, neighbor, candidate,
  direct-selected, or counterfactual-selected identities.
- **PF6 Reproduction:** require 935/1,098 direct complete, DA-003's 48 neighbor
  benefits, 9 downstream benefits, 40 harms, and 25,844 neutral primary edges.
- **PF7 Absorbing state:** not applicable; require byte-identical blind replay.
- **PF8 Length:** use every DA-003 edge and every primary edge after join; no
  new-corpus transfer is available.
- **PF9 Surrogate audit:** set-level lexical and cosine efficiency are not
  evidence utility, and exact availability is not reader use.
- **PF10 Live boundary:** any gate requires a fresh corpus and separately locked
  prospective rule, threshold, reader, and adoption criteria.

## 7. Stops and Outputs

Stop on any hash mismatch, missing identity, cache access, nondeterminism,
population mismatch, direct-total mismatch, causal set-accounting failure, or
DA-003 transition-count mismatch.

Commit a blind perturbation artifact, joined result artifact, and report. Do
not alter features, endpoints, model, groups, or reporting rules after labels
are opened.
