# Study 009 Amendment 001: Protocol Repair and Resumption

**Author authorization:** User instruction permitting documented amendments to
bring Studies 009 and 010 into working order.
**Applies before:** Full Arm S execution and all Study 009 scoring
**Registration anchor:** `37fff74`
**Ablation STOP evidence:** `842fe67`
**Status:** BINDING; Study 009 resumes

## 1. Reason

The original registration required both structural absence of the LTM tier in
Arm S and byte-identical S/L prompts and responses through the empty-store
prefix. The 35-turn ablation proved those requirements mutually exclusive:
accepted Arm L renders `<retrieved_ltm/>`; Arm S correctly omits it. Raw prompts
differ at turn 1, seeded responses at turn 3, and stored-response propagation
widens the difference at turn 4.

The user has author-authorized a documented repair. This amendment changes the
invalid parity requirement, not any recall bar or null-test decision threshold.

## 2. Cross-Arm Parity Repair

Cross-arm byte-identical prompt and response requirements are replaced by:

1. byte-identical decoded script and user messages;
2. identical model artifact, server flags, seed, response budget, embedding
   artifact, and context ceiling;
3. identical STM N + K implementation, topic assignment, rule handling, and
   raw-store write path;
4. within-arm deterministic prefix reproduction across fresh server
   lifecycles;
5. architectural prompt differences are permitted exactly where the registered
   treatment differs: Arm L's LTM tier and Arm S's structural absence of it.

No claim of cross-arm response identity is made. Same-seed arms are paired
inputs, not identical stochastic trajectories after a treatment-visible prompt
difference.

## 3. Arm L Artifact Reuse

Arm L is the accepted Study 007 treatment, unmodified. Study 009 G2 reproduced
its turn-120 and turn-121 LTM blocks byte-for-byte. Rather than spend another
identical 121-turn inference run, Study 009 reuses the preserved accepted
Study 007 live artifact as Arm L.

This is a frozen-control reuse, not a synthetic replay:

- all 121 model responses were generated live under the registered runtime;
- script, seed, model, response budget, and treatment configuration are the
  values Study 009 carries;
- preserved prompts, responses, stores, and logs remain the scored/control
  artifacts;
- G2 is the implementation-fidelity bridge.

Arm S is run live under the same carried runtime.

## 4. Rater Amendment

The human-rater requirement is amended to a blinded agent rater, following the
documented Study 007 precedent and the user's present author authorization.

- Two anonymous response directories are generated from Arm S and frozen Arm L.
- Their mapping is sealed and not opened until scores are committed.
- The agent scores all 28 arm-question pairs against the locked rubric and Q14
  criteria, with primary and strict scores plus rationale.
- No full-run Arm S mechanism log, retrieval log, constructed prompt, database,
  or fact matrix may be opened before the score commit.
- The already-inspected 35-turn ablation is not a scored artifact and contains
  no terminal probe responses.

## 5. Digest and Bars

The G1 contingency is unchanged. S+D remains dropped. Digest Bars 1 and 2 are
not evaluable. The S-versus-L null-test decision rule and protocol-integrity
requirements remain unchanged except for the parity repair above.

## 6. Resumption Order

1. Commit this amendment.
2. Run Arm S for 121 turns and seal its outputs.
3. Build and commit blinded response inputs plus sealed mapping.
4. Commit blinded scores before opening full-run mechanism logs.
5. Unseal, build fact matrices, apply the registered null-test rule, and close.
