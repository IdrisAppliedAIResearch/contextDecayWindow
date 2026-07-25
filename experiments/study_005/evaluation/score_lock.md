# Study 005 Pre-Mechanism Score and Structural Lock

**Date:** 2026-07-22

Both 121-turn arms completed before scoring. Only the locked rubric response
artifacts, scoring authorities, fact key, distilled database, and run-completion
metadata were used. Full-run dream, arbitration, retrieval, and probe-context
logs had not been opened when these results were assigned.

## Scores

| Measure | Seeded promotion control | Dreaming treatment |
|---|---:|---:|
| Category 1, Q1-Q3 | 3.0 / 3.0 | 3.0 / 3.0 |
| Category 2, Q4-Q6 | 3.0 / 3.0 | 2.5 / 3.0 |
| Category 3, Q7-Q8 | 2.0 / 2.0 | 1.5 / 2.0 |
| Category 4, Q9-Q11 | 2.0 / 3.0 | 2.0 / 3.0 |
| Category 5, Q12-Q13 | 2.0 / 2.0 | 2.0 / 2.0 |
| Q1-Q13 total | **12.0 / 13.0** | **11.0 / 13.0** |
| Q11 | 0.0 | 0.0 |
| Q14 | 0.0 | 0.5 |

## Structural checks

- Same-seed prefix: 30/30 prompts and 30/30 responses byte-identical.
- Distilled records: 12 content records, all 12 faithful to provenance.
- Non-content records: 0.
- Rubric-critical domains represented: 2/4, civil engineering and monetary
  policy. Renaissance art and marine biology are absent under the locked fact
  matcher.
- Bar 1 formation threshold: **FAIL** because fewer than 3 domains are present.

Because Bar 1 fails, the preregistration requires Bar 2 to be recorded as not
evaluable: the read path is not credited or failed when the target facts are
not present in the distilled store. Bar 3 also fails provisionally because the
treatment scores below the control overall and in Categories 2 and 3.

The next analysis stage may now open mechanism logs without changing these
locked scores or structural results.
