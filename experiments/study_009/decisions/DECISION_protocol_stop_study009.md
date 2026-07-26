# Decision: Stop Study 009 at the Arm S Ablation

**Status:** BINDING STOP
**Registration anchor:** `37fff74`
**Gate commit:** `f901bda`
**Trigger:** Cross-arm prefix requirement is incompatible with structural Arm S

## Decision

Study 009 stops after the completed 35-turn Arm S ablation. No full Arm S or
Arm L run, blinded scoring, fact matrix, null-test verdict, or mechanism
analysis is performed.

## Reason

The registration requires Arm S to have no LTM tier on its import graph and no
`<retrieved_ltm>` block in its prompt. It also requires byte-identical prompts
and responses across arms through the empty-store prefix. The accepted Study
007 Arm L prompt contains `<retrieved_ltm/>` during that prefix.

The ablation confirms the contradiction is behaviorally material:

- raw prompts differ at turn 1;
- responses first differ at turn 3;
- after that response enters the raw store, prompts differ beyond the empty-tag
  normalization at turn 4.

No implementation can satisfy both requirements while leaving Arm L unmodified.
Adding an empty tag to S breaks structural absence. Removing it from L changes
the accepted treatment and breaks the unmodified-arm contract. Treating the
tag as ignorable after observing divergence would create a post-result
normalization rule.

## Consequences

- The S-versus-L null test is **not evaluated**.
- LTM is neither retired nor newly justified at the 120-turn scale.
- Digest replay failed and S+D remains dropped.
- Study 010 input `digest carry` is **false**.
- Study 010's LTM setting remains the Study 007 accepted treatment as the last
  accepted configuration, with an explicit note that Study 009 supplied no
  null-test verdict.
- A future 120-turn null test requires a new registration that chooses one
  coherent prefix rule before implementation: structural tier absence with
  expected prefix divergence, or prompt-shape parity with an explicitly inert
  placeholder.

The human-rater dependency was never reached. No agent rater was substituted.
