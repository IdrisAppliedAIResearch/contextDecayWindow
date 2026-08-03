# RD-001 - Lexical Rarity Diagnostic Report

**Pre-registration SHA:** `37d5bf2db418a0cc2e333faad47bb9c1965c28b4`
**Implementation SHA:** `7cbdb2c099f60722c60934cda16bfc633a71c1e8`
**Evidence SHA:** `765f48e8098acdc0d02990308b6a04412ae90cb6`
**Outcome:** **STOP - MEASUREMENT NOT IDENTIFIABLE**
**Registered branch:** **NONE**
**Part 2:** **NOT AUTHORIZED**

## Outcome

The carried embedder was available and passed its SHA-256 assertion. Under
E005's committed nine-query batch, RD-001 recovered the complete 119-episode
cosine ordering. A byte-identical rerun passed. The replay also reproduced all
16 previously published rank checks, including the already-recorded correction
of turn 118 from rank 21 to rank 20.

The registered correlation cannot be computed from the promised inputs. The
ordering contains 76 fact-bearing episodes, but the prior rarity artifact
scores only six of those episodes. Each has three variants
(`rarity_mean`, `rarity_max`, and `rarity_sum_per_word`), with no registered
primary and no phrase-to-episode aggregation. Seventy fact-bearing episodes
have no unchanged committed rarity score.

No Spearman coefficient, confidence interval, or scatter claiming the
registered population was produced. This is not a null result and not Branch B.
Branch D also does not apply because its n=16 rank premise was removed by the
successful full-rank replay.

## Six-Plant Inventory

The six committed plant rows map to source turns 56, 60, 61, 62, 101, and 102,
at cosine ranks 27, 30, 114, 91, 44, and 23. Their source spans are present
verbatim. Episode lengths and phrase positions are recorded in
`artifacts/rd001/plant_rank_inventory.csv`. These six descriptive points do not
substitute for the registered 76-episode correlation.

## Integrity

- Zero inference or generation calls.
- One carried embedding batch, under the registered E005 call shape.
- Full rank count: 119.
- Fact-bearing count: 76.
- Published-rank replay: PASS.
- Input hashes unchanged before and after.
- Independent rerun: byte-identical.
- No rarity score recomputation.

## Paper Disposition

PAPER-001 is revised rather than abandoned. The recovered full ordering improves
Figure 3, but the paper now states that RD-001 exposed a measurement-unit
mismatch and left the corpus-artifact hypothesis unresolved. The paper cannot
claim that the correlation is runnable from already-committed inputs.

## Close Checklist

- [x] Report records the pre-registration SHA.
- [x] Full rank and feasibility artifacts committed.
- [x] Post-result decision committed separately; locked design unchanged.
- [x] PAPER-001 Sections 5.5.1, 8.5, 8.8, Figure 3, and conclusion corrected.
- [x] Claim table and evidence index updated.
- [x] Root README and AGENTS digest updated.
- [x] Retrieval ledger and memory updated.
- [x] ERRATA reviewed; no published score or historical number changed.
- [x] Pull request opened: PR #36.
