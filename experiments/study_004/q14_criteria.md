# Q14 — Second Breadth Probe: Text and Scoring Criteria
## Study 004, contextDecayWindow
**Committed with:** `experiments/study_004/pre_registration.md`
**Position:** Turn 121 (immediately after Q13; after all Study-003-equivalent probes)
**Purpose:** Second breadth-query probe so Bar 1 (breadth recovery) does not rest on Q11 alone.

---

## Design constraints satisfied

- **Same coverage demand as Q11, different surface form.** Q11 asked the model to "list everything discussed across all four topics." Q14 reframes as a synthesis/recall task with a different verb and structure, so the two probes do not produce near-identical query embeddings while still requiring all four domains.
- **Requires a specific planted item per domain.** Full credit is impossible without surfacing a concrete planted value/entity from each of civil engineering, Renaissance art, monetary policy, and marine biology.
- **Ordering neutrality.** The question does not name the domains in the order they appeared, to avoid cueing recency/primacy.

---

## Q14 — probe text (as delivered to the model at turn 121)

> Before we finish, I want to check my own notes are complete. Across everything we've worked through together in this whole conversation, there were four distinct subject areas. For each one, remind me of the single most concrete fact or figure you gave me at the time — the kind of detail I'd want to have written down. Please make sure you cover all four areas, not just the recent ones.

Rationale for wording:
- "four distinct subject areas" states the count without naming or ordering the domains — the model must recover *which* four.
- "single most concrete fact or figure … at the time" forces retrieval of a planted specific, not a topical gloss.
- "all four areas, not just the recent ones" is a deliberate anti-recency instruction; a system that can only serve recent/similar context will visibly fail it, which is exactly the Study 003 failure mode Q14 is here to detect a second time.

---

## Scoring criteria (locked; scored 0 / 0.5 / 1.0)

Let a "domain hit" = the response correctly names the subject area AND supplies at least one specific planted fact/figure from that domain that matches the script's planted content (not a generic plausible statement).

| Score | Condition |
|-------|-----------|
| **1.0** | Four domain hits. All four subject areas named, each with at least one correct planted specific. |
| **0.5** | All four subject areas named, but exactly one domain is missing its specific (named-only) OR has an incorrect specific. At most one such lapse. |
| **0.0** | Any subject area entirely omitted, OR two or more domains named-only/incorrect, OR the response asserts a domain was not discussed. |

Scoring notes:
- "Named-only" means the domain is acknowledged but no correct planted specific is given.
- Asserting a domain was not discussed is an automatic 0.0 (this is the exact Q11 failure: the turn-120 response claimed Renaissance art and monetary policy had not come up). This mirrors Q11 scoring so the two are comparable.
- Half credit is capped at a single lapse by design — two lapses means the breadth mechanism is not reliably working, which should not earn partial credit.
- Scored against the same planted-fact key used for Q1–Q13. No new planted facts are introduced for Q14; it draws on the existing early/middle/late plants across the four domains.

---

## Interaction with Bar 1

Bar 1 requires Q11 ≥ 0.5 AND Q14 ≥ 0.5 AND (Q11 + Q14) ≥ 1.5. Q14's 0/0.5/1.0 scale (vs Q11's original 0/1.0) is intentional: it lets a near-miss register as partial rather than binary, giving a finer read on whether breadth *partially* recovered. For the combined-≥1.5 arithmetic, Q11 contributes its binary 0 or 1.0 and Q14 its 0/0.5/1.0.

**Attribution requirement (carried from Bar 1):** for either probe's pass to be read as an LTM-read-path effect, the arbitration log for that probe turn must show ≥ 1 LTM-provenance episode from a domain that STM retrieval did not surface. A pass with an all-STM context is recorded as a pass with unattributed cause and flagged.
