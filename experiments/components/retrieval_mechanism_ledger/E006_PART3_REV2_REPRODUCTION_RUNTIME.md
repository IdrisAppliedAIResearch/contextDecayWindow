# E006 Part 3 Rev 2 - Reproduction Runtime Repair

**Type:** Auditor implementation repair after a failed historical gate
**Date:** August 10, 2026
**Failed gate commit:** `1a2702ee`
**Failed artifact SHA-256:** `B70906D6E7D4816090BFEDD0DA5D93CC74D8C0B030757ACFF1E38EAA0065716C`
**Status:** PRE-REGISTERED - AUTHORIZATION MUST FOLLOW THIS REVISION ANCHOR

## Trigger

The first Rev 1 reproduction run passed `114/144` Tier 4A E3 rows and failed
`30/144`. All 30 failures were the three depths for ten `c1000_l` queries.
Every row reproduced its selected count and exact serialized character count;
the failures were selected-sequence order and consequent payload SHA-256.
Tier 4A source identity and all 48 read-only cache accesses passed.

The reproduction auditor imported NumPy before setting the four single-thread
variables that the historical Tier 4A launcher set before every numerical
import. A diagnostic launch that set those variables in the parent shell before
Python import reproduced `144/144` Tier 4A rows and `8/8` A1 cells. This isolates
the failure to the auditor's numerical runtime contract, not the retained query
vectors, graph, serializer, or registered mechanism.

## Sole repair

At the top of `src/analysis/e006_p3_reproduction.py`, before any import that can
load NumPy, set all of the following to the historical value `1`:

- `OMP_NUM_THREADS`
- `OPENBLAS_NUM_THREADS`
- `MKL_NUM_THREADS`
- `NUMEXPR_NUM_THREADS`

The gate output must record these four values. The gate must still execute all
144 rows, require exact selected identity sequence and payload SHA-256 in every
row, and stop before A2 unless A1 also reproduces all eight cells. No tolerance,
comparison key, threshold, vector, graph, score, serializer, or outcome rule
changes.

## Ordering and scope

Commit this revision and its standalone authorization before the auditor repair.
Then commit the repaired auditor before rerunning into a new artifact directory;
the failed artifact is immutable. The rerun uses the existing sealed vector cache
and makes zero additional embedding calls.

This revision authorizes no A2 output by itself. A2 exploration remains gated on
the repaired `144/144` Tier 4A and `8/8` A1 result. All original scope and
interpretation limits remain binding.
