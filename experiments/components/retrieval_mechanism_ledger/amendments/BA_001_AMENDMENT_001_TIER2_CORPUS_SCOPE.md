# BA-001 Amendment 001 - Tier 2 Corpus Scope

**Date:** August 11, 2026
**Design anchor:** `94ed623a67fe5a893521323796b74d68aa4feebd`
**Authorization anchor:** `af5f3209b75f68c18b548172e913101c3542ea28`
**Status:** LOCKED BEFORE IMPLEMENTATION

## Trigger and evidence

Before implementation, the PF6 inventory grouped the frozen Tier 2 evaluation
rows by `corpus_id`, `method_id`, and `query_class`. This showed that Section
2.2 of the design carried pooled summaries while Section 7 explicitly limits
the diagnostic to corpus `c121_l`.

The frozen source remains:

`experiments/surveys/retrieval_bakeoff/tier2/evaluation_results.jsonl`

SHA-256:
`4DD8AECC17B8F21D7F5DBCD2EE40249532662205D5A262F7180452D2587E8E50`

For `c121_l`, the 24 rows per method reproduce these macro means:

| Method | Lookup (12) | Chained (8) | Enumeration (4) |
|---|---:|---:|---:|
| M2 raw whole episode | 0.7500 | 0.5625 | 0.0625 |
| M5 span dense | 1.0000 | 0.8125 | 0.6250 |

## Change

For BA-001 Sections 2.2, 3 PF6, 7, and Prediction 4, these values replace the
incorrect pooled values `0.8750/0.5938/0.1875` for M2 and
`0.7500/0.5938/0.6458` for M5.

The diagnostic remains limited to `c121_l`. Its registered disposition remains:
M5 enumeration recall must exceed M2 enumeration recall and the gain must be
positive for at least one query identity.

## Rationale

This repairs a corpus-scope contradiction so PF6 can require the values implied
by the registered input filter. It does not add data, change a method, add a
parameter, alter a threshold, or use a post-implementation result.

## Exclusions

- No pooled-corpus conclusion is authorized.
- No lookup improvement is required by the disposition.
- No live-answer or causal representation claim is added.
- The locked pre-registration is not edited.

## Authorization

The user's August 11 instruction, "Okay, you are authorized to proceed fully,"
authorized execution and necessary protocol-compliant blocker repairs through
the committed `CHARACTERIZED` ceiling. This amendment remains within that
scope.
