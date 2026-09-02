# DA-020 Protected Boundary Substitution Continuation

**Status:** `POST-STOP CROSS-CORPUS EXPLORATION PROTOCOL`
**Date:** August 30, 2026
**Parent:** DA-019 stop commit `e25a6d7c`
**Standing:** frozen continuation on spent NF-004 and LongMemEval
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Authorization and Scope

DA-019 stopped unopened because PF4 required a real duplicate rejection although
both parent edge streams deduplicate neighbors upstream. DA-020 does not repair
DA-019. It registers a successor with the exact already committed DA-019 rule,
selection and populations.

The only protocol correction is test placement: duplicate rejection is verified
on a synthetic duplicated edge, while real-data preflight verifies the upstream
no-duplicate invariant. No score, guard, threshold, order, payload, population,
activity count or selection may change from DA-019.

## 2. Frozen Treatment and Controls

The complete DA-019 Section 2 controls and six-step Section 3 boundary rule are
incorporated unchanged:

- NF-004 control is exact DA-010 benefit-order pair-then-turn at 970.
- LongMem control is exact DA-016 phrase-coded temporal pair-then-turn at 188.
- The incumbent is the last admitted linked action.
- Direct and every earlier linked action remain fixed.
- Traverse baseline skips in original order and allow at most one exchange.
- Require exact fit, preservation of every incumbent-unique original-question
  token, and candidate frozen-query cosine at least incumbent cosine.
- Preserve parent pair-first/frozen-singleton materialization and direct-derived
  phrase dictionaries.

The blind treatment must reproduce DA-019 selection SHA-256
`b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f`,
571 NF substitutions, 188 LongMem substitutions, and rejection counts fit
8,631, lexical 359, semantic 6,786. Any difference stops before evidence.

## 3. Endpoint and Decision

After blind reproduction, measure exact complete evidence delivery for all 1,098
NF-004 and 465 LongMem questions. Report per corpus: control/treatment totals,
gains/losses, exact paired test, group cells, changed evidence identities,
incumbent/replacement carrier accounting, costs, ranks and guard surfaces.

Report `PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL` only if treatment has at least
one gain, zero losses, and no negative conversation/question-type cell on both
corpora. Otherwise report
`NO_PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL`. Corpus-specific movement remains
descriptive and cannot select or tune another rule.

## 4. Preflight

- **PF1 Inputs:** verify DA-019 protocol, stop, code and blind artifact hashes;
  reproduce DA-010/DA-016 controls and all source seals.
- **PF2 Identity:** DA-019 unit tests remain exact. Add a synthetic duplicated
  skipped neighbor and require `DUPLICATE` rejection without changing output.
- **PF3 Ordering:** commit protocol, then commit byte-identical blind
  reproduction before evidence access.
- **PF4 Reachability:** require exact 571/188 activity and 8,631/359/6,786 real
  rejection counts; verify zero duplicate neighbor opportunities in both real
  streams and the synthetic duplicate test pass.
- **PF5 Keys:** preserve every DA-019 key and reject missing joins.
- **PF6 Reproduction:** require exact baseline actions, direct identities,
  charging and DA-019 selection SHA.
- **PF7 Determinism:** require byte-identical blind and opened replay.
- **PF8 Length:** retain all 1,563 questions and every baseline skip.
- **PF9 Surrogate audit:** structural dominance does not certify evidence
  preservation; both corpora are spent.
- **PF10 Live boundary:** no reader, latency, production or adoption claim.

Stop on any DA-019 selection change, real duplicate opportunity, failed
synthetic duplicate behavior, hash drift, direct/earlier-link mutation,
undercharge, nondeterminism or unexplained outcome. No guard relaxation,
alternative incumbent, refill, second swap or post-result tuning.

