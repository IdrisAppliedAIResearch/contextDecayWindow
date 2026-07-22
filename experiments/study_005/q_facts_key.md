# Study 005 Rubric-Critical Plant Key

**Status:** LOCKED with the Study 005 pre-registration

**Purpose:** Define the planted facts used by the facts-in-LTM harness and Bar 1. A domain is present when at least one target row for that domain matches a faithful distilled record's provenance text. Matching is case-insensitive and requires every term in one row's `Required terms` cell.

## Civil engineering

| Fact ID | Required terms | Source turn(s) | Rubric dependency |
|---|---|---:|---|
| civil_span | Halcyon Crossing; 847 | 3 | Q1, Q11, Q14 |
| civil_engineer | Dr. Anara Bekova | 3 | Q2, Q10, Q11, Q14 |
| civil_steel | S460ML | 4 | Q1, Q11, Q14 |
| civil_load | 92.4; metric tons per axle | 4 | Q2, Q11, Q14 |

## Renaissance art

| Fact ID | Required terms | Source turn(s) | Rubric dependency |
|---|---|---:|---|
| art_identity | The Annunciation of Forlì; Melozzo da Forlì; Cardinal Giuliano della Rovere; 1483 | 55 | Q4, Q11, Q14 |
| art_pigment | lead white ground; ultramarine glaze | 56 | Q5, Q11, Q14 |
| art_patron_role | Cardinal Giuliano della Rovere; Pope Julius II | 60 | Q6, Q11, Q14 |

## Monetary policy

| Fact ID | Required terms | Source turn(s) | Rubric dependency |
|---|---|---:|---|
| monetary_taylor | Taylor Rule; 1993 | 61 | Q11, Q14 |
| monetary_fed | Federal Reserve; dual mandate | 62 | Q11, Q14 |
| monetary_threshold | Dr. Priya Mehta; reverse repurchase; 2.3%; 2% | 65 | Q10, Q11, Q14 |

## Marine biology

| Fact ID | Required terms | Source turn(s) | Rubric dependency |
|---|---|---:|---|
| marine_identity | Vampyroteuthis infernalis; Dr. Kenji Watanabe; 600; 900 | 100 | Q7, Q10, Q11, Q14 |
| marine_photophores | photophores; mantle margin | 101 | Q8, Q11, Q14 |
| marine_feeding | marine snow particle aggregation | 102 | Q7, Q11, Q14 |

## Bar 1 interpretation

Bar 1 passes when all of the following hold:

1. At least one target fact is present for at least 3 of the 4 domains.
2. Every counted record resolves to source provenance and matches it verbatim.
3. No non-content distilled record exists.
4. Marker records with `present_no_salient_fact` status do not count as facts or non-content records.

All-4 domain coverage is reported separately as the stronger outcome.
