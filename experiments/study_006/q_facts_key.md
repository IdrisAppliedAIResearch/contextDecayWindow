# Study 006 Rubric-Critical Plant Key

**Status:** LOCKED with the Study 006 pre-registration

**Carried from:** `experiments/study_005/q_facts_key.md` (amended — see Diff from Study 005)

**Purpose:** Define the planted facts used by the facts-in-LTM harness and Bar 1. A domain is present when at least one target row for that domain matches a faithful distilled record's provenance text. Matching is case-insensitive and requires every term in one row's `Required terms` cell.

**Span-granularity requirement (new in Study 006):** Study 006 selects sentence-level spans rather than whole turns. Every row's required terms must therefore be satisfiable **within a single sentence span** of its source turn. All rows below were verified against `experiments/study_005/script.json` under the locked segmenter (spaCy `en_core_web_sm` 3.8.0 sentencizer); each is satisfied by at least one span. Rows are unchanged from Study 005 except where noted.

## Civil engineering

| Fact ID | Required terms | Source turn(s) | Rubric dependency |
|---|---|---:|---|
| civil_project | Halcyon Crossing | 3 | Q1, Q11, Q14 |
| civil_span | main span; 847 | 3 | Q1, Q11, Q14 |
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

## Diff from Study 005

One amendment, required by the move to span granularity. No source turns changed; no facts added or removed from the script.

**Study 005 row (whole-turn matching):**

| Fact ID | Required terms | Source turn(s) |
|---|---|---:|
| civil_span | Halcyon Crossing; 847 | 3 |

**Problem.** Turn 3 segments into four sentences. `Halcyon Crossing` falls in span 0 (`"We are beginning work on a major infrastructure project called Halcyon Crossing — a long-span cable-stayed bridge."`) and `847` falls in span 1 (`"The total main span is 847 meters."`). No single span contains both terms, so the row is **unmatchable by construction** at span granularity — it could never be satisfied regardless of selection quality, and would misreport as a formation failure.

**Amendment.** The row is split so each row is satisfiable within one span:

| Fact ID | Required terms | Satisfied by |
|---|---|---|
| civil_project | Halcyon Crossing | turn 3, span 0 |
| civil_span | main span; 847 | turn 3, span 1 |

`civil_span` retains its ID and rubric dependency and remains the row carrying the 847 m measurement; `civil_project` is added to preserve coverage of the structure's name, which the Study 005 row also asserted. Aggregate civil-domain coverage is unchanged.

**Verification.** All 13 Study 005 rows were checked for single-span satisfiability under the locked segmenter. `civil_span` was the only unmatchable row; the remaining 12 are carried forward verbatim.

## Bar 1 interpretation

Study 006 raises the formation bar from 3 of 4 domains to **4 of 4**. See the pre-registration section *"Why the formation bar moves to 4 of 4"*: Study 005's control formed 3 of 4 domains and still scored Q11 = 0.0, because Q11 requires enumeration across all four domains. A 3-of-4 bar is logically insufficient to enable the breadth bar that depends on it.

Bar 1 passes when all of the following hold:

1. At least one target fact is present for **all 4 of the 4 domains**.
2. Every counted record resolves to source provenance and matches it verbatim **at the recorded character offsets**.
3. No non-content distilled record exists.
4. Marker records with `present_no_salient_fact` status do not count as facts or non-content records. On this script all four domains contain planted facts, so a marker in any domain is a formation failure for the purposes of Bar 1.
