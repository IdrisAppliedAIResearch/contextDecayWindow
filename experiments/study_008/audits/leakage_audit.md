# Study 008 — Retrieval Leakage Audit

**Command:** `.venv/Scripts/python.exe scripts/verify_study_008_leakage.py`
**Verdict:** PASS

## Literal scan

- Python files scanned: 22
- Violations: 0

## Import-closure scan

- Modules in retrieval closure: 14
- Violations: 0

## Retrieval import closure

- `src/db/episode.py`
- `src/db/retrieval.py`
- `src/db/rule_store.py`
- `src/db/topic.py`
- `src/embeddings/provider.py`
- `src/memory/arbitration.py`
- `src/memory/context_builder.py`
- `src/memory/distilled_ltm_store.py`
- `src/memory/dream_engine.py`
- `src/memory/informativeness.py`
- `src/memory/ltm_store.py`
- `src/memory/retrieval_budget.py`
- `src/memory/retrieval_engine.py`
- `src/memory/span_segmenter.py`

## Violations

- None.

The test suite also plants a transitive test-only violation and
requires both detectors to reject it.
