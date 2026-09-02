# DA-049 Directional Residual Audit

**Status:** `COMPLETE; FARTHER_DIRECTIONAL_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-048 result commit `6fbc412b`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Among the 170 questions still incomplete after DA-048, how many missing evidence
sets lie farther along an already-frozen directional temporal ray?

## Audit

Reproduce DA-038=232, DA-046=250, and DA-048=295 exactly. For each remaining
miss, map every missing evidence member to its episode/session position. For
every frozen baseline edge, treat `seed_id` plus `direction` as a ray and record
the minimum exact temporal distance of the target episode when it lies strictly
beyond distance two in the same session and direction.

Classify each residual exclusively as:

- `SINGLE_DIRECTIONAL`: all missing evidence is one member in one episode on at
  least one frozen ray; report minimum distance and exact rendered frame cost;
- `MULTI_MEMBER`: more than one missing member is required;
- `NO_DIRECTIONAL_RAY`: the singleton target lies on no frozen ray.

Report distance counts, <=2,048 fit, and question types. This is an
evidence-aware audit only. It changes no order, payload, stream, threshold, or
outcome and authorizes no reader or adoption claim.

## Result

Of 170 residuals, 37 are singleton directional: 18 at distance 3, 10 at 4,
and 9 at 5. All 37 fit the 2,048-character frame. The remainder is 78
multi-member and 55 off-ray. The next structural probe is therefore a frozen
directional cursor through distance 5, followed by grouped retention if useful.
