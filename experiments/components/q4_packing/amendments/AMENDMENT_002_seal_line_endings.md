# AS-001 Amendment 002 - Seal Line-Ending Unit

**Date:** 2026-07-29
**Authorization:** The author explicitly allowed amendments for these follow-up
documents.
**Timing:** Raised before any post-fix packing output was generated or opened.

## Trigger and Evidence

Amendment 001 required each tracked canonical git blob SHA-256 to equal its seal
entry. A complete check showed that the run was sealed from mixed Windows
working-tree representations:

- 2 tracked files match their canonical LF blob bytes;
- 262 tracked files match the deterministic CRLF materialization of their
  canonical blob bytes;
- 0 tracked files fail both representations;
- `study.db` remains the sole uncommitted file.

The seal therefore hashes line-ending representations, not one stable git-byte
unit. Requiring only the canonical LF hash would falsely reject 262
content-identical committed files.

## Change

For each tracked text artifact listed by the seal:

1. Load the canonical git blob.
2. Compute SHA-256 for the blob exactly.
3. Normalize CRLF to LF, materialize that text as CRLF, and compute SHA-256.
4. Require the seal entry to match one of those two values.
5. Reject any file matching neither value.

Binary artifacts are not transformed. The database remains a missing committed
artifact and the historical seal verdict remains
`FAIL_MISSING_COMMITTED_DB`.

This supersedes only Amendment 001's statement that every tracked seal entry
must match the canonical blob's exact SHA-256. Its committed-log
reconstruction, cosine reproduction, and stop conditions remain binding.

## Rationale

The correction names the measurement unit actually used by the historical
seal. It permits only the repository's deterministic LF/CRLF conversion and
does not accept arbitrary normalization or content changes.

## Exclusions

This amendment does not edit the seal, historical files, candidates, renderer,
budget, packing order, or decision rule. It does not convert the historical
seal verdict to PASS.
