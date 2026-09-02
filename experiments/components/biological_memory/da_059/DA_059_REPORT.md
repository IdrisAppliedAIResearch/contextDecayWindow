# DA-059 Report

**Disposition:** `BROAD_SPARSE_SESSION_SIGNAL`

The exact-token posting route is fully evidence-blind and score-free. It covers
every required session for all 465 questions and every question type.

It is not selective. Median routed sessions are 44, representing 91.8% of the
available sessions; p90 routed fraction is 96.0%. The first required session has
median rank 13 and the last median rank 28. Exact singleton union therefore
moves token flooding out of the prompt but does not solve head choice.

The next structural key is exact token-pair co-occurrence. No model, embedding,
cache, delivery, reader, or adoption claim follows.
