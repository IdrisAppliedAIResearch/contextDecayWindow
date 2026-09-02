# DA-014 Scratchpad

## Inherited Evidence

- DA-013 compact protected temporal fallback transfers 164->171 complete on
  spent LongMemEval, +7/-0, p=.015625.
- The fixed one-hop edge set can complete 250, leaving 79 reachable misses after
  temporal allocation.
- All seven gains are singleton turns. DA-004 transfer scoring collapses to the
  exact temporal allocation and is dropped.

## Branch Rule

Audit the 79 misses exhaustively before proposing another mechanism. Carry the
modal mechanical blocker only if accounting is complete and deterministic. If
blockers are mixed, backtrack to the protected compact-link architecture and
seek a fresh validation surface rather than tuning LongMemEval.

## Result

- Complete accounting: 86 reachable direct misses = 7 rescued + 79 blocked;
  zero unaccounted.
- Classes: initial payload too large 49, multi-carrier conjunction 12, prior
  consumption 12, wrong member 6, rescued 7. Status `CAPACITY_BLOCKER`.
- Initial-size misses have median initial slack 230 chars and optimistic minimum
  deficit 91 chars (p10 18.4, p90 222.6, max 355). Rescues have median 353.
- Prior-consumption starts at median 343 slack and arrives with 103. Wrong-member
  cases retain 295.5. Conjunctions need median two carriers and start at 182.
- The ceiling is upstream representation capacity. Ranking/member choice jointly
  own only 18 cases; another selector sweep is not the main branch.
