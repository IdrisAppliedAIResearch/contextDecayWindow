# IC-001 Amendment 001 — No vector recomputation, no cache to bind

**Study:** IC-001 internal packing-priority counterfactual
**Registration anchor:** `7b578c54aa5643fbc691ed679aab95e531a9e962`
**Status:** AUTHORIZED
**Authorization:** Program author authorized the substitution, August 6, 2026,
after the proposed text and both arms' results were presented. The proposal was
recorded before any arm ran, so the substitution is visible in git order rather
than discovered in the report; this authorization is a separate commit ahead of
the runs that rely on it.

## Trigger and evidence

Section 3 of the registration requires the replay to run "read-only against
the CC-006-protected cache, with the file and canonical content hashes
asserted before and after."

No such cache exists for the internal corpus, and none can be created without
the model calls the same section forbids:

- CC-006's protection "begins with retained caches." The only adopted cache is
  EC-002's `ec002_exact_solo_embeddings.db`, 96,585 entries over the
  **LongMemEval** corpus. It contains no internal-corpus text.
- The only internal-corpus vector artifacts are the gitignored span-embedding
  SQLite files under `experiments/surveys/retrieval_bakeoff/cache/`. They are
  untracked, carry no recorded file or canonical content hash, and are not
  CC-006 caches.
- The Study 006/007 lineage predates CC-006 entirely, so the corrected Tier 6
  run retained no hashed vector cache.

The requirement is unreachable as written. It is also unnecessary here: this
replay needs no vector at all.

## Change

The cache clause is satisfied by a **stronger** condition, asserted in its
place:

1. Both arms consume the deployed run's **committed candidate identities**
   from `logs/context_match.jsonl` — the `n_candidate_ids` and
   `k_candidate_ids` the deployed run recorded at each probe turn. No cosine
   is recomputed, no ranking is re-derived, and no vector is read.
2. That log's SHA-256, and the SHA-256 of `study.db`, the committed A0
   baseline, and the AR-001 achievability artifact, are asserted before and
   after every phase in `source_integrity.json`.
3. `no_model_call_audit.json` records zero model calls, zero embedding calls,
   and zero cache misses, and mechanically asserts that the embedding provider
   loaded no model and that the carried embedder module was never imported.

## Rationale

The clause exists to prevent recomputed embedding from moving a rank or a
block boundary — the EC-001 failure CC-006 was written for. Reading frozen
candidate identities removes that risk entirely rather than bounding it: there
is no vector in this replay to move. A cache assertion is a proxy for "the
vectors did not change"; here the stronger statement holds, that no vector was
consulted.

This does not make any criterion easier. The B0 gate is unchanged and remains
binding, and it is a stricter test of faithfulness than any hash comparison:
B0 must reproduce the committed deployed result's fact count, per-domain
breakdown, character count, episode identities, and payload SHA-256, and must
equal the shipped `pack_stm_payload` output byte-for-byte.

## Exclusions

- No locked registration text is edited.
- No retrieval, selector, threshold, packing, renderer, or budget change.
- No new embedding, cache, or model artifact is created.
- No committed EC-002, CC-006, AR-001, or E005 artifact is edited.
- If the program author declines this substitution, IC-001's arms are
  withdrawn and the study requires re-registration against an artifact that
  can supply a CC-006 cache for this corpus.

## Binding

This file is not documentation of a decision made elsewhere; it is the
decision, and the harness enforces it. Every phase:

1. refuses to run unless this file's `**Status:**` line reads `AUTHORIZED`;
2. hashes this file in `source_integrity.json` before and after the phase,
   alongside the store, the context log, and the pre-registration; and
3. records the file's SHA-256 and status in `run_header.json` and in
   `no_model_call_audit.json`.

Reverting the status line therefore stops IC-001 rather than silently
changing what its artifacts mean.
