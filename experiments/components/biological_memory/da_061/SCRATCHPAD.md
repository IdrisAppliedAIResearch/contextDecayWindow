# DA-061 Scratchpad

## 2026-08-31 - Registration

- Ordered adjacent query bigrams; exact adjacency inside accepted episodes.
- Union source-order postings; no unigram/pair fallback or score.
- Seal routes before required-session join.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Complete required-session coverage 401/465 (.862); any 432/465.
- Routed sessions p50 21; fraction p50 .447/p90 .851.
- Required-session first/last rank p50 5/9.
- Fails the .90 coverage bar and remains above the .25 selectivity bar.
- Do not use as a substitution gate; strongest order remains immutable.
