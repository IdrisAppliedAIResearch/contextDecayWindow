# Amendment 002 - Deterministic Embedding Replay

**Date:** 2026-07-29
**Applies to:** DR-001 at `094cbea2`
**Status:** LOCKED by the commit that first adds this file

## Trigger and evidence

DR-001 section 6 requires replaying the Study 007 probes over the registered
budget sweep after serialized costs change. The committed retrieval-budget logs
contain scores and identities only for admitted candidates. They do not contain
the query embeddings or scores for every unadmitted candidate, so the post-fix
frontier cannot be reconstructed from logged values alone.

The preserved stores contain every candidate embedding, and the exact carried
embedding model is locally available and hash-registered by the retrieval
bakeoff.

## Change

Authorize deterministic offline embedding replay for the registered probe query
texts using the carried Qwen3-Embedding-0.6B Q8_0 artifact. The replay must:

1. Verify the model SHA-256 against the carried constant before use.
2. Use one CPU thread and the existing deterministic provider.
3. Hash all source artifacts before and after.
4. Record the query text hashes and resulting vector hashes.
5. Make no generative model call and create no conversation response.

The same authorization applies to Study 010 Q13/Q14 re-selection if needed to
evaluate the exact-cost production frontier.

## Rationale

This repairs an evidence-availability blocker. It restores the scores that the
historical runtime computed but did not log for rejected candidates. It does not
change a query, candidate, model, parameter, gate, or decision criterion.

For this component record, "no inference run" continues to prohibit generative
conversation inference. A deterministic embedding replay is an offline
measurement operation, not a new study arm or run.

## Exclusions

No language-model generation, scoring, tuning, new query, new candidate,
selection change, or historical artifact mutation is authorized.

## Authorization

The author authorized amendments on 2026-07-29. This amendment is raised before
the post-fix frontier is computed.

