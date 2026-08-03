# RD-001 Post-Result Decision

**Date:** August 3, 2026
**Design anchor:** `37d5bf2db418a0cc2e333faad47bb9c1965c28b4`
**Evidence commit:** `765f48e8098acdc0d02990308b6a04412ae90cb6`
**Decision:** **STOP - MEASUREMENT NOT IDENTIFIABLE**
**Part 2:** **NOT AUTHORIZED**

## Trigger

RD-001 recovered all 119 cosine ranks under E005's committed nine-query
embedding call. The pre-correlation join then found that the earlier rarity
artifact does not contain the episode-level variable the registered analysis
requires.

## Evidence

- The rank replay checks all 16 published points and passes with only the
  already-recorded turn-118 correction from rank 21 to 20.
- The recovered ordering contains the expected 76 fact-bearing episodes.
- The rarity artifact has three scores for each of six planted source episodes.
  It has no score for the other 70 fact-bearing episodes.
- The design names no primary rarity variant and no rule for aggregating phrase
  rarity to an episode carrying multiple target phrases.
- The six source episodes can be located and their length and phrase position
  reported, but six points are not the registered 76-episode measurement.

## Decision

No Spearman coefficient or confidence interval is computed. Choosing a rarity
variant, extending the score to 70 episodes, or defining an aggregation after
the decision rule was locked would add outcome-determining measurement choices.

No registered branch applies. Branch D assumes that cosine ranks are limited to
16; that premise is false after the successful full-rank recovery. Branch B
cannot be inferred from a coefficient that was never validly defined.

This is a post-result decision, not an amendment. The result had been opened
before the mismatch was confirmed, so the locked design remains untouched.

## Consequences

1. Chained retrieval remains unauthorized. No Part 2 branch, prior-art scan,
   mechanism code, or live run is opened.
2. The vocabulary-versus-retrieval alternative remains unresolved.
3. PAPER-001 pauses for a bounded correction: withdraw the claim that the
   correlation is runnable from already-committed ranks and phrases.
4. The recovered 119-rank inventory is valid descriptive evidence and may
   replace Figure 3's former 16-point rendering.
5. Any future rarity correlation requires a new prospective design naming the
   text unit, rarity variant, phrase-to-episode aggregation, interval method,
   and branch for incomplete joins.
