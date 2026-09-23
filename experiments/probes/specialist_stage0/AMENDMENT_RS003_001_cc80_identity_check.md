# AMENDMENT_RS003_001 — CC80 instrument check: proxy replaced by exact identity

**Study:** RS003 Stage-0 (pre-registration
`RS003_STAGE0_PRE_REGISTRATION.md`, commit `d9edfc26`).
**Status:** recorded before any arm metric was produced; no result was
observed when this was written. Trigger found while running the registered
instrument checks for the first time.

## Trigger and evidence

The registered §3 instrument check for `CC80_8k` ("mean n-packed elements
must sit within ±2 of the committed mean n_cc80 (= 24.5)") failed: harness
mean 22.17 vs committed mean 24.35, diff 2.18. Diagnosis on all 120 items:

1. The frozen `rank_cc80` order in this harness reproduces
   `retrieve_long_term(read_policy='legacy_cc80', recency_window_n=0)`'s own
   `alloc.ranking.order` **exactly**, item by item.
2. The committed `n_cc80` counts selections of `retrieve_long_term` under
   `budget=8000`, which budgets its rendered episode tags — not raw joined
   element text. The committed 8k selections carry >8,000 raw chars
   (e.g. conv-26:107: 8,793), so the committed count is systematically
   ~2.2 elements higher than any raw-char 8,000 pack of the same order.

The registered ±2 tolerance was a proxy for "the ranking reproduction has
not drifted". The proxy is mis-scaled by the packer-accounting difference
the pre-registration itself acknowledged; the property it was meant to test
holds exactly.

## Change

`CC80` instrument check #5 becomes: for every item, exact equality of
(а) this harness's `rank_cc80` order against `retrieve_long_term`'s own
`ranking.order`, and (b) `len(alloc.selected_ids)` against the committed
`n_cc80`. Any single mismatch halts the harness.

## What this does not change

- No arm's pack rule, cap, population, metric, disposition bar, or control
  is altered. CC80 arms keep the registered order + registered skip-on-overflow
  raw-char packer at 8k/16k.
- `B_as_is`/`C_as_is` remain verbatim committed-block replays.
- The change makes the check strictly stronger (exact vs ±2 proxy); it
  cannot make any disposition easier.
