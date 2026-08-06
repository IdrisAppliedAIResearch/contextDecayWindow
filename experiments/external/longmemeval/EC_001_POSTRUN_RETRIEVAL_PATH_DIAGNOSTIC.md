# EC-001 Post-run Retrieval-path Diagnostic

**Status:** POST HOC; no registered metric, criterion, score, or run artifact is
changed.

## Trigger

The EC-001 report placed two true results next to each other without explaining
their mechanism: the pooled median evidence-session cosine rank is 2, while
any-session recall is 109/470 (23.2%). The original six adaptation hazards
registered recency and exchange/session granularity but omitted the carried
`K = 0.48` threshold as a distinct foreign-corpus hazard.

This diagnostic was requested after study closeout. It cannot become a
pre-registered explanation. It uses only the committed Tier 1 scores, the
already-opened sealed mechanism log, the pinned dataset, and the committed run
configuration.

## Fixed audit

For each question:

1. Treat the last 32 stored exchanges as the recency candidate set, matching
   the carried component.
2. Attribute a delivered evidence-session hit to recency when a delivered
   exchange from that evidence session is inside those last 32 exchanges.
3. Attribute every other delivered evidence-session hit to non-recency.
4. Count a question as having a K candidate when the maximum session cosine is
   at least 0.48. Because session cosine is the maximum exchange cosine, this
   is exactly the condition that at least one exchange clears K.
5. Use the committed `ContextReport.k_count` for K-eligible exchanges that
   actually survive outside recency.

Non-recency attribution cannot identify whether the evidence-bearing exchange
came from K or A3 when both paths delivered exchanges on the same question.
The diagnostic does not rerun embeddings or retrieval.

## Result

The apparent contradiction is a selection-and-packing result, not a rank
calculation error.

- The pooled median over 890 annotated evidence sessions is rank 2. At the
  question level, the best evidence-session rank has median 1, and 401/470
  questions have evidence in the top four. Only 96/401 of those questions
  retrieve any evidence session.
- A K candidate exists on 232/500 questions, so K does not simply fail to fire.
  A non-recency K exchange survives packing on only 20/500 questions, 26
  exchanges total.
- At least one evidence session contains a K-eligible exchange on 208/470
  questions. Only 56/208 retrieve any evidence session. Thus the 0.48
  threshold is consequential but cannot by itself explain the loss.
- Every block is truncated and at least 31,000 characters. The median block is
  31,920 characters and 17 exchanges, not roughly 60: 16 recency, 0 K, and 1
  A3 coverage exchange. Delivered blocks range from 9 to 42 exchanges.
- An evidence session intersects the 32-exchange recency candidate set on
  131/470 questions. It survives exact packing on 91; 40 recency-candidate
  questions still miss.
- Of 109 evidence-session hits, 91 are attributable to delivered recency and 18
  to all non-recency paths. No question has both kinds of evidence-session hit.
- Thirty of the 109 session hits omit every exact annotated answer turn,
  measuring the registered session/exchange granularity surrogate directly.

The carried N-first order is therefore the dominant observed gate on this
corpus: long recent exchanges consume nearly the entire exact-character budget
before K and A3. The threshold is an additional category-specific gate.
Single-session preference is the clearest case: its best evidence-session
cosine has median 0.399, only 5/30 evidence sessions contain any K-eligible
exchange, 20/30 still place evidence in the top four, and only 1/30 retrieves
the session. Granularity then explains the smaller 109-to-79 loss after a
session is retrieved.

## Interpretation boundary

This audit diagnoses the committed run. It does not estimate a counterfactual
score for a different K, recency policy, packing order, episode granularity, or
budget. Any such change is a new mechanism evaluation, not a repair to EC-001.
