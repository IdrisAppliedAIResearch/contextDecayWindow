# Decision: Invoke the Registered Digest Contingency

**Study:** 009
**Registration anchor:** `37fff74`
**Gate artifact:** `experiments/study_009/gates/gate_results.json`
**Decision:** S+D is dropped before ablation

## Evidence

The production digest builder was replayed against the read-only Study 007 raw
store through turn 111. It used the locked sentence segmentation, eligibility,
density score, 0.95 semantic deduplication, verbatim provenance, and exact
production serialization.

The registered `d = 2`, `B_digest = 2,500` frame serialized to 2,332 characters
but contained no complete rubric-critical fact in any of the four domains. Its
highest-density spans were mostly numeric assistant-generated overview text,
reproducing the standing surrogate failure: density certified information-rich
text without certifying the facts the breadth probes require.

Calibration was broadened through `d = 50` and `B_digest = 50,000`. No setting
reached fact-aware coverage for all four domains. The preserved Study 007 store
and artifact tree were unchanged by replay.

G2 reproduced the Study 007 turn-120 and turn-121 LTM blocks byte-for-byte. G3
found no LTM, dreaming, promotion, or digest module in the Arm S import closure,
and the hand-derived N + K fixture passed.

## Binding Consequence

The pre-registration states that if no digest setting reaches 4/4, S+D is not
run and Study 009 reduces to the null test. That contingency is now invoked.

- S+D receives no ablation or live inference run.
- Digest Bars 1 and 2 are not evaluable.
- The live design contains Arm S and Arm L only.
- The confirmatory S-versus-L decision rule and protocol-integrity bar remain
  unchanged.
- Study 010 receives `digest carry = false` as the provisional branch input,
  subject to the Study 009 closeout.
