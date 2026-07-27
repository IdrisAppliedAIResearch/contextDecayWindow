# Study 010 Amendment 005: Disable Inapplicable Rule Extraction

**Date:** July 27, 2026
**Authorized by:** Muzaffer Ozen
**Authorization basis:** Amendment 004 authorizes documented amendments needed
to run Study 010 end to end.
**Applies after:** the failed Amendment 004 rehearsal committed at `68f2129`
**Applies before:** any replacement rehearsal or 1,000-turn run

## Trigger and Evidence

Arm L rehearsal attempt `study_010_rehearsal_002` completed 200 turns but
failed behavioral integrity. The inference-side rule classifier promoted 118
turn-local domain-scoping clauses into persistent rules. At the first domain
transition, the pinned Aster Viaduct instruction caused refusals; those
responses then contaminated STM and LTM. The pinned-rules block reached an
estimated 5,512 tokens.

The locked script contains no persistent behavioral-rule plant. Its repeated
"Stay within the [domain] thread" wording scopes the current filler question
and intentionally changes between domains. Persistent-rule extraction
therefore has no valid positive target in this study.

## Change

For Study 010 only, both Arm L and Arm S:

1. call the inference provider with `suppress_rule_detection=True`;
2. skip the lexical persistent-rule fallback;
3. retain an empty pinned-rules block; and
4. assert at every completed turn that the rule store count is zero.

The replacement rehearsal must run 200 turns for each arm and pass:

- zero detected or pinned rules at every turn;
- no cross-domain refusal caused by a prior domain's scope instruction;
- checkpoints at turns 100 and 200;
- peak context below the registered 80% ceiling;
- all existing runtime, leakage, and integrity guards.

Only a passing two-arm replacement rehearsal authorizes the full runs.

## Rationale

This is a protocol repair for an inapplicable carried subsystem, not a
parameter choice based on scored outcomes. No genuine rule can be lost because
the locked script contains none. Applying the repair identically to both arms
preserves the S-versus-L contrast and prevents a known classifier error from
dominating context growth.

## Exclusions

This amendment does not:

- edit the locked script, rubric, plant key, or artifact lock;
- change rule detection globally or alter prior-study behavior;
- change STM retrieval, topic assignment, consolidation, LTM formation,
  arbitration, rendering, budgets, sampling, or scoring;
- rescue or reuse contaminated rehearsal state;
- waive the failed G2 result or make post-stop evidence confirmatory.

## Reporting

The failed rehearsal remains part of the study record. Replacement rehearsal
and full-run manifests must cite both Amendments 004 and 005. The final report
must quantify the failed rehearsal's false-rule accumulation and confirm zero
pinned rules in accepted continuation runs.
