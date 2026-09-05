# DA-011 Residual Reachable-Miss Mechanism Audit

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-010 result commit `882f9c2c`
**Standing:** descriptive causal audit on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

What blocks the 16 direct-incomplete questions whose complete evidence exists in
DA-004's one-hop edge population but is not delivered by DA-010's frozen
`PAIR_THEN_TURN` arm?

This audit changes no renderer, ranking, threshold, payload, budget, or result.
It identifies the next mechanism to test.

## 2. Locked Population and Replay

Use DA-010's committed blind payloads and allocations, DA-009 direct role
contexts, DA-004 blind rows/labels, and exact NF-004 evidence. Refit DA-004's
fixed grouped model only to reproduce AUC .823401708567509 and the exact edge
order. Replay `PAIR_THEN_TURN` action by action and require 935 direct, 970 arm,
986 all-eligible oracle, 35 gains, zero direct losses, and byte-identical final
dialogue selections.

The primary population is exactly the 16 questions that are direct-incomplete,
fallback-incomplete, and all-eligible-oracle-complete.

## 3. Fixed Trace

For every residual question and every missing direct evidence dialogue ID,
report its carrier pair, carrier edge position, DA-004 predicted score, lexical
member position, full-pair and evidence-member costs at arrival, initial and
arrival slack, prior admitted characters, pair overflow, chosen fallback member,
chosen-member fit/admission, and evidence-member fit.

Report missing dialogue count, distinct carrier-pair count, whether both members
of one pair are required, and the minimum exact cost of all missing evidence
members from an empty linked context under the frozen DA-009 dictionary.

## 4. Mutually Exclusive Blocker Classes

Assign each residual question to the first applicable class:

1. `MULTI_PAIR_CONJUNCTION`: missing evidence spans more than one carrier pair.
2. `BOTH_MEMBER_CONJUNCTION`: both members of one carrier pair are required.
3. `WRONG_MEMBER`: one carrier pair suffices; its full pair overflows; the blind
   chosen member does not carry all missing evidence; the required member would
   fit at the same arrival state.
4. `PRIOR_CONSUMPTION`: required evidence payload fits initial direct slack but
   not its arrival slack after earlier links.
5. `BASE_CAPACITY`: required evidence payload does not fit initial direct slack.
6. `OTHER_TRACE_FAILURE`: none of the above; report exact trace without repair.

Classes describe the frozen path. They do not authorize a fix.

## 5. Fixed Diagnostic Counterfactuals

Run two outcome-oracle diagnostics, clearly labelled non-deployable:

- `ORACLE_MEMBER`: preserve edge order and pair-first behavior, but after full
  pair overflow choose an evidence-bearing member when one exists; otherwise use
  the frozen lexical member.
- `CARRIER_FIRST`: preserve pair-then-lexical-turn payload behavior but move all
  evidence-carrier edges before noncarriers, retaining their relative order.

Report complete totals, residual rescues, any losses versus DA-010, conversation
cells, and exact discordance. These are causal upper bounds, not candidate rules.

## 6. Preflight Part 1 - Audit

**Behavioral identity.** The baseline trace must exactly reproduce DA-010 at
every action and final dialogue identity. Diagnostics change only the named
member choice or edge order.

**Name-to-behavior.** Tests must establish arrival slack, pair overflow,
fallback admission, evidence-member alternative cost, multiple carrier pairs,
both-member conjunction, hierarchical classification, oracle-member isolation,
carrier-first stable partition, and skip-on-overflow continuation.

**Distribution.** Before evidence access verify all sealed hashes, populations,
both member indices, pair/turn fit disagreement, and every conversation. After
the join report all class counts and continuous trace distributions.

Primary risks are treating an oracle diagnostic as a deployable rule and
assigning one cause when conjunction requires multiple actions.

## 7. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify DA-010 payload/result, DA-009 role, DA-004 blind/labels,
  26,100 blind and 25,941 primary edges, 1,104/1,098 questions, six conversations.
- **PF2 Identity:** pass every trace, class, and diagnostic test in Section 6.
- **PF3 Ordering:** commit protocol before implementation and mechanical
  preflight before evidence analysis.
- **PF4 Reachability:** require pair overflow, fallback admission, both lexical
  member choices, carrier reordering, and a synthetic instance of every class.
- **PF5 Keys:** preserve every question, edge, pair, member, dialogue, direct,
  evidence, score, and action key; reject duplicates or missing joins.
- **PF6 Reproduction:** require 935/970/986, 35/0, exact DA-010 selections,
  DA-004 labels and grouped AUC.
- **PF7 Absorbing state:** not applicable; require deterministic trace replay.
- **PF8 Length:** audit all 16 residual questions and all their carrier actions.
- **PF9 Surrogate audit:** oracle rescues are upper bounds, not evidence-blind
  predictors; exact availability is not reader use.
- **PF10 Live boundary:** any successor needs its own registration, blind rule,
  fresh transfer, reader and adoption criteria.

## 8. Stops and Outputs

Stop on hash mismatch, replay drift, population mismatch, unclassified residual,
diagnostic direct loss, nondeterminism, or causal-accounting failure. Commit the
mechanical preflight before evidence access, then result, report, scratchpad and
digest. No model, embedder, cache, threshold tuning, or adoption is authorized.

