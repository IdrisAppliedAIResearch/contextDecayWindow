# LV-001 — Blind Scores

**Committed before the arm mapping was opened.** `AGENTS.md` §4: git order is
the evidence. At the time of this commit the rater does not know which of A and
B is the control and which is the treatment.

Rubric: `experiments/study_002/rubric_filled.md`, locked at S2_007.
Scoring surface: `blinded_surface.json`.

---

## B1 — Q11 breadth, correctly attributed items (turn 120)

Scored against the plant key per LV-001 §5: **an item restated inside a wrong
answer scores zero.** Mechanical presence is reported beside it to show where
the two diverge.

| Domain | Item | Arm A present | Arm A attributed | Arm B present | Arm B attributed |
|---|---|:--:|:--:|:--:|:--:|
| civil | Halcyon Crossing | yes | **yes** | no | no |
| civil | 847 | yes | **yes** | no | no |
| civil | Dr. Anara Bekova | yes | **yes** | yes | **yes** |
| civil | S460ML | no | no | no | no |
| civil | 92.4 | no | no | no | no |
| art | The Annunciation of Forlì | no | no | no | no |
| art | Melozzo da Forlì | no | no | no | no |
| art | Cardinal Giuliano della Rovere | no | no | no | no |
| art | 1483 | no | no | no | no |
| monetary | Taylor Rule | yes | **yes** | no | no |
| monetary | Federal Reserve | yes | **yes** | yes | **yes** |
| monetary | Dr. Priya Mehta | yes | **yes** | yes | **yes** |
| monetary | 2.3% | yes | **yes** | yes | **yes** |
| marine | Vampyroteuthis infernalis | no | no | yes | **yes** |
| marine | Dr. Kenji Watanabe | no | no | no | no |
| marine | 600 | yes | **no** | no | no |
| marine | marine snow | no | no | yes | **yes** |

**Arm A: 8 present, 7 correctly attributed.**
**Arm B: 6 present, 6 correctly attributed.**

The single presence/attribution split is Arm A's `600`. It states
"600–900 meters" as a mesopelagic/bathypelagic zone interface, not as the depth
range of the planted organism — and *Vampyroteuthis infernalis* is absent from
Arm A's answer entirely, so the value cannot be attributed to its subject.

**Domains reached.** Arm A: civil, monetary — and it states outright that no art
episodes were in its context. Arm B: civil, monetary, marine. Neither arm
delivers a single art item. Both enumerate general domain vocabulary in place of
the planted specifics.

---

## B2 — Targeted probes Q1–Q8

Locked rubric scoring: 1.0 / 0.5 / 0.0 per question.

| Probe | Expected | Arm A | Score | Arm B | Score |
|---|---|---|:--:|---|:--:|
| Q1 (112) | 847, S460ML | 847 only; says steel grade not in context | **0.5** | both correct | **1.0** |
| Q2 (113) | Bekova, 92.4 | Bekova only | **0.5** | says neither is recorded | **0.0** |
| Q3 (114) | both formatting rules | says no record of the conversation's start | **0.0** | both rules, verbatim | **1.0** |
| Q4 (115) | Annunciation, Melozzo, della Rovere, 1483 | attributes to **Leonardo da Vinci**, 1472, Benedictine monks | **0.0** | attributes to **Piero della Francesca**, Guidobaldo da Montefeltro, 1470 | **0.0** |
| Q5 (116) | lead white ground, ultramarine glaze | Fra Filippo Lippi / Fra Angelico; no technique given | **0.0** | names both pigments, but lead white as *highlights* not ground, inside the fabricated attribution | **0.5** |
| Q6 (117) | della Rovere as patron, later Julius II | denies the patronage as "a historical myth", cites a debunking | **0.0** | recasts him as papal governor of Forlì 1502–03 | **0.0** |
| Q7 (118) | Vampyroteuthis, Watanabe, 600–900m, marine snow | refuses: not in context | **0.0** | refuses: no such researcher known | **0.0** |
| Q8 (119) | photophores, mantle margin | photophores on mantle surface/webbing | **0.5** | photophores along the lateral mantle edges | **1.0** |

**Arm A targeted total: 1.5 / 8.**
**Arm B targeted total: 3.5 / 8.**

---

## B3 — Fabrication

Descriptive, no threshold, per §3.

| Arm | Probes containing fabricated content | Character |
|---|:--:|---|
| A | 3 of 8 (Q4, Q5, Q6) | Confident false attribution: Leonardo da Vinci as painter; a named art historian "debunking" the true patron |
| B | 4 of 8 (Q4, Q5, Q6, Q7) | Confident false attribution: Piero della Francesca as painter; an invented governorship; a fabricated pigment analysis containing two of the correct pigment names |

Both arms refuse honestly on Q7 where the material is absent, and both fabricate
freely on the art domain, which neither retrieved. Arm B's Q5 is the case
LV-001 §5 anticipated: the correct planted terms appear **inside** a wholly
fabricated account, and a presence-only scorer would have credited it.

---

## Rater note

Scored by one rater in a single pass against the blinded surface. The registered
protocol calls for three blind passes with adjudication; this is one, and that
shortfall is a limitation of this run rather than a property of the design.
No mechanism log, run header, or arm label was consulted before this file was
committed.
