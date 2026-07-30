# Retrieval Mechanism Ledger Memory Update

**Status:** CLOSED on 2026-07-30.

Do not re-propose fixed-width mechanical query segmentation as the breadth
repair: E002 exhaustively tested 992 configurations and peaked at 10/17 Q11
items across 3/4 domains.

Do not treat generator attention as a perfect-term oracle or a deployable
retrieval mechanism. E001 was an exploratory NF4 Q4-only diagnostic. Its best
cue raised cosine from 0.120421976 to 0.210318044 and descriptive similarity
rank from 24 to 20, but none of 714 rows reached K=0.48.

E003 late interaction is untested and not authorized. Opening it requires a
new prospective breadth bound, measured storage multiplier, exact-budget
policy, and targeted no-regression test. E001 cannot supply that breadth bound.

Authoritative files:

- `RETRIEVAL_MECHANISM_LEDGER_REPORT.md`
- `artifacts/e002/e002_results.json`
- `artifacts/e001/capture_001/capture_manifest.json`
- `artifacts/e001/analysis_001/e001_results.json`
