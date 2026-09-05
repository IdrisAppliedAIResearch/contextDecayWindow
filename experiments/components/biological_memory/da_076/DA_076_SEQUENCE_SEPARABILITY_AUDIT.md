# DA-076 Episode-Sequence Separability Audit

**Status:** `POSTHOC_SEQUENCE_SEPARABILITY_CHARACTERIZED`
**Date:** August 31, 2026
**Parent:** DA-075 result commit `f5cd0e72`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Scope

DA-075 identifies five target sessions that still share a role-typed union
signature with other sessions. This outcome-aware diagnostic has no inferential
disposition. It asks whether session union discarded distinguishing temporal
structure already present in the exact episode features.

## Fixed Analysis

Use only DA-075 `ROLE_SIGNATURE_COLLISION` target sessions and every session in
their exact role-signature groups. Represent each session as the ordered tuple
of its per-episode DA-074 augmented feature sets. Episode order and set contents
must match the sealed dataset; no alignment, weighting, edit distance, or
partial matching is allowed.

For each target report its union-group size/rank and exact sequence-group
size/rank. Classify it as `SEQUENCE_SPLIT` when sequence-group size is one,
otherwise `SEQUENCE_COLLISION`. Report how many union collisions split, group
distributions, and whether sequence length alone distinguishes the target.

No graph, selector, branch rule, or stopping criterion may be introduced. This
cannot support transfer or adoption. Zero model, embedding, and cache calls.

## Result

Exact episode sequences split all 5/5 residual role-signature collisions. The
union groups contain 2, 4, 5, 6, and 7 sessions; every target's exact sequence
group has size one. Sequence length alone distinguishes three targets. The two
remaining targets require episode order and per-episode feature contents.

Replay is byte-identical. This establishes deterministic identity only. It does
not show that a sequence-addressed carrier is useful, that a replacement is
safe, or that a reader can traverse the representation.

Artifacts:

- `artifacts/analysis/result.json`
- `artifacts/analysis/target_sessions.jsonl.gz`
