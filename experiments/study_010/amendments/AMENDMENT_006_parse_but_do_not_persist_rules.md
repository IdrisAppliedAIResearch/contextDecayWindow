# Study 010 Amendment 006: Parse but Do Not Persist Rules

**Date:** July 27, 2026
**Authorized by:** Muzaffer Ozen
**Authorization basis:** Amendment 004 authorizes documented amendments needed
to run Study 010 end to end.
**Applies after:** rehearsal attempts 003 and 004
**Supersedes:** Amendment 005's instruction to call
`suppress_rule_detection=True`

## Trigger and Evidence

Attempt 003 showed that the existing suppression API still injected the
classifier suffix but returned its tag as response text. All 200 responses
were contaminated with `<rule_detection>`.

After that API was corrected to omit the suffix, attempt 004 showed that the
raw-completion runtime used the suffix as a practical response delimiter.
Without it, turn 1 continued toward the 2,048-token safety ceiling. The attempt
was terminated before any response was accepted.

Both failed attempts are preserved and precede this amendment in git history.

## Change

For Study 010 only, both arms:

1. retain normal rule-classifier instruction injection;
2. parse and remove the classifier tag from the assistant response normally;
3. ignore the parsed `contains_rule` and `rule_summary` values by setting them
   to false and null before episode storage; and
4. assert that the persistent rule store remains empty.

The global provider suppression API remains corrected: callers that explicitly
request suppression receive no injected classifier instruction. Study 010 no
longer uses that option.

## Rationale

The locked script has no persistent-rule stimuli, so persistence decisions
have no valid positive target. Retaining the suffix preserves the established
raw-completion boundary; discarding only its persistence decision prevents the
known false positives from entering context.

The change is symmetric, deterministic, and orthogonal to the S-versus-L
memory contrast.

## Acceptance

A fresh 200-turn rehearsal of both arms must show:

- zero literal `<rule_detection>` tags in stored assistant responses;
- zero detected or pinned rules;
- zero prior-domain scope refusals;
- valid checkpoints at turns 100 and 200;
- peak context below the registered ceiling; and
- all existing runtime and integrity guards passing.

No full run begins until both arms pass.

## Exclusions

No locked artifact, memory policy, topic policy, retrieval threshold, budget,
sampling setting, score, or historical failed attempt changes. The G2 failure
and post-stop exploratory status remain unchanged.
