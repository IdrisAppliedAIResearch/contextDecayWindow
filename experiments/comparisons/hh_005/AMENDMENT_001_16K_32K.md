# HH-005 Amendment 001 - paired 16k and 32k budgets

**Status:** `LOCKED after 20 32k answers and 8 pilot judgements, before score opening`
**Date:** September 1, 2026

At the user's correction, expand the benchmark from one 32k arm to two frozen
budget arms. `A_SEMANTIC_DA_V2_16K` allocates 8,000 characters to the unchanged
semantic order and 8,000 to DA-v2. `A_SEMANTIC_DA_V2_32K` allocates 16,000 to
each. Additive recency remains unchanged and outside the allowance.

At amendment lock, the 32k checkpoint contained 20 answers and eight pilot
judgements. No aggregate or item score had been opened. Preserve these stable
rows byte-for-byte after renaming the arm; never regenerate them. The 16k arm
has no paid rows. Finish both answer populations before full judging. Report
each against matched ASPECT-v1 and directly compare 32k versus 16k. All other
registered constraints remain unchanged.
