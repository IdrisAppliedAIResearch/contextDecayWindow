# DECISION — Dreaming Selection Policy Revision (Study 006)

**Study:** 006
**Pre-registration:** `experiments/study_006/pre_registration.md` (SHA `5def302`)
**Date:** 2026-07-25
**Scope:** The dreaming **selection policy only.** No pipeline component is added, removed, or reordered.

---

## 1. The Study 005 finding this responds to

Study 005 established the architecture and failed on one thing: **which spans dreaming chose.**

Every mechanical property passed — 100% provenance faithfulness, zero non-content records, zero inference calls in dreaming, 10.81% compression, and distilled records reliably reaching both breadth probes. The confirmatory outcome was nonetheless PARTIAL: Bar 1 failed at 2 of 4 domains (civil and monetary formed; art and marine did not), Bar 2 was therefore not evaluable, and Bar 3 failed at 11.0 vs the control's 12.0.

The cause was the salience proxy, not the mechanism. Study 005 scored **whole user/assistant turn episodes** by **absolute counts**:

```
salience(episode) = named_entity_count + 2 × numeric_token_count
```

Long generated answers accumulate many incidental names and numbers simply by being long. With a top-3-per-topic cap, the ranking systematically preferred verbose model output over concise user-planted facts. Planted facts ranked **11th, 16th, 17th, 18th, 19th and 28th** within their dream events; only two of eleven were selected.

The algorithm behaved exactly as specified. **The proxy for factual salience was the failing assumption** — which is the finding, and the reason this revision is a policy change rather than a bug fix.

---

## 2. The three changes

All three sit inside the existing extractive dreaming stage. Dreaming remains extractive: it selects and copies existing text and makes zero inference-model calls, so fabrication stays structurally impossible.

**2.1 Span granularity.** Selection operates on sentence-level spans rather than whole turns, so a compact fact competes on its own merits instead of being buried inside a long turn. Spans carry source episode_id, turn, role, and **character offsets**, which is what makes the verbatim assertion checkable at span granularity.

**2.2 Density normalization.** Salience becomes entity/numeric content *per unit length*:

```
base(s)     = named_entity_count(s) + 2 × numeric_token_count(s)
density(s)  = base(s) / word_count(s)
```

This is the core correction: it makes a short dense fact outrank a long diffuse answer, which is precisely the Study 005 failure. It was deferred as a "tunable" in the Study 005 design and is now empirically motivated.

**2.3 Source awareness.** `salience(s) = density(s) × source_weight(role)`, with user 1.5 and assistant 1.0. In a conversation the user is the source of ground truth and the model's own prior output is derivative. This is a tiebreaker-scale weight, not a domination weight — a genuinely dense assistant span can still outrank a sparse user span.

---

## 3. Rejected alternatives

| Alternative | Rejected because |
|---|---|
| **Raise the per-topic cap C above 3** | Treats a ranking failure as a capacity problem; the plants ranked as low as 28th, so any cap that admitted them would admit ~25 verbose decoys with them and destroy the compression the architecture exists to provide. |
| **Keep whole turns, tune the entity/numeric weights** | Reweighting cannot fix a length bias: under absolute counts a long turn accumulates score by length regardless of the weights, so the ordering that buried the plants survives any nonnegative reweighting. |
| **Move to abstractive/generative dreaming** | Extractive fidelity was never the bottleneck (100% faithful in Study 005); generation would add a fabrication failure mode on top of an unsolved selection problem. |
| **Build the retrieval-diversity mechanism now** | Its pre-registered trigger is Bar 1 pass + Bar 2 fail, which has not occurred. Formation is upstream of retrieval; fixing retrieval against a store that lacks the facts is untestable. |

---

## 4. Why the formation bar moves from 3 of 4 to 4 of 4

Study 005's control produced an unplanned natural experiment. The promotion-based control formed **3 of 4** domains (civil, art, marine — missing monetary) and still scored **Q11 = 0.0**.

Q11 requires enumeration across all four domains. A store missing any domain cannot support it. A 3-of-4 formation bar is therefore **logically insufficient** to enable the breadth bar that depends on it — the two bars were internally inconsistent in Study 005, and the control demonstrated it rather than merely implying it.

Bar 1 is raised to 4 of 4. The `present_no_salient_fact` marker path remains implemented and is retained as an honest general-purpose mechanism, but on this script all four domains contain planted facts, so a marker in any domain is a formation failure for Bar 1.

---

## 5. Pre-lock probe evidence

An executable probe scored every plant-key row against `experiments/study_005/script.json` under the locked segmenter before any parameter was fixed. It scores plants **in isolation** and does not model competition for the top-3 slots; the Retrospective Replay Gate remains the authority on selection outcomes.

**Word window 4–60 — validated.** Every planted span falls inside the window (observed 7–39 words). No bound excludes a plant.

**Plant key — one amendment.** `civil_span` required both `Halcyon Crossing` and `847`, which turn 3 segments into different sentences. The row was unmatchable at span granularity by construction and would have misreported as a formation failure. Split into `civil_project` and `civil_span`; all 14 resulting rows are single-span satisfiable. Full diff in `q_facts_key.md`.

**F = 0.15 — provisional.** All four domains retain at least one plant clearing 0.15 (civil 0.19/0.38, art 0.31, monetary 0.18/0.31, marine 0.41), so 4/4 is reachable at the floor. But 8 of 14 rows fall below it. F is **not locked by this record**; it is fixed by S6-T-013 on replay evidence, before the ablation, and never after a run.

---

## 6. Risks accepted at lock

Recorded before the run so the outcome is confirmatory rather than post-hoc, and left unfixed so that replay evidence — not pre-run tuning — governs any revision.

- **`marine_photophores` is rejected at the eligibility filter.** spaCy tags no entity in it (Latin binomials such as *Vampyroteuthis infernalis* are not NER entities) and it carries no numeric token, so it scores 0.0 and never becomes a candidate. Marine formation rests entirely on `marine_identity`; art rests entirely on `art_identity` for the same reason.
- **Bar 3 regression risk sits where Study 005 already failed.** Study 005's Q1–Q13 shortfall was Q5 (art) and Q8 (marine). The facts those questions depend on — `art_pigment` (0.05) and `marine_photophores` (0.00) — are the two lowest-scoring rows under this policy. **Bar 1 may reach 4/4 while Bar 3 fails for the same reason as Study 005.**

---

## 7. Source-weight limitation (carried verbatim into the report)

> **Source weighting is script-correlated.** Weighting user spans above assistant spans is defensible in general (the user supplies ground truth; model output is derivative), but in *this* script the planted facts are user-authored, so the weight is also conveniently aligned with the answer key. This study cannot separate "user content is genuinely more valuable" from "user content happens to be where this script hid the answers." A script with model-authored target facts would be needed to disentangle, and is out of scope.

The replay gate carries its own interpretive limit: it validates the policy against data the policy was designed after. It prevents spending a run on a policy that provably cannot work; it does not independently establish generalization. The adversarial fixture is the complementary check that the policy handles the failure *shape* rather than these specific sentences.

---

## 8. Authorization

The decisions recorded above — the three-part selection-policy revision, the rejected alternatives, the 3/4 → 4/4 bar change, the spaCy segmenter/NER lock, the `civil_span` plant-key amendment, and the choice to record rather than tune away the two risks in §6 — were taken by the author on 2026-07-25.

**Authorized by:** Muzaffer Ozen, Idris Applied AI Research — 2026-07-25
**Status:** AUTHORIZED. F remains open until S6-T-013.
