# SR-001 Extractive Span Representation Report

**Date:** August 11, 2026
**Outcome:** `NO_BROAD_GAIN - CHARACTERIZED`
**Pre-registration:** `baa317db41cb45b90087f4ec1cb1d4bd558cf55a`
**Authorization:** `f99b86a4`
**Amendment 001:** `5828147c98afdd542a6fe4233af8e0e7220bb04a`
**Passing Part 1:** `bbef505c648371e7761e0bedb9a35da21f4ccda6`
**Final design lock:** `13fe470e`
**Passing Preflight:** `709387a2297e7a96d3bafe70990dbeb84bb1a33a`
**Measurement implementation:** `cea52969578095ede5c9dc596423085bfe0839e2`
**Result commit:** `06f81786a0d4a7194101aeeebd63aa89273aa419`
**Result digest:** `33337dafd13ec7165431d068a5525b27d4bb6f4320102892aca49a6773e7d625`
**Calls:** zero model calls; zero new embedding calls; zero live runs

## Answer

Extractive span representation alone does not explain BA-001's promising span
result. When both arms receive the identical complete source-episode ranking,
the span arm performs worse:

| Measure | Whole episodes C0 | Source-rank spans T1 |
|---|---:|---:|
| Q11 facts | 8/17 | 4/17 |
| Q11 domains | 3/4 | 2/4 |
| Targeted matched facts | 19 | 17 |
| Targeted query gains / losses / ties | - | 0 / 2 / 22 |
| Enumeration macro recall | 0.0625 | 0.0625 |

G1 integrity and G2 matched retrieval pass. G3 fails because Q11 loses four
facts and total targeted availability loses two rather than gaining at least
one. G4 would also fail on `h121_l03` and `h121_c04`; G5 would fail because
lookup, chained, structural, and marine macro recall regress. The binding
disposition is the first failure: `NO_BROAD_GAIN`.

No 35-turn ablation or live run is authorized.

## Mechanical explanation

The historical BA-001 comparison changed two things at once. M2 ranked 111
whole episodes. M5_span embedded and ranked 3,268 sentence spans directly.
That span-level query matching moved short fact-bearing sentences ahead of
long semantically related responses and produced 10 gains, zero losses, and
the 0.625 enumeration result.

SR-001 removes that ranking change. Every sentence inherits its source
episode's score and remains grouped under its source rank. Under 32,000
characters, C0 delivers 7-11 distinct episodes per query. T1 spends the same
budget on 85-95 separately tagged spans but reaches only 3-7 distinct sources;
23/25 traces end partway through one source. Sentence markup and exhaustive
within-source delivery consume budget without moving later fact-bearing
sources forward.

The result separates two hypotheses: smaller serialization units are not
sufficient; span-level retrieval or within-source selection may be useful, but
that is a ranking/selection component, not representation granularity alone.

## Effects

Q11 retains civil 3/5 and monetary 1/4, but marine falls 3/4->0/4; art remains
0/4 in both arms. Targeted lookup falls 0.7500->0.6667, chained
0.5625->0.5000, and enumeration remains 0.0625. Structural macro recall falls
0.475->0.375 and marine 0.625->0.575; art and monetary tie.

The targeted losses are `h121_l03` (1.0->0.0) and `h121_c04` (1.0->0.5).
There are no targeted gains. Art remains a separate routing problem.

## Integrity

The first Part 1 execution stopped on three payload hashes even though all
selected identities and character counts matched. Recomputed cosines differed
from committed display scores by less than `6e-8`, crossing six-decimal render
boundaries. Amendment 001 anchored those committed display scores in both arms
without changing source order, selection, spans, budget, or gates. The failed
artifact remains committed.

Corrected Part 1 reproduces all 24 M2 controls byte-for-byte in two fresh
processes with deterministic digest
`7f4f04fff4937e81a75a1c44b4cc219497943baff7288e379ebda835a5dd6776`.
PF1-PF10 pass. All 28 targeted facts and the 17/17 Q11 ceiling are planted and
reachable in the eligible source population. Measurement requires terms to
share one selected unit at the registered turn and role.

All 18 focused tests pass. The full checkout passes 1,544 tests and retains 11
inherited Windows CRLF-versus-LF hash failures in locked BA-001, PS-001,
PS-003, and TA-001 checks. No seal was weakened. `ERRATA.md` was reviewed and
requires no update because SR-001 changes no previously published result.

## Disposition

`NO_BROAD_GAIN - CHARACTERIZED`. Do not promote source-rank-preserving
exhaustive span packing, and do not live-test it. BA-001's positive signal is
localized to span-level ranking or selection. Testing that mechanism would be
a new preregistered study and must not be described as representation-only.
