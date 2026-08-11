# Amendment 005 - Rev 4 Query Vector Absence

**Date:** August 10, 2026
**Applies to:** `E006_PART3_REV4_NEUROSCIENCE_CONSTRUCT_REPAIR.md`
**Design anchor:** `a4f952f6`
**Authorization anchor:** `27313b66`
**Status:** AUTHORIZED - BINDING BEFORE IMPLEMENTATION

## Trigger and evidence

Rev 4 Section 5 assumed a carried internal-Q11 query vector. The
post-authorization input audit found no such committed vector:

- `artifacts/rd001/full_rank_inventory.csv` contains 119 scalar query-to-episode
  cosines, not a query vector. SHA-256:
  `8D6F9EEE6EBE232608981AAC0C0D4816EAEC4710AE551DB028AE0B323253AC03`.
- `artifacts/e006_p3_tier4a_capture/query_vectors.sqlite` contains exactly 48
  retained vectors, all identified by its manifest as the `c1000_l` and
  `c121_l` holdout queries. It contains no internal-Q11 text or vector.
  SHA-256:
  `D9741EDB0545D8CFE050663340599A31813D6025C38F0467E0EC7671573A1E6A`.
- The capture manifest names all 48 corpus/query identities. SHA-256:
  `2C24EA75D7551BEB6658D8B9208225B985E25A9111CFD3766EC4F7980A7F18E4`.
- The committed E006 Part 2 Preflight had already recorded the broader input
  class as absent. SHA-256:
  `AE78582C4116800FCAABB9286AF1AF262C5F34B7F42ED2990FD3F11D51369FA9`.

A least-squares vector can be constructed to reproduce the 119 cosines, but it
is not the original query embedding and is non-identifiable outside the episode
span. Bipolarizing that surrogate would make an arbitrary reconstruction act as
the neural cue. That can pass while natural-language partial-cue completion is
false, exactly the construct error Rev 4 is intended to repair.

## Change

Rev 4 Section 5, its dependent PF1 query-vector inventory, implementation-order
steps 8-9, and any Q11 translation output are removed from authorization.

The binding Rev 4 work remains unchanged:

- The 119 committed episode vectors are encoded exactly as registered.
- G1-G4 and the degenerate-cue audit run exactly as registered.
- The result remains one of `INVALID_IMPLEMENTATION`, `PATTERNS_NOT_STORED`,
  `NO_EXACT_MINIMAL_COMPLETION`, or
  `AUTOASSOCIATIVE_COMPLETION_DEMONSTRATED`.
- Zero embedding requests and zero model-generation calls remain binding.

If G3 or G4 passes, the report may state only the attractor-recovery result and
its registered limitations. It produces no Q11 fact count, payload, retrieval
ranking, or promotion comparison.

## Rationale

This amendment removes an unavailable input and a non-identifiable surrogate;
it does not alter G3, G4, their exact bars, the episode population, encoding,
learning rule, recurrence, or disposition. It cannot make the binding result
easier. It also reinforces the post-mortem distinction between within-memory
pattern completion and cross-memory retrieval selection.

## Exclusions

This amendment authorizes no new embedding call, query reconstruction, alternate
cue representation, use of Q11 fact labels, targeted measurement, live run,
multi-attractor search, threshold change, or reinterpretation of completed P3.
A future natural-language partial-cue test requires a prospectively retained
query vector or a separately specified cue encoder.

## Author authorization

The program author explicitly authorized handling the Preflight and any
revisions needed to continue, then authorized amendment and reimplementation
after clarifying the intended neuroscience construct. This amendment applies
that authorization narrowly to an input absence discovered before
implementation. No gate is waived.
