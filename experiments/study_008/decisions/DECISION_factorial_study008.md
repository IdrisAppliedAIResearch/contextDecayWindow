# Decision Record — Study 008 Retrieval Factorial

**Study:** 008
**Tasks:** S8-T-002, S8-T-010
**Pre-registration:** `experiments/study_008/pre_registration.md`
**Registration commit:** `0a20ef0`
**Status:** AUTHORIZED and binding

---

## 1. Corrected finding from Study 007

Study 007 did not demonstrate that the model ignored retrieved context. Its
binding correction (`fd78018`) showed that the Q11 answer used all 10 of the 10
rubric-critical atomic items delivered in the prompt, invented none, and missed
the remaining seven because they were absent from the prompt.

The retrieval failure had two coupled causes:

1. The similarity-ranked per-topic floor selected broad overview episodes for
   art and monetary policy instead of the fact-bearing source turns.
2. Uncapped global fill assigned every remaining slot to civil engineering.

The earlier "any planted term" surrogate certified topic presence while the
property needed by the rubric was delivery of a complete critical fact. That
criterion is retired. Study 008 gates count a domain only when the rendered
block contains every required term in at least one locked fact row.

## 2. Decision

Run a 2x2 factorial over two retrieval-side factors:

| Arm | Factor F: floor/fill | Factor R: rendering |
|---|---|---|
| A | similarity floor, uncapped fill | source episode |
| B | density floor, capped fill | source episode |
| C | similarity floor, uncapped fill | selected span |
| D | density floor, capped fill | selected span |

Formation, STM retrieval, `B_ltm = 32,000`, `k_min = 1`, seed, runtime, response
budget, and the 121-turn script remain fixed.

### Factor F

Floor candidates rank by the formation density score
`(named_entities + 2 * numeric_tokens) / word_count` computed over the unit that
will be delivered, with similarity as the deterministic tiebreaker. Fill
remains globally similarity-ranked but admits at most `c_fill` records per
topic. Floor selections do not consume the fill quota. `c_fill` is the only
deferred parameter and is locked by the joint Gate 2/Gate 3 calibration before
ablation.

### Factor R

Span arms render the selected distilled span verbatim with its source turn,
role, topic, dream-event, and offset provenance. Episode arms retain Study 007
rendering. Containment follows the delivered unit: episode identity for A/B and
recorded span offsets within STM episodes for C/D.

### Character parity

Every arm receives the same 32,000-character LTM content budget, charged against
the text that arm actually renders. Equal record counts would not be comparable:
episode and span units differ by roughly an order of magnitude. Character parity
holds delivered text volume fixed while allowing the rendering factor to change
how many independently selectable units fit.

## 3. Why a factorial

Rendering and floor policy are expected to interact through the fixed character
budget. Span rendering buys many more selections but gives up accidental
whole-episode carriage; density ranking can only help if fact-bearing units are
independently selectable and affordable. A factorial measures each main effect
and whether either effect depends on the other.

## 4. Leakage boundary

Density is a general text property. No retrieval-path module may read, import,
or transitively depend on the plant key, a rubric, scoring output, or a
fact-specific measurement module. Offline gates and evaluators may read those
artifacts because they measure the mechanism after selection; runtime selection
may not.

This boundary is enforced continuously by:

- a literal scan over retrieval-path source directories; and
- an AST import-closure audit rooted at the live retrieval modules.

Both detectors have a test-only planted transitive violation that they must
reject.

## 5. Standing surrogate-audit rule

For every gate and bar, ask: "Can this check pass while the property it claims
to certify is false?" Any residual gap is either fixed before use or recorded
and explicitly accepted. The audit is
`experiments/study_008/decisions/surrogate_audit_study008.md`.

## 6. Rejected alternatives

| Alternative | Reason rejected |
|---|---|
| Sequential studies | Would make the second factor operate on a different run and store, obscuring the budget-mediated interaction. |
| A single both-on treatment | Could show improvement but could not attribute it to floor policy, rendering, or their interaction. |
| Prompting/context-presentation study | Study 007's correction showed perfect use of delivered Q11 facts; prompting targets a failure not observed. |
| Fact-key-informed ranking | Outcome leakage. It would answer whether an oracle can retrieve the test facts, not whether a general retrieval policy improves. |
| Formation changes | All four domains already form under the accepted Study 007 formation path; formation is outside this study's change surface. |

## 7. Stage-interface re-derivation

Factor R changes one stage interface from "selected distilled records resolve to
source episodes" to "selected distilled records may render independently as
spans." Every downstream consumer is re-derived below.

| # | Consumer | Episode arms A/B | Span arms C/D | Resolution |
|---:|---|---|---|---|
| 1 | Distilled retrieval query | Source episode text and span embedding | Also needs distilled text, role, offsets, counts, and density | Query is additive; carried fields and ordering remain intact. |
| 2 | Selection identity | Source episode ID; multiple spans collapse | Distilled ID; spans from one episode remain independent | `selection_key` is rendering-aware and is the authority for dedup, phases, and floor protection. |
| 3 | Floor density | Recomputed over delivered user + assistant episode text | Uses formation's persisted span density | Both call the shared `density_score`; similarity remains the tiebreaker. |
| 4 | Character cost | User-message plus assistant-message characters | Verbatim span characters | `rendered_cost` dispatches on rendering mode; all arms retain `B_ltm = 32,000`. |
| 5 | Containment | Drop an LTM episode already in STM by source episode ID | Drop every span whose recorded source episode is already in STM; offsets, role, and text are mandatory | Filtering occurs before floor/fill so replacement follows the same phase and topic rules. |
| 6 | Arbitration merge | STM and LTM can merge as `both` on episode identity | Span identity is disjoint from STM episode identity; containment prevents redundant source overlap | Final uniqueness and floor-protection assertions use rendered-unit identity. |
| 7 | Tagged renderer | Existing `<episode>` with user and assistant children | `<span>` with verbatim text and distilled/source/turn/role/topic/dream-event/offset provenance | The five outer context blocks and their order are unchanged. |
| 8 | Budget utilization | Usually a small number of large units | Usually many small units | Utilization is measured in content characters in both modes; item count is observational, not a cap. |
| 9 | Context-size projection | 32,000 content characters plus episode tag overhead | 32,000 content characters plus more per-span provenance overhead | Gate 2 records actual rendered prompt sizes; the carried live monitor still aborts above 80% of 50,000 tokens. |
| 10 | Retrieval logs | Episode ID is the rendered unit | Distilled ID is the rendered unit; source episode remains provenance | Logs now record rendered-unit ID, mode, density, role, offsets, fill allocation, cap skips, and unchanged source IDs. |
| 11 | Retrieval metadata | Update the source episode's retrieval timestamp | Also update each selected span's source episode | Runtime database updates continue to receive raw source episode IDs, deduplicated after context assembly. |
| 12 | Formation | Produces the locked span records | Identical | No formation code path depends on rendering mode; only the shared density formula was extracted without changing its arithmetic. |

**Result:** no downstream consumer uses source-episode identity or episode text
unconditionally for an LTM unit. STM, topic assignment, consolidation,
formation thresholds, salience weighting, `C = 50`, and the inference path are
unchanged.

## 8. Authorization

Authorized by the study author through the July 26, 2026 instruction to register
the supplied Study 008 documents and conduct the study end to end. Amendments
are authorized only when a blocker is encountered, must be made in good faith,
and must be registered before the affected work continues.
