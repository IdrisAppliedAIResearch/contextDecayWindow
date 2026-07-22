# Decision: Study 004 Association Decoupling

**Status:** Accepted and locked for Study 004

**Date:** July 21, 2026

**Author authorization:** Muzaffer authorized Study 004 to begin and this decision to be recorded on July 21, 2026.

## Finding

Study 003 scored Novelty and Association against the same global LTM centroid. The two scores were therefore complements, which capped their combined weighted contribution at 0.35:

```text
0.35N + 0.20(1 - N) = 0.20 + 0.15N
```

Once LTM was non-empty, the weighted promotion route was structurally near-unreachable. Zero weighted promotions occurred after the first batch; all nine later promotions used all-or-nothing bypasses.

## Decision

Adopt Option A. Novelty remains unchanged. Association becomes the maximum cosine similarity between the candidate episode and the canonical per-topic centroids present in the LTM batch snapshot:

```text
A(e) = max over t in LTM_topics of cosine_similarity(embedding(e), centroid(t))
```

Stored topic labels are resolved through the current canonical consolidation mapping before grouping. Each canonical topic contributes one centroid, including one-member groups. The centroids are frozen for the entire promotion batch and recomputed only after batch writes complete. Empty LTM yields Association = 0.0.

## Bypass scope

Association is excluded from the all-or-nothing bypass. A high Association score means the candidate closely resembles knowledge already stored in LTM, so it is a redundancy signal rather than the high-intensity encoding represented by the bypass. Novelty, Repetition, and Emotional remain bypass-eligible; Association contributes only through the weighted route.

## Rejected alternatives

- **Rebalance weights:** rejected because changing weights would alter more of the standing filter design and would treat the symptom without separating the two constructs.
- **Re-register Association as a bypass detector:** rejected because high Association identifies near-duplication of existing LTM knowledge, not an independently sufficient reason to promote.

## Known degeneracy

With exactly one canonical topic in LTM, its per-topic centroid equals the global centroid, so Novelty and Association remain complements for that batch. The decoupling takes structural effect only when LTM contains at least two canonical topics; Study 004 therefore interprets route behavior from batches three and later separately.

## Consequence

The maximum possible combined Novelty-plus-Association contribution rises from 0.35 to 0.55 when multiple topic centroids permit the scores to vary independently. All weights and thresholds remain unchanged, and whether the weighted route actually fires remains observational.
