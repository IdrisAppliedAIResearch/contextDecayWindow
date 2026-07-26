# Study 009 Report: Null Test Stopped Before Full Run

**Registration anchor:** `37fff74`
**Implementation and gates:** `f901bda`
**Final status:** STOPPED AT 35-TURN ABLATION

## Result

Study 009 does not produce an STM-versus-LTM verdict. The study stopped before
the 121-turn runs because two registered requirements proved mutually
exclusive: structural Arm S must omit the LTM tier, while the protocol also
requires byte-identical cross-arm prompts through the empty-store prefix.

Arm S's 35-turn ablation completed successfully, but its raw prompt differs
from accepted Arm L at turn 1 because Arm L renders `<retrieved_ltm/>`.
Seeded responses diverge at turn 3. The sprint contract requires a stop on this
divergence, and neither changing Arm L nor adding an inert LTM placeholder to S
is permitted after registration.

## Digest Gate

The topic digest did not survive its pre-registered replay gate. At registered
`d = 2`, `B_digest = 2,500`, the exact 2,332-character frame contained no
complete rubric-critical fact in any domain. Calibration through `d = 50` and
`B_digest = 50,000` never reached fact-aware 4/4 coverage.

This is another instance of the standing surrogate failure: high density
selected numeric and entity-rich overview text, but not the facts the breadth
probe measures. The registered contingency dropped S+D before ablation.

## Gate Summary

| Gate | Result |
|---|---|
| G1 digest replay | FAIL; registered contingency invoked |
| G2 Arm L fidelity | PASS; turns 120 and 121 byte-identical |
| G3 Arm S sanity | PASS; N + K fixture and import closure clean |
| Arm S 35-turn runtime | PASS |
| Cross-arm prefix equality | FAIL; binding STOP |

Arm S's minimum speed was 33.70 tok/s, mean speed 41.19 tok/s, and peak
estimated context 9,960 tokens against the 40,000-token alert threshold. All
required logs were populated, the leakage audit passed, and no forbidden module
loaded.

## Scientific Consequence

The null test is unevaluable. Study 009 provides no evidence for retiring or
retaining LTM at 120 turns. The control-failure finding remains unresolved and
must not silently disappear from future study designs.

Study 010 receives:

- `digest carry = false`;
- `LTM configuration = Study 007 accepted treatment`, solely because it is the
  last accepted configuration, not because Study 009 validated it;
- `Study 009 null-test verdict = unavailable (protocol STOP)`.

No human scoring was requested or performed, no mechanism logs were used to
score responses, and no agent rater was substituted.
