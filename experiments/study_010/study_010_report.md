# Study 010 Report: Stopped Before Lock

**Source-document commit:** `ead2f66`
**Final status:** STOPPED BEFORE SCRIPT AUTHORSHIP

## Result

Study 010 does not lock or run. Pre-lock review found that it inherits the exact
protocol contradiction that stopped Study 009: structurally minimal Arm S must
omit the LTM tier, while S and accepted Arm L are also required to have
byte-identical prefixes.

Study 009 already demonstrated that accepted Arm L's empty
`<retrieved_ltm/>` block makes raw prompts differ at turn 1. Seeded responses
diverge at turn 3 and propagate into stored state. This is independent of the
new script and the 1,000-turn scale, so none of Study 010's later gates can make
the two requirements compatible.

The draft also says lock follows a Study 009 verdict. Study 009 produced no
null-test verdict because of its protocol STOP.

## Resolved Branches

- Digest carry: **false**. Study 009's fact-aware digest gate failed through
  `d = 50`, `B_digest = 50,000`.
- Arm L: **Study 007 accepted treatment, unchanged**. No Study 009 mechanism
  result exists to justify an amendment.
- Study 009 null-test input: **unavailable**.

## Consequence

The study stopped before authoring `script_1000.json`, its plant key, or its
rubric. No calibration, checkpoint implementation, rehearsal, live inference,
or scoring occurred. This avoids tuning or spending against a design that
cannot pass its own prefix requirement.

An author-approved re-registration must decide between structural subtraction
and prompt-shape parity and must replace the missing Study 009-verdict lock
condition with the actual STOP result.
