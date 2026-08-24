# CC-007 — episodic-chat read-path adoption report

**Status:** PASS; deployed engineering adoption  
**Date:** 2026-08-24  
**Pre-registration commit:** `293df2d0649907451099d3da41d0c2f0ee576ead`  
**Preflight artifact SHA-256:** `78e5536e875df79b106a78f2fdc2899964653c300b3da1ce7355be7ce43e184`  
**Post-activation artifact SHA-256:** `f57d6a14e5bd52b0754457785e290fe326d72a4a41755c44484a852b7562faf6`

## Outcome

The installable distribution is now `episodic-chat` version `0.2.0`, retaining
the stable Python namespace `episodic`. `EpisodeStore.context()` now returns:

- every one of the latest 32 completed user/assistant episodes as additive
  continuity context;
- a separately budgeted long-term block, default 32,000 characters, ranked by
  exact CC80 (`0.8` per-query normalized dense cosine plus `0.2` per-query
  normalized BM25);
- stable-identity deduplication between recent and long-term context; and
- optional frozen static ASPECT, disabled by default, with the tested 50/50
  protected allocator and unused capacity returned to CC80.

The old cosine-threshold/A3 path remains private only so registered historical
checks continue to run. It no longer backs the public store method.

## Independent 1:1 verification

The pre-activation verifier compared package-only mechanism output against
committed TC-009 and TC-011 frozen artifacts on all 871 questions:

- 871 CC80 complete-store orders;
- 1,742 CC80 selected-identity sequences and payload digests at 16k/32k; and
- 1,742 static-ASPECT selected-identity sequences and payload digests at
  16k/32k.

Result: **4,355/4,355 exact groups, zero mismatches**, 2,236 retained-vector
cache hits, zero misses, zero new embedding calls and zero LLM/generative
calls.

The gate was not ceremonial. Its first execution found 121 mismatched groups
despite matching aggregate selection distributions. Two port drifts caused it:

1. vectorized float32 row normalization differed from TC-005's one-vector-at-a-
   time normalization by up to about `6e-8`, changing one CC80 tie and
   downstream ASPECT choices; and
2. reconstructing one empty-assistant candidate with an added trailing newline
   changed spaCy's entity parse.

The implementation now preserves per-vector normalization and accepts the
exact original searchable text when an adapter supplies it. The frozen source
was not changed.

After public activation, a separate verifier reconstructed final contexts from
the frozen CC80 orders without calling the new composition function: remove
the latest 32 identities, exact-pack the remainder to 32k, then render recent
plus retrieval. Result:

- **871/871 final payloads byte-identical**;
- exactly 32 recent episodes on every trace;
- zero duplicate deliveries;
- zero long-term budget breaches; and
- 871/871 final payloads above 32k, positively demonstrating that recency is
  additive rather than silently charged to retrieval.

## Package and regression gates

- Clean isolated install reports distribution `episodic-chat 0.2.0` and imports
  `episodic`; the base install does not require spaCy.
- ASPECT dependencies are an optional `aspect` extra and missing parser/model
  failures are loud; there is no fallback parser.
- Focused CC-002–CC-007 integration gates passed after updating the one
  intentional old assertion from total-budget ceiling to retrieval-budget
  ceiling.
- Full repository suite: **2,267 passed in 109.20 seconds**.
- Root and package documentation, deployed settings, diagram, lockfile and
  AGENTS digest now describe the activated path.

## Claim boundary and residuals

This report certifies implementation identity, composition, budget semantics,
deduplication, packaging and regression safety. It does not claim that static
ASPECT beats CC80—TC-011 measured the opposite, which is why it defaults off.
It also does not establish live reader benefit, enterprise-benchmark transfer,
concurrency safety, or latency of the new full-store ranking path. Those are
separate measurements.
