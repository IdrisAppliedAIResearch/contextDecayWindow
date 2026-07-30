# AS-001 Amendment 001 - Uncommitted Run Database

**Date:** 2026-07-29
**Authorization:** The author explicitly allowed amendments for these follow-up
documents.
**Timing:** Raised after the AS-001 decision rule was committed and before any
post-fix packing output was generated or opened.

## Trigger and Evidence

The corrected Tier 6 mechanism seal lists `study.db`, but `.gitignore` excludes
`*.db` and the file is absent from every git commit and from Git LFS.
`git show HEAD:<run>/study.db` therefore fails even though a local checkout copy
exists. The canonical run tree contains 266 tracked files; the seal describes
265 mechanism files plus the seal and scoring surface, which would require 267.

A local ignored database cannot be an evidence source under AS-001's
committed-artifact rule.

The canonical committed `logs/turns.jsonl` preserves, for every turn, the
stored episode ID, topic label, user message, and assistant message. The
canonical `logs/context_match.jsonl` preserves the ordered 32 Q4 N candidate
IDs. The committed runner fixes each episode embedding input as:

```text
User: USER_MESSAGE
Assistant: ASSISTANT_MESSAGE
```

## Change

1. Do not read the ignored local `study.db`.
2. Reconstruct the 32 candidate episode records by joining the canonical
   context-match IDs to canonical turn-log `stored_episode_id` values.
3. Recompute candidate embeddings with the SHA-verified carried embedding
   model and the committed runner input format. This is deterministic
   embedding replay, not generative inference.
4. Require the recomputed turn-55 cosine to match the already committed
   `0.16612689197063446` value within `1e-7`.
5. Report the historical run seal as `FAIL_MISSING_COMMITTED_DB`; do not relabel
   it PASS. Separately verify that every tracked sealed mechanism blob matches
   its listed SHA-256 and that checkout-only newline differences normalize to
   the canonical blob content.

## Rationale

This repairs source provenance without changing candidate identity, order,
content, rendering, budget, or the binding decision rule. The cosine
reproduction is an independent check that reconstruction matches the original
embedding path.

## Exclusions

This amendment does not commit or modify the local database, edit the historical
seal, waive a mismatch, change any score, or authorize inference. If any
candidate cannot be reconstructed or the turn-55 cosine does not reproduce,
AS-001 stops without a verdict.
