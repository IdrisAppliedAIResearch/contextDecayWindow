# Amendment 002 - Mixed Seal Representations

**Component:** Retrieval Mechanism Ledger, E002
**Timing:** Raised after Amendment 001's stricter canonical verifier ran and
before the embedding model loaded or any segmented-retrieval output was
generated.
**Authorization:** Owner request of July 30, 2026 to work the supplied ledger
end to end, subject to `AGENTS.md`.

## Trigger And Evidence

Amendment 001 assumed all tracked hashes in the corrected Tier 6 seal were
canonical LF hashes. Full verification showed the historical seal is mixed:

- 262 tracked entries use deterministic CRLF-materialized hashes;
- 2 tracked entries use canonical LF hashes;
- `study.db` uses its exact binary hash.

For all tracked entries, the checkout is newline-normalized identical to the
canonical `HEAD` blob. This is the same mixed-representation pattern handled by
AS-001's seal-line-ending amendment.

## Change

For each tracked entry, the verifier will:

1. load the canonical `HEAD` blob;
2. compute both its canonical SHA-256 and the SHA-256 after deterministic LF to
   CRLF materialization;
3. require the historical sealed hash to equal one of those two values; and
4. require the checkout bytes to be identical to the canonical blob after
   newline normalization.

The aggregate is recomputed from the unchanged historical sealed hashes. The
database remains exact-byte verified.

## Rationale

The historical seal committed a mixed platform representation. Requiring only
canonical hashes would reject 262 content-identical artifacts; requiring only
checkout hashes would reject the two canonical entries. Enumerating the two
permitted byte representations preserves the original seal without accepting
arbitrary content normalization.

## Exclusions

No E002 mechanism, input, sweep cell, budget, gate, tie-break, or interpretation
changes. No semantic equivalence is accepted. Only canonical LF and its
deterministic CRLF materialization are permitted.
