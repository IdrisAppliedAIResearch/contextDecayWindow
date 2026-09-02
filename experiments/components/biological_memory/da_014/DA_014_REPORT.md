# DA-014 Reachable Gap Audit Report

**Status:** `CAPACITY_BLOCKER`
**Date:** August 30, 2026
**Standing:** post-outcome causal audit on spent LongMemEval

## Result

All 86 one-hop-reachable direct misses are accounted for: 7 rescues and 79
remaining misses, with zero `UNACCOUNTED` cases.

- `INITIAL_PAYLOAD_TOO_LARGE`: 49
- `MULTI_CARRIER_CONJUNCTION`: 12
- `PRIOR_CONSUMPTION`: 12
- `WRONG_MEMBER_CHOICE`: 6
- `RESCUED`: 7

The registered disposition is `CAPACITY_BLOCKER`. Initial payload size is the
modal class and occurs in every question type except preference.

## Mechanism

DA-013 creates a median 176 characters by reversible direct rendering. Rescued
items have median initial slack 353 characters. Initial-size misses have median
230; even an optimistic evidence-member cost exceeds available slack by a median
91 characters (p10 18.4, p90 222.6, max 355).

Prior-consumption cases are the smaller ordering opportunity: they begin with
median 343 characters but have 103 at carrier arrival. Wrong-member cases retain
median 295.5 at arrival. Conjunction cases need a median two carrier episodes
and begin with median 182.

This explains the linear-looking gains from earlier seed expansion. More seeds
expose more carriers, but only payloads below a narrow slack ceiling can enter;
additional candidates do not enlarge the context budget. The seven DA-013 gains
are the small singleton tail, not token flooding.

## Disposition

Do not pursue another evidence-blind ranker as the primary branch: at most 18
single-carrier cases are attributable to order or member choice, while 49 fail
before ordering can help and 12 require conjunction capacity.

The next upstream question is whether another **reversible, evidence-preserving**
representation can recover roughly 100-225 additional characters per question.
If not, the protected-slack branch has reached its practical ceiling and must be
validated as a small additive mechanism rather than expanded by tuning.

No selector, allocator, reader, fresh validation or adoption is authorized.

