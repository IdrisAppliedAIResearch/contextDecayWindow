# Amendment 001 - Canonical Seal Representation

**Component:** Retrieval Mechanism Ledger, E002
**Timing:** Raised after the first execution attempt stopped at the source-seal
gate and before the embedding model loaded or any segmented-retrieval output was
generated.
**Authorization:** Owner request of July 30, 2026 to work the supplied ledger
end to end, subject to `AGENTS.md`.

## Trigger And Evidence

The corrected Tier 6 seal verifier reported exactly two mismatches:

- `logs/context_match.jsonl`
- `runtime_audit.json`

For both files, the sealed SHA-256 equals the canonical blob at `HEAD`. The
working-tree copy differs only because Git materialized LF as CRLF on Windows.
The sealed `study.db` is not tracked, but its exact working-tree SHA-256 matches
the seal.

The failed attempt created only the empty E002 output directory and its empty
`raw` child. It stopped before constructing the embedder and before any
configuration result was generated.

## Change

E002 will verify:

1. every tracked seal entry against its canonical `HEAD` blob;
2. the working-tree copy against that blob after newline normalization;
3. every untracked binary seal entry, currently only `study.db`, by exact bytes;
4. the original expected file count and absence of missing entries.

The verifier must report each representation used. Any canonical content
mismatch, non-newline checkout mismatch, database mismatch, or missing file
still fails the gate.

## Rationale

The seal protects content, not platform-specific line-ending materialization.
Using canonical Git bytes preserves the committed integrity anchor and follows
the already documented AS-001 seal-line-ending treatment.

## Exclusions

This amendment does not change query text, store eligibility, embeddings,
ranking, segmentation, sweep cells, deduplication, packing, character budget,
fact matching, gates, tie-breaks, or interpretation. It does not accept semantic
equivalence or arbitrary text normalization; only line endings may differ.
