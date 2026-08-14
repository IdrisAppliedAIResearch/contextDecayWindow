# Amendment 002 - Candidate-Load Ratio Arithmetic

**Study:** NF-007 Part 1
**Status:** `BINDING - REPORTING CORRECTION`
**Amends:** `NF_007_PART1_REGISTRATION.md`, locked-parameter scale audit only
**Authorization:** mechanical correction under the repository amendment rule;
no design or criterion changes

## Trigger

The registration correctly fixes 119 parent episodes, 791 statement candidates,
and 16 clusters, but reports their candidate-load ratio as `6.6454x`.

## Correction

The exact registered arithmetic is:

- mean parents per cluster: `119 / 16 = 7.4375`;
- mean statements per cluster: `791 / 16 = 49.4375`; and
- candidate-load ratio: `(791 / 16) / (119 / 16) = 791 / 119 =
  6.647058823529412`, reported to four decimals as **`6.6471x`**.

The `6.6454x` value is withdrawn. The machine-readable artifact carries the
unrounded quotient.

## Effect on the registered design

None. `k=16`, both populations, the assignment construction, the reachability
rule, the stop branch, all integrity checks, and the construction caveat are
unchanged. The correction cannot change which clusters are occupied or whether
the registered branch passes.
