# Decision: Stop Study 010 Before Lock and Script Authorship

**Status:** BINDING PRE-LOCK STOP
**Study 010 source-document commit:** `ead2f66`
**Inherited Study 009 evidence:** `842fe67`

## Trigger 1: Lock Precondition Is Missing

The Study 010 pre-registration says it locks only after Study 009's verdict
resolves its branches. Study 009 stopped at the 35-turn Arm S ablation and
produced no STM-versus-LTM verdict. The digest and Arm L configuration can be
resolved mechanically, but the stated verdict precondition did not occur.

## Trigger 2: The Prefix Contract Is Already Falsified

Study 010 inherits both of these requirements:

1. Arm S is Study 009's minimal composition, with the LTM tier and
   `<retrieved_ltm>` block structurally absent.
2. S and L must have an identical prefix.

Study 009 measured this exact pair. Accepted Arm L renders
`<retrieved_ltm/>` while the store is empty; Arm S omits it. Prompts differ at
turn 1, seeded responses differ at turn 3, and stored-response propagation
causes broader prompt divergence at turn 4.

The contradiction is independent of script length. A 1,000-turn script,
checkpointing, scale gates, or a 200-turn rehearsal cannot repair it.

## Why Work Stops Before S10_001

The sprint plan permits script authorship before Study 009, but it does not
require spending that effort after a binding feasibility failure is known. The
contract says to stop and flag on divergence. Authoring and hash-locking a new
1,000-turn script against an impossible arm protocol would create substantial
artifact work that cannot reach the green light.

The registered human-rater dependency is also unconfirmed, but it is not the
primary stop reason.

## Required Re-Registration

Study 010 can proceed only with an author-approved replacement registration
that resolves both issues before script authorship:

- choose structural tier absence with expected prompt/response prefix
  divergence, or prompt-shape parity with an explicitly inert placeholder;
- replace the missing Study 009-verdict lock condition with the actual Study 009
  STOP inputs.

No 1,000-turn script, rubric, plant key, calibration, checkpoint
infrastructure, rehearsal, live inference, or scoring was produced.
