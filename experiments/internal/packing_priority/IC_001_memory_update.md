# IC-001 memory update

- Every study in this program's record ran recency-first. IC-001 is the first
  measurement of what that cost on the internal corpus.
- The replay needed no vectors at all: both arms consume the deployed run's
  committed `n_candidate_ids` and `k_candidate_ids` from `context_match.jsonl`,
  so nothing is re-ranked and no model or embedding call occurs. That is
  stronger than EC-002's cache reuse, and it is why the registered CC-006 cache
  clause is met by substitution rather than by the registered mechanism — no
  such cache exists for this corpus (Amendment 001, authorized August 6, 2026,
  and enforced: a phase refuses to run unless the amendment says AUTHORIZED).
- Under the deployed order the K path delivered **zero episodes and zero
  characters at 8 of 8 probes**. Recency consumed the whole budget every time.
  The similarity path was computing candidates and being denied window space,
  exactly as EC-001 found externally.
- Q11 rose 6/17 -> 7/17, one gain and zero losses. The eight targeted probes
  rose 14/21 -> 18/21: four gains, zero losses. Q5 and Q6 went 0/2 to 2/2.
  Branch A.
- K-first delivered **more episodes for fewer characters** at Q11: twelve in
  31,863 against eight in 31,946. Admitting two small similarity hits first
  left room the deployed walk had already spent on one large episode. A
  fill-order change is not only a reprioritization; it changes how much fits.
- The LV-001 displacement did not reproduce. B1's Q11 window *gains* the turn-1
  and turn-2 episodes B0 dropped — the formatting-rule plants LV-001 reported
  missing live. Recency-first was the order dropping them.
- Aggregate totals concealed the change: both arms delivered exactly 71 recency
  episodes across the eight probes, in different compositions. Paired
  per-probe counts were the only way to see it.
- The deployed configuration has no coverage tier. It is recency-32 plus
  `K = 0.48`, so IC-001 tests a two-tier instance of the registered three-tier
  order.
- Branch A makes the section 6 recalibration conditions live, not satisfied.
  Availability is not a verdict; no verdict changes without a registered live
  run, and the graveyard entries that failed upstream of delivery stay closed.
