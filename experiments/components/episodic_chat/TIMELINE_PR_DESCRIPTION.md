## Summary

Release **episodic-chat 0.3.0** with chronological relevance retrieval, retain optional last-32 continuity, and close the chronological study arc. The previous library default used budgeted CC80; the timeline previously existed only in experiment code. The proposed extra LLM step is paused.

## What changes in the library

- **Retrieval:** include every complete exchange with raw cosine similarity **>=0.48**, without a character or relevance-item packing cap.
- **Continuity:** include the latest **32 completed exchanges by default**. Set `EpisodicConfig(recency_window_n=0)` to disable it.
- **Presentation:** deduplicate the combined evidence and present it in chronological source order.
- **Boundaries:** accept an explicit caller-supplied anchor and inclusive source horizon. The horizon also restricts continuity; no anchor is inferred from natural language.
- **Compatibility:** retain `read_policy="legacy_cc80"` for the previous budgeted behavior. Existing stores require deliberate migration to the new policy.

The package adds no generative retrieval call or contextual/traversal fusion. Applications remain responsible for checking reader prompt capacity because the returned evidence is uncapped.

## Results: chronological versus original order

The direct ordering probe used **the same selected retrieval records and source text**, with 12 synthetic “immediately before” questions and four latest/absence guard questions. It separated removing continuity from changing presentation order.

| Reader configuration | Before-event answers correct | Latest-setting guards | Absence guards |
|---|---:|---:|---:|
| Original order, with last-32 continuity | 5/12 (41.7%) | 2/2 | 2/2 |
| Original order, continuity removed | 5/12 (41.7%) | 2/2 | 2/2 |
| Chronological order, continuity removed | **8/12 (66.7%)** | 2/2 | 2/2 |

**Ordering improved correctness by 25 percentage points: three gains and zero losses.** Removing continuity alone produced no correctness change. Between the two no-continuity arms, evidence membership and content were unchanged; this was a reader benefit from presentation, not improved retrieval availability. All four remaining before-event misses lacked complete required evidence.

This was an exploratory probe on 16 exposed synthetic questions, one seed, with native thinking off in every arm. It does not establish a population accuracy rate. **Chronological presentation with continuity enabled was not tested in this comparison.**

[Chronology report, per-question answers and raw-artifact references](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/blob/807e95b9/experiments/probes/temporal_da_fusion/CHRONOLOGY_REPORT.md)

## Later results: retrieval expansion and explicit cutoffs

These follow-ups kept chronology and changed other parts of evidence delivery. Their gains should not be attributed to ordering alone.

| Follow-up | Reader result | Interpretation |
|---|---|---|
| Remove packing caps; use cosine >=0.48 plus known anchors | 8/12 → **11/12**; four gains, one loss | More necessary evidence reached the reader; chronology was fixed in both arms. |
| Larger single-arm synthetic evaluation | **106/128** before-event answers correct; latest and absence each 32/32 | All 22 remaining before-event errors had complete annotated evidence. |
| Remove records after the explicit review anchor | 106/128 → **126/128**; 22 gains, two losses | Combined across two diagnostic batches: prior misses, then prior correct answers. Not independent confirmation or an ordering-only effect. |

Sources: [relevance comparison](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/blob/807e95b9/experiments/probes/temporal_da_fusion/RELEVANCE_REPORT.md), [larger reader run](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/blob/807e95b9/experiments/probes/temporal_da_fusion/FULL_E_REPORT.md), [miss recovery](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/blob/807e95b9/experiments/probes/temporal_da_fusion/POST_REVIEW_REPORT.md), [preservation check](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/blob/807e95b9/experiments/probes/temporal_da_fusion/PREFIX_106_REPORT.md).

**Adoption scope:** keeping last-32 continuity on by default is the user's product decision. This exact default composition has no new live-reader score. The synthetic results do not establish general natural-language anchor resolution, and historical 0.2 benchmark scores do not describe this release. The combined contextual/traversal experiment in #98 shares chronology across both arms and cannot isolate its effect; that configuration remains experimental.

## Verification

- **2,306 exact historical selection/payload checks**, with continuity disabled: 192 timelines, 128 prefixes and 1,986 LoCoMo cases.
- **217 passing tests** covering public API behavior, continuity on/off, chronological deduplication, boundaries, migration, persistence and legacy compatibility.
- Offline wheel build and installation; identical evidence across fresh processes; installed-package continuity toggle verified.
- Offline lockfile check passed. No new reader, judge or encoder-model calls for this release.

## Documentation and closeout

Root/package README, architecture diagram, deployed settings, migration notes, reports, handoffs, version metadata and lockfile are updated. Historical registrations and scores remain unchanged; no numerical ERRATA is required. The full inference run remains stopped and the extra LLM planner remains paused.

This PR is stacked on #98. It adopts the chronological foundation, not that experiment's contextual/traversal additions. No PR merge or package-registry publication is included.

[Adoption report and verification artifacts](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/blob/807e95b9/experiments/components/episodic_chat/TIMELINE_REPORT.md) · [Migration notes](https://github.com/IdrisAppliedAIResearch/contextDecayWindow/blob/807e95b9/episodic/CHANGELOG.md)
