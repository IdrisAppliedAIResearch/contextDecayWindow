# Chronological timeline adoption and arc closeout

Date: 2026-09-19. Engineering plan: **1c024e70**, continuity clarification
**fbd5cd42**. Part 1: **5e1431ae**. Package parity before activation: **bc7ffb39**.
Disposition: **authorized product adoption; exploratory study arc closed**.
This is not a new registered effectiveness result. No historical score changes.

## Product decision

The user selected the chronological relevance timeline for the deployed library,
paused the proposed extra LLM step, and explicitly retained last-32 continuity
by default with an off toggle. Version 0.3.0 implements this composition:

1. Scan eligible complete exchanges using raw query cosine >=0.48.
2. Union the latest 32 eligible exchanges by default; `recency_window_n=0`
   disables continuity. No character or item cap applies to relevant evidence.
3. Protect an explicitly supplied anchor, deduplicate, then render all selected
   original exchanges in ascending source-turn order.
4. Apply an inclusive source horizon only when the caller supplies one. It
   restricts continuity too. There is no natural-language anchor inference.

The existing append store, embedding identity contract and XML escaping remain.
No contextual embeddings, max-product traversal, DA fusion or generative planner
are promoted. Legacy CC80/ASPECT is explicitly available; old stores require a
deliberate configuration migration to use the new policy. Failed embedding
validation cannot persist a requested config migration.

The optional explicit anchor API generalizes a previously synthetic interface;
it does not establish automatic binding of names, events or references. Source
order is recording order, not an inferred event timeline. Later testimony can
be necessary, so a historical event question alone is not grounds for a cutoff.

## What the arc found

| Evidence | Observation | Supported reading |
|---|---|---|
| [Same-retrieval chronology](../../probes/temporal_da_fusion/CHRONOLOGY_REPORT.md) | Before-event original/no-recency/chronological-no-recency: 5/12, 5/12, 8/12; 3 gains, 0 losses | Chronological presentation helped this small exposed synthetic sample. Recency removal alone did not. |
| [Relevance timeline](../../probes/temporal_da_fusion/RELEVANCE_REPORT.md) | All required before evidence 109/128→128/128 with anchors; fresh reader 8/12→11/12 | Removing packing caps recovered known evidence; one complete-evidence answer regressed. |
| [Full E reader](../../probes/temporal_da_fusion/FULL_E_REPORT.md) | Before 106/128; latest and absence 32/32 each | A single-arm native-thinking-off reader result, not availability alone. All 22 before misses had complete annotated evidence. |
| [Prefix removal](../../probes/temporal_da_fusion/POST_REVIEW_REPORT.md) and [preservation](../../probes/temporal_da_fusion/PREFIX_106_REPORT.md) | 22/22 prior misses recovered; 104/106 prior correct retained; combined 126/128 | Known-anchor source restriction helped synthetic before-event answers. Two sequential diagnostic batches, 22 gains and 2 losses; not chronology-only or independent confirmation. |
| [Natural timeline30](../../probes/locomo_timeline30/REPORT.md) | Broad 13/20; additional temporal 5/10; annotations complete 16/20 and 10/10 | Natural questions expose both retrieval and reader failures. The quoted-anchor grammar does not transfer. |
| [Unified subset](../../unified_contextual_memory/REPORT.md) | C0 384/566, C1 399/566, 27 gains/12 losses; annotation delivery 493→516/565 | Chronology and captions are shared, so this contrast cannot identify their effects. Nonrandom stopped subset, same-model judging, no full-population claim. |
| [Unified diagnosis](../../unified_contextual_memory/PROBE_001_REPORT.md) | Path attenuation excludes many missing carriers; date/list judging inconsistent in both directions | The 15-answer margin is not precise enough to justify a broad architecture claim. Locked scores remain unchanged. |

There is evidence for a useful deterministic timeline and evidence that delivery
does not guarantee answer correctness. There is no established general solution
to indirect anchors, multi-hop evidence completion, or reliable stopping based
on completeness. The .48 cutoff is a carried operating point, not an optimized
or universal relevance threshold.

The default continuity union is a product decision, not the no-recency research
arm. Neither its reader accuracy nor its latency has been newly measured. Earlier
0.2 HH-003 benchmark scores must not label the 0.3 default. No new reader calls,
judge calls, rescoring, package-registry publication or PR merge occur here.

## Verification

[Part 1](timeline_artifacts/part1.json) hashes all seven input files. E selections
range 106–113 records (median 108), with median 84,627 serialized characters;
LoCoMo selections range 0–323 (median 79), including two empty selections and
no full-store selections. This characterizes the saved no-recency configurations.

[Parity](timeline_artifacts/parity.json) reproduces **2,306** selections with zero
mismatches: 192 E timelines, 128 E prefixes and 1,986 LoCoMo selections. E payloads
are byte-identical; LoCoMo payload hashes use the original retained source adapter,
not the public store's user/assistant XML. Same-count wrong-identity and altered
payload controls are rejected. The passing gate was committed before activation.

PF1/PF2/PF5/PF6 are covered by those hashed artifacts and boundary fixtures.
PF3 is the commit order above. PF4 covers empty/all-selected and threshold edges;
PF7 covers repeatability and context-call database purity. PF8/PF9 constrain these
checks to port/API correctness, not reader efficacy. PF10 is the scoped live
evidence above. No effectiveness bar is added after results.

**217 tests pass** across the timeline release, CC-002 through CC-007 and
HH-003 suites ([test output](timeline_artifacts/tests.xml)). Public API checks
cover default continuity and opt-out, source-order union, threshold boundaries,
no-cap delivery, explicit anchors/horizons, byte-identical reopening, store purity,
old serialized configs and migration failure safety. Historical public consumers
are explicitly pinned to `legacy_cc80` to preserve their old behavior.

The wheel built and installed offline; an isolated interpreter loaded it from
its own `site-packages`. Two fresh processes returned the same evidence SHA;
continuity opt-out passed ([wheel smoke](timeline_artifacts/wheel_smoke.json)).
These tests use deterministic fake embeddings; no model or reader is called.
`uv lock --check --offline` passes. [Activation record](timeline_artifacts/activation.json)
records the package and test hashes. The wheel build is local, not a registry
publication. Historical benchmark scores, registrations and answer artifacts
are unchanged, so no numerical ERRATA entry is required.

## Closed and paused work

The chronological study arc is closed at its existing exploratory evidence.
The unified subset remains complete and the unfinished full run stays stopped.
The one-call planner design is **paused, not implemented**. A future research
decision can reopen those questions explicitly; installing this product release
does not restart them. Historical registrations and sealed outputs are preserved.
