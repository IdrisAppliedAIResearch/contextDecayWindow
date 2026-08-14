# Amendment 001 - Domain Label Vocabulary

**Study:** NF-007 Part 1
**Status:** `BINDING - BEFORE VALID RERUN`
**Amends:** `NF_007_PART1_REGISTRATION.md`, registered reachability rule label
literals only
**Authorization:** the author's August 13 instruction explicitly permits domain
labels in evaluation and defines the intended comparison as art versus monetary

## Trigger and evidence

The first registered execution produced
`art_occupied_clusters=[]` and `NO_CLUSTER_REACHABILITY`. That result is invalid:
the evaluator looked for literal labels `art` and `monetary`, while the frozen
database uses `renaissance_art` and `monetary_policy`.

The invalid artifact is preserved byte-for-byte as
`artifacts/part1_cluster_reachability_invalid_v1.json`:

- bytes: 8,954;
- SHA-256: `6d046e5b9e605bf29c652ca58fca4c348e83330d4b5e7fe8df94c8366b0ac201`;
- observed statement-label totals: `renaissance_art=194`,
  `monetary_policy=208`, `civil_engineering=216`, `marine_biology=140`, and
  `probe=33`.

Thus the registered semantic populations were present and counted, but neither
could match the two incorrect literals. The failure branch fired vacuously and
does not measure reachability.

## Change

The evaluation-only vocabulary is corrected as follows:

| Registered semantic name | Frozen database label |
|---|---|
| art | `renaissance_art` |
| monetary | `monetary_policy` |

No other mapping, normalization, alias, or inferred label is allowed. The
machine-readable artifact must expose both semantic names and exact database
labels.

## Rationale

This repairs the measurement instrument without changing the property being
tested. "An art-occupied cluster contains no monetary statements" retains its
registered meaning; only the database vocabulary used to count those
populations changes. Leaving the literals untouched would make the intended
PF4 question unmeasurable and certify failure while the relevant populations
are non-empty.

## Unchanged and excluded

- `k=16` remains frozen; no alternate cluster count or sweep is run.
- Parent-derived clustering and expanded statement assignments remain frozen.
- The registered pass/fail rule and stop branch are unchanged.
- All assignment digests, population counts, frozen hashes, and call counts are
  unchanged.
- Domain labels remain evaluation-only and cannot affect clustering or future
  selection.
- No selector, query, Q11 key, availability measurement, or targeted outcome is
  opened.
- The invalid artifact is not overwritten, reused, or reported as a result.

## Effect on reachability

The amendment makes both registered semantic populations non-empty. It does not
make the positive branch easier: a pass still requires at least one cluster
with art statements and zero monetary statements. If every corrected
art-occupied cluster contains corrected monetary statements, the registered
`NO_CLUSTER_REACHABILITY` stop fires and no alternative `k` is tried.
