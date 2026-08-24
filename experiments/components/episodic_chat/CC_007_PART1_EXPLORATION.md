# CC-007 Part 1 — deployed CC80 + static ASPECT characterization

**Type:** engineering adoption exploration  
**Date:** 2026-08-24  
**Branch:** `codex/episodic-chat-cc80-aspect`

## Behavioral identity

On the committed LoCoMo development trace, CC80 is a complete-store episode
ranking formed by independently min-max normalizing dense cosine and BM25 and
combining them as `0.8*dense + 0.2*BM25`; static ASPECT protects two solo half
budgets, saturates deterministic syntactic facets in the spread half, merges
once, and returns unused capacity and wrapper savings to unchanged CC80 order.

This was executed previously on 871 label-blind questions and re-opened here
from the committed artifacts before the adoption design was locked. The source
and selection anchors observed in this exploration are:

| Input | SHA-256 |
|---|---|
| `src/analysis/tc009_convex_fusion_probe.py` | `a624b5a9dea820f37b1c8bf97ed6ac67871d0b8c9a4aa9703a73abd965393016` |
| `src/analysis/tc011_spread.py` | `3d7ce67360c9f1897559c987587535a3a199c1ba0de365a1ea75967fcbc20f80` |
| `src/analysis/tc007_allocation.py` | `97276ebca1da1b545fb518f514b974d9d7951449f28700dad9d3c4a3df23c007` |
| TC-009 CC80 frozen selections | `17e88abdc88547ec8abd96fb09ce8ae8e3f04c605d0081eed5f8cf837e2ad202` |
| TC-011 frozen selections | `9f4ae9abb57dfc76aecb3afdfcb62029056c10c6a412e42914d0c2294c2c9a0a` |

## Name-to-behavior checks

- **Latest 32 episodes:** the deployable store's episode unit is one completed
  user/assistant exchange. Its carried `_recency_window` returns exactly the
  final `min(32,N)` records in ascending conversation order.
- **CC80:** both score families are normalized per query before the fixed
  convex sum. It is not “80% of raw cosine plus 20% of raw BM25.” Every one of
  871 CC80 orders differed from dense-only and RRF in the source exploration.
- **Protected 50/50:** each arm has a maximum solo allowance of `B/2`; it is not
  a guarantee that half of final characters belong to each arm. At 32,000,
  ASPECT returned at least one CC80 candidate on 708/871 questions.
- **ASPECT:** it covers six exact facet families (entity, date, number, noun,
  event, relation). It is the static TC-011 mechanism, not either TC-012
  growing-cue variant.
- **Deduplication:** stable episode identity owns equality. The intended
  composition excludes recent identities from long-term admission and emits
  every episode at most once.
- **Budget:** `32,000` is the long-term retrieval ceiling only. Recent episodes
  are additive continuity context, so total returned characters may exceed
  32,000.
- **Rename:** `episodic-chat` is the installable distribution name. The Python
  import remains `episodic` in this release so existing stores, harness imports,
  and public callers do not undergo an unrelated namespace migration.

## Distributions and degenerate states

At 32,000 characters, static ASPECT selected 80–126 episodes (median 100), of
which 37–54 were spread admissions (median 46). Its final payload used
31,867–32,000 characters (median 31,973). Spread candidates had CC80 ranks
39–338 (median 126). The semantic seed contained 38–75 episodes (median 52).
All 871 traces had nonempty spread and reached a registered stop.

At 16,000, static ASPECT selected 39–68 episodes (median 49), with 19–29 spread
admissions (median 23), and used 15,871–16,000 characters (median 15,975).

Observed absorbing states are `no_complete_candidate_fits` and
`no_positive_marginal`; state changes only after an admitted complete episode.
The production boundary adds explicit behavior for traces the study rejected:
an empty or all-recent long-term pool returns no long-term episodes; a constant
dense or BM25 score family contributes an all-zero normalized component; and
ASPECT with no semantic seed returns CC80 unchanged. These cases are outside
the 871-trace parity population and must not alter any nondegenerate replay.

## Outcome boundary

The adoption is user-authorized despite the offline disposition. For context,
full CC80/static ASPECT complete-evidence totals were 771/749 at 16k and
819/810 at 32k. Those are availability counts on reused LoCoMo development
data, not reader accuracy or transfer. ASPECT therefore ships disabled by
default, exactly as authorized; no new effectiveness claim is made.
