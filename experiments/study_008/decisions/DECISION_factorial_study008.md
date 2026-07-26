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

The downstream-consumer re-derivation required by S8-T-010 is appended here
after Factor R is implemented and before Gate 3. It must cover renderer,
budgeting, containment, logs, context projections, and ceiling monitoring for
both rendering units.

## 8. Authorization

Authorized by the study author through the July 26, 2026 instruction to register
the supplied Study 008 documents and conduct the study end to end. Amendments
are authorized only when a blocker is encountered, must be made in good faith,
and must be registered before the affected work continues.
