# HH-003 Amendment 002 - paid pilot prefix identity

**Date:** August 24, 2026
**Timing:** After context construction, before the first paid API call and before
any answer or judgement exists
**Pre-registration anchor:** `ea5cf2b6`

## Fixed prefix

G4's previously unnamed paid pilot is fixed to both registered arms on
`conv-26`, using its first eight scored questions in ascending source-index
order. These are the same eight items used by the committed G3 byte-identity
replay in `artifacts/preflight/g3_contexts.json`.

The pilot therefore contains 16 answers and 16 judgements. Successful records
are keyed by the registered content hash and are reused unchanged in G5. The
pilot checks API access, response shape, malformed count, resume behavior,
prompt/completion token accounting, and observed cost inputs. It carries no
score interpretation and changes no arm, endpoint, or full-run denominator.
