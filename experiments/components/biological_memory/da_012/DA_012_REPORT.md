# DA-012 Grouped Evidence-Carrier Ranking Report

**Status:** `NO_CARRIER_RANK_SIGNAL`
**Protocol commit:** `8155ee86`
**Mechanical preflight commit:** `383d083c`
**Standing:** grouped ranking exploration on spent NF-004 LoCoMo
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 30, 2026

## Result

The grouped carrier classifier is stable as an edge-level predictor but does not
improve exact delivery:

| Order | Complete | Gains vs direct | Losses | Versus benefit |
|---|---:|---:|---:|---:|
| DA-004 benefit | **970** | 35 | 0 | control |
| Grouped carrier | **970** | 35 | 0 | 3 gains / 3 losses |
| Neighbor coverage | 966 | 31 | 0 | 4 / 8 |

Carrier versus benefit has exact p=1.0 and regresses `conv-50` by one item while
gaining one in `conv-43`. It therefore fails the registered delivery and
conversation nonregression bars.

## Predictor

On 2,264 eligible edges from the 163 direct-incomplete questions, 76 are carrier
positive (3.36%). The leave-one-conversation-out carrier model reports:

- pooled ROC AUC .7645;
- average precision .2266;
- Brier .0298;
- conversation AUCs .853, .660, .670, .707, .756, and .929.

It passes `STABLE_CARRIER_PREDICTOR`. Raw neighbor query coverage is weaker at
AUC .6968 but remains above .50 in every conversation.

## Why Prediction Does Not Convert

The allocation problem is within-question and capacity-bound, while pooled AUC
counts every positive-negative edge comparison across questions. Carrier median
rank is already 2 under benefit order and remains 2 under carrier order; p90
moves only from 11.5 to 10.5. That small tail shift trades item identities rather
than increasing complete sets.

Neither learned order completes a multi-carrier conjunction. Raw coverage
completes one conjunction but loses more single-carrier items elsewhere. A
stable pooled carrier endpoint is therefore insufficient as the allocation
objective.

## Consequence

The carrier-ranking branch closes on NF-004. Thresholds, blends, within-question
losses, nonlinear models or feature selection would tune the spent corpus and
are not authorized.

The robust carried architecture remains DA-010's cumulative 970 result:
reversible direct speaker/role compression, frozen DA-004 benefit order, full
linked pairs with lexical-turn fallback only on overflow. The next useful test
is transfer of that frozen architecture outside the six NF-004 conversations,
not another NF-004 ranking objective.

## Integrity and Boundary

All seals, 25,941 primary edges, 935 direct, 970 benefit, 986 oracle, DA-004 AUC
and exact benefit allocations reproduce. The result SHA-256 is
`93af8acac931c7f58debbab84444e81ec4352b63815aed9d2b9535f7e9f6f3c5`.

Target conversations are excluded from carrier training, but this remains
grouped reuse of a spent corpus. It is not fresh validation, reader evidence or
adoption authority.

