# BEAM-001 Amendment 006 - Pilot gate ordering

**Status:** authorized prospective repair; no reader or judge call made  
**Date:** 2026-08-28  
**Amends:** `BEAM_001_PRE_REGISTRATION.md` at commit `12f01fcc`

## 1. Conflict

Section 5 required the six-answer reader pilot to be judged before the remaining
answers were generated. Section 6 and PF3 require all 5,400 answers to be sealed
before any judge request is constructed. Both cannot be true. Early pilot
judging would expose outcomes before the answer schedule was complete and could
feed back into whether the population run proceeds.

The conflict was found before live implementation and before any reader or
judge call. It is repaired prospectively rather than reconciled in code.

## 2. Binding repair

The pilot consists only of the two lexicographically smallest question keys in
all three arms: six reader requests. It passes when all six responses are
nonempty, naturally stopped and bound to their registered request-body digests.
No outcome field, rubric or judge prompt is opened or constructed during the
pilot. The six responses remain part of the fixed 5,400-answer population and
are reused without regeneration.

After the pilot passes, generate and seal all remaining answers. Only then open
the outcome surface, construct all 16,275 blind criterion requests, and begin
judging. The first submitted judge batch is the transport/schema smoke for that
stage; it has no result-dependent continuation rule beyond the already
registered validity checks.

G-PILOT is correspondingly repaired to require six valid reader answers and
zero judge calls. PF3 and G-ANSWERS remain unchanged and govern the judge-stage
ordering.

## 3. Unchanged

The model, prompts, population, six pilot identities, request counts, output
limits, retry rule, scoring, statistics, dispositions and every other gate are
unchanged. The complete valid schedule remains 5,400 reader calls plus 16,275
judge calls before retries.
