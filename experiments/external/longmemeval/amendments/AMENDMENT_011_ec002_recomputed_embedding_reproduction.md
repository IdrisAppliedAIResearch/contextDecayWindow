# EC-002 Amendment 001 — Reproduction under recomputed embeddings

**Study:** EC-002 K-first packing diagnostic  
**Registration anchor:** `8c75d7e22258c56cb6b422c0dfcc013cddd65613`  
**Status:** AUTHORIZED AFTER A0 BLOCKED AND BEFORE A1  
**Authorization:** Program author, August 5, 2026

## Trigger and evidence

The registered A0 byte-exact replay gate failed after all 500 questions were
processed. Source, configuration, model-artifact, and original-artifact
integrity checks passed, but:

- all 500 report comparisons failed because a rebuilt `EpisodeStore` assigns
  fresh UUIDs and the report compared `dropped_ids` directly;
- one otherwise identical score row moved one evidence-session rank from 21
  to 20;
- one question delivered one additional coverage-selected episode while its
  recall and availability outcomes remained unchanged; and
- the original EC-001 embedding cache was not retained and is unrecoverable.

The first failure compares generated database identities rather than episode
content. The remaining differences show that pinning the embedding model
artifact does not make freshly recomputed vectors bit-identical to the
unavailable EC-001 vectors.

## Change

A0 is relabeled a **reproduction under recomputed embeddings**, not a
byte-exact replay. Its binding gate is replaced by these mechanical checks:

1. Represent every episode identity used for cross-run comparison by the
   SHA-256 of its role-delimited user and assistant content, with occurrence
   position included to disambiguate repeated identical exchanges. Generated
   store UUIDs are never compared across runs.
2. Require identical delivered recency and K episode identities on all
   500 questions.
3. Require identical recall and availability outcomes on all 500 questions.
4. Permit each annotated evidence-session rank to move by at most one
   position relative to EC-001.
5. Permit coverage-selection differences on at most 2 of 500 questions,
   provided that for each:
   - recency and K episode identities are unchanged;
   - every differing delivered episode is coverage-selected;
   - the delivered character count does not exceed 32,000;
   - recall and availability outcomes are unchanged; and
   - the instance and every differing field are disclosed in full.
6. Three or more questions with coverage-selection differences fail A0.
7. Dataset, embedder artifact, configuration, original-artifact hashes, and
   source integrity must still pass.

The aggregate summary comparison uses the same registered recall and
availability outcomes plus the amended one-position rank tolerance. It does
not require byte identity for the rank-distribution array.

## Rationale

Generated UUID equality is not the property the report gate intended to
certify; stable episode content identity is. The original cache cannot be
recovered, so a claim of bit-exact EC-001 replay would be false. The amended
gate holds recency, K delivery, recall, and availability rigid while bounding
the only permitted coverage drift mechanically. It does not assert or infer a
cause for a difference.

The two-question cap is an author-specified bound, not an implementation-chosen
materiality threshold. The amendment changes no retrieval threshold, budget,
packing order, A1 outcome criterion, or production-promotion rule.

## Record limitation

EC-001 is reproducible in aggregate under the amended checks but is
permanently unreplayable at bit granularity because its original embedding
vectors were not retained. A future library cache contract can guarantee
vector identity only for runs created after that contract lands; it cannot
repair the EC-001 historical record.

This limitation must be stated in the EC-002 report and in
`paper/PAPER_001.md` section 7 if A0 passes and the diagnostic proceeds.

## Exclusions

- No EC-001 locked registration, score, mechanism log, or run artifact is
  edited.
- No A1 result has been produced or inspected.
- No change to K, N, A3, the 32,000-character budget, or packing priority.
- No inference, reader answer, rater pass, or adjudication.
- No vector-cache library implementation is included in EC-002. That
  correctness change requires its own registration, branch, and pull request.
