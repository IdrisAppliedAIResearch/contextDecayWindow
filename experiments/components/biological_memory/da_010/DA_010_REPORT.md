# DA-010 Evidence-Blind Linked Payload Granularity Report

**Status:** `COMPACT_PAYLOAD_SIGNAL` for `ATOMIC_TURNS` and `PAIR_THEN_TURN`
**Protocol commit:** `50d2e27f`
**Blind-selection commit:** `17031eaa`
**Standing:** post-outcome payload diagnostic on spent NF-004 LoCoMo
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 30, 2026

## Result

Keeping full pairs when they fit and falling back to the evidence-blind lexical
turn only on pair overflow raises complete evidence from DA-009's 966 to **970**.
Atomic turns independently reach the same 970 complete-item set.

| Payload arm | Complete | Gains vs direct | Losses | Versus full pair |
|---|---:|---:|---:|---:|
| `FULL_PAIR` | 966 | 31 | 0 | control |
| `BEST_TURN` | 962 | 27 | 0 | 6 gains / 10 losses |
| `ATOMIC_TURNS` | **970** | **35** | 0 | 4 / 0 |
| `PAIR_THEN_TURN` | **970** | **35** | 0 | 4 / 0 |

The winning arms are nondecreasing in every conversation. The four incremental
rescues are two items in `conv-43` and two in `conv-49`. Their exact paired
contrast with full pairs is p=.125, so this is a registered descriptive signal,
not a statistically differentiated incremental result.

## Mechanism

Global best-turn replacement is too aggressive. It admits 5,880 members but
loses ten full-pair completions while finding six others. Lexical overlap does
not reliably identify which member carries evidence.

`PAIR_THEN_TURN` preserves a full pair whenever possible. It admits 2,535 full
pairs and uses 1,176 singleton fallbacks only after pair overflow. Those
fallbacks recover four additional items without losing any full-pair completion.
Median linked payload rises from 635 to 649 characters and median unused slack
falls from 41 to 19.

`ATOMIC_TURNS` admits 6,266 members and changes the linked dialogue sequence on
922/1,098 questions relative to fallback, but produces the exact same complete
item set. Fragmenting every pair therefore adds churn without additional exact
availability. Pair-first fallback is the narrower explanatory mechanism.

None of the 35 gains requires both dialogue members from the same linked pair.
The remaining useful evidence is localized to individual turns, but selecting
one turn globally is unsafe; localization is useful specifically at the
overflow boundary after pair protection.

## Ceiling

DA-010 recovers 35 of the 51 one-hop-rescuable direct misses, leaving 16. The
protected sequence is now:

- DA-008 reversible speaker dictionary: 961, +26/0;
- DA-009 repeated role pattern: 966, +31/0;
- DA-010 overflow-only turn fallback: 970, +35/0.

The incremental gains continue as measured representation cost falls. This is
not generic context flooding: direct evidence remains fixed and exact, and the
payload rule only changes how a ranked linked pair is materialized when its full
form does not fit.

## Integrity and Boundary

The blind payload artifact replayed byte-identically at SHA-256
`51e0e648f66bf2c5a7ab6161c5fbcbc9efaadff306beb9b98ffac6a2f19d47b3`.
The result SHA-256 is
`ef59203e80991132dffad38cd849bf161026a038490b9b518c095c612e54c1af`.
Direct 935, full-pair 966, all DA-004 labels and grouped AUC reproduce exactly.

This remains spent-corpus availability. It does not validate reader use,
transfer, lexical member selection, or payload adoption.

