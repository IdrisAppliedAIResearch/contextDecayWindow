# DA-005 Structural Displacement Guard Exploration

**Status:** `POST-OUTCOME EXPLORATION PROTOCOL`
**Date:** August 29, 2026
**Parent:** DA-004 result commit `2712d211`
**Standing:** descriptive protection diagnostic on spent NF-004 LoCoMo
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can a label-blind, deterministic limit on the exact packing blast radius
exclude harmful edge admissions while retaining a useful share of DA-004's
beneficial actions?

DA-004 can rank benefit but cannot predict harm. DA-005 does not fit another
harm model. It tests structural guards that inspect only the counterfactual
identity delta before admitting an edge.

This exploration cannot select a guard, threshold, production rule, reader, or
adoption decision.

## 2. Locked Population and Decisions

Use DA-004's committed 26,100 blind perturbation rows at SHA-256
`e48e52b83f4b3704fedff81a44069b9caab775fd319a20ac863e99d96cb022b4`.
Do not open the corpus, vector cache, embedder, or model during the blind stage.

For every edge, record an admit/reject decision for these fixed guards:

- `OPEN`: admit every edge with at least one added identity;
- `COUNT_0`, `COUNT_1`, `COUNT_2`, `COUNT_4`: admit when displaced identity
  count is at most the suffix integer;
- `CHARS_256`, `CHARS_512`, `CHARS_1024`: admit when displaced characters are
  at most the suffix integer;
- `DUAL_1_512`: admit when displaced count is at most 1 and displaced
  characters are at most 512.

Edges with no added identity are rejected by every arm because they perform no
admission. Decisions use DA-004's exact set-level displaced count and character
sum, not DA-003's neighbor-local attribution.

## 3. Fixed Analysis

Commit the blind decisions and SHA-256 before importing DA-004 edge labels.
Require exact reproduction of 57 benefits, 40 harms, and 25,844 neutral primary
edges.

For each guard report:

- admitted primary edges and admission rate;
- retained benefits and benefit retention `retained / 57`;
- admitted harms and harm exclusion `1 - admitted / 40`;
- admitted neutral actions;
- benefit-minus-harm net among admitted actions;
- conversation-level retained benefits and admitted harms;
- p10/p50/p90 displaced count and characters among admitted actions.

Report the complete fixed table. A guard is `HARD_PROTECTION` only if it admits
zero harms by construction or observation; distinguish those explicitly. A
guard is `NONTRIVIAL_HARD_PROTECTION` descriptively only if it admits zero harms
and retains at least one benefit. This is not an adoption bar.

Do not combine the guards with DA-004 benefit scores, tune a threshold, add a
budget, compute a classifier, or select a winner after labels are opened.

## 4. Preflight Part 1 - Exploration

**Behavioral identity.** A displacement guard accepts or rejects a fully
simulated edge action based only on the number or exact characters of direct
identities the action removes. It does not identify evidence.

**Name-to-behavior.** Tests must establish no-op rejection, inclusive count and
character boundaries, dual conjunction, monotonic nesting within each guard
family, set-level rather than neighbor-local displacement, and deterministic
decision replay.

**Distribution.** Before labels, report decision counts, overlaps, empty
displacement, zero-character displacement, and exact-boundary cases for every
guard. Preserve every conversation.

The primary surrogate risk is calling low blast radius safe: one displaced
candidate can still be the required evidence. Only `COUNT_0` is safe by
construction at the exact-availability endpoint. Any other zero-harm result is
observational and spent-corpus-specific.

## 5. Preflight Part 2 - Checklist

- **PF1 Inputs:** verify the DA-004 blind artifact hash, 26,100 edges, 1,104
  questions, six conversations, and the fixed feature schema.
- **PF2 Identity:** pass every name-to-behavior and degenerate test in Section 4.
- **PF3 Ordering:** commit this protocol before implementation and commit blind
  decisions before importing edge labels.
- **PF4 Reachability:** require nonempty admit and reject sets for every guard
  except `OPEN`; require `COUNT_0` admits only zero-displacement actions.
- **PF5 Keys:** preserve question, seed, and neighbor keys; reject duplicates or
  missing DA-004 joins.
- **PF6 Reproduction:** require exact DA-004 label and carrier counts after join.
- **PF7 Absorbing state:** not applicable; require byte-identical blind replay.
- **PF8 Length:** enumerate every DA-004 edge and all primary edges after join;
  no new-corpus transfer is available.
- **PF9 Surrogate audit:** small displacement is not evidence-free displacement,
  and exact availability is not reader use.
- **PF10 Live boundary:** any selected guard requires a fresh corpus and
  separately locked benefit rule, reader, and adoption criteria.

## 6. Stops and Outputs

Stop on hash mismatch, population drift, missing identity, nondeterminism,
decision nesting failure, label-count mismatch, or an observed harm admitted by
`COUNT_0`.

Commit blind decisions, joined result, and report. Do not add, remove, combine,
or reinterpret a guard after labels are opened.
