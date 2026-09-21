# AF-PRE-002 Part 1 RESULTS (2026-09-20)

Rule and bars frozen in `AF_PRE_002_PLAN.md` (commit `5205a3f3`) before this file scored anything. Characterization surfaces only.

## S1 — E 17-anchor fidelity: **17/17**
Event gate + quoted-name match recovers all 17 anchors that LEX/BM25/QWEN-BI/CE all missed top-1 (0/17 each). Machinery valid: the anchor is exactly the event turn, and it *is* lexically findable — even on templated data, this is the first method of any kind to identify these anchors at top-1.

## S2 — H1 (anchor-ness is lexically visible): **SUPPORTED**
Anchor event rate **53.5%** vs non-anchor **29.3%** → **+24.2 pp** (bar: ≥ +15). Anchors are disproportionately event turns. Dominant discriminating families (anchor share vs base): TEMPORAL_SHIFT, MOTION, STATE_CHANGE, ANNOUNCE; EVENT_NOUN is the noisy one (671/2291 non-anchors).

## S3 — H2 (event feature helps the ranking): **NOT SUPPORTED**
HYBRID = BM25 × (1 + family_count): **17/120 vs BM25 29/120**, net **−12**, p = .012 — significantly *worse*. EVENT-ONLY: 1/120.

Per category: cat-2 (temporal) hybrid **10** vs BM25 8 (anchor event rate 82%) — the only gain; cat-4 (single-hop, preferences/answers) hybrid **7** vs BM25 21 (anchor event rate 39%) — the entire loss.

## Reading
H1 and H2 come apart cleanly. Event-ness *identifies where anchors live* (coverage) but not *which turn answers* (ranking): a multiplicative event prior lets loud-but-wrong event turns displace answer-bearing turns — 16 items BM25 got, hybrid lost. The temporal-category sliver is the honest positive: event features help precisely where the question is itself an event-recovery query, and hurt where the gold is an answer-shaped preference.

Per the registered bar, **no fine-tuning Part 2 opens on this evidence**. What was actually tested is one naive combinator; killing the concept would require showing no combinator works (e.g., event-gated retrieval feeding a reranker rather than score multiplication), and any such test is a new registered probe, not an amendment of this one. The strongest standing result stays AF-PRE-001's: event anchors defeat every answer-seeking retriever, and only a rule that ignores answer-tokens and looks for the event itself (S1) finds them.

Artifacts: `artifacts/event_probe_results.json`.
