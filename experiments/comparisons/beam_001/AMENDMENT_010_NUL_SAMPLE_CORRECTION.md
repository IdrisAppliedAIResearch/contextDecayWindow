# BEAM-001 Amendment 010 - NUL sample correction

**Status:** prospective sizing correction; optimized API run not started  
**Date:** 2026-08-28  
**Amends:** Amendment 009  
**Corrected audit anchor:** `c89d7e1`

## 1. Finding

Amendment 009 correctly specifies one NUL byte between the sample domain and
question key. Its pre-registration sizing command accidentally evaluated the
two printable characters backslash-zero. Full implementation preflight used the
registered NUL byte and stopped on the resulting token mismatch before any
optimized API request.

The category rotation, conversation population, category balance and scale
balance do not depend on the within-category hash separator and are unchanged.
The fixed within-category identities do change. NUL-byte selection is retained
because it is the registered rule; the audit numbers are corrected rather than
changing the implementation to match the erroneous sizing command.

## 2. Corrected fixed counts

Replace Amendment 009's affected counts with:

- 53,892,126 exact reader input tokens;
- 56,656,926 charged reader tokens;
- 1,387 official rubric criteria;
- 4,161 criterion judge calls; and
- 5,511 successful optimized calls before retries.

The schedule remains 450 questions and 1,350 reader calls, with 90
conversations, five questions per conversation, 45 per category, scale counts
100/175/175 and zero overlap with the excluded pilot questions.

The corrected charged volume is 87.8% of HH-002's 64,551,127-token ledger and
remains inside the four-to-five-hour design envelope. Every other transport,
runtime, scoring, gate and disposition rule is unchanged.
