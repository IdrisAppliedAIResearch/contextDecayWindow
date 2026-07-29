# Retrieval Bakeoff Amendment 002 Correction

**Original result anchor:** `29c5150d`

**Amendment anchor:** `7b9994b1`

## Corrected T1.3

| Store | Historical K | Stored K | Recomputed pair K | User-only K | Assistant-swap K | Replay threshold crossings |
|---|---:|---:|---:|---:|---:|---:|
| study_009_arm_s | 0 | 0 | 0 | 4 | 6 | 0 |
| study_002_condition_c | 5 | 5 | 5 | 3 | 1 | 0 |

Most likely mechanism: `assistant_response_content_shift`.

## Exact Advancement

- `M2`: DOES NOT ADVANCE; wins=lookup,chained; regressions=enumeration.
- `M3`: ADVANCES; wins=lookup,chained,enumeration; regressions=none.
- `M4`: ADVANCES; wins=lookup,chained,enumeration; regressions=none.
- `M5_span`: ADVANCES; wins=lookup,chained,enumeration; regressions=none.
- `M6`: ADVANCES; wins=lookup,chained; regressions=none.

## Exact Routing Bound

Oracle recall `61/72` versus single-best `115/144`; relative gain `7/115`. Interpretation: `do_not_build_routing`.
