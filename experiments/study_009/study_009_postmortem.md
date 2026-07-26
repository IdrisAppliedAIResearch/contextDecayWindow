# Study 009 Postmortem

## What Worked

- Registration artifacts were committed before implementation.
- Arm S is genuinely minimal: its runtime closure contains no LTM, dream,
  promotion, or digest module.
- N + K behavior matches a hand-derived fixture.
- Digest charging uses the production serialization as its sole cost authority.
- G2 preserved Study 007 probe fidelity byte-for-byte.
- The 35-turn Arm S run cleared speed, context, logging, leakage, and structural
  checks.
- The study stopped before expensive full runs and scoring when the protocol
  became internally unsatisfiable.

## What Failed

The digest's density surrogate selected information-rich decoys rather than
rubric-critical facts. Expanding both span count and budget did not restore all
four domains.

More importantly, registration combined structural subtraction with byte-level
prefix parity. An absent tier changes prompt bytes even when the corresponding
store is empty. With seeded sampling, the difference became observable at turn
3 and propagated through the raw store.

## Prevention

Future subtraction controls must choose their parity unit before lock:

- behavioral architecture parity, allowing prompt-byte differences caused by
  structural absence; or
- prompt-shape parity, using an explicitly registered inert placeholder.

They cannot claim both structural absence and byte identity against an arm that
renders the empty tier.

Future component gates should also require the proposed ranking surrogate to
surface at least one complete target fact in a tiny frozen fixture before the
component is fully implemented. The fact-aware replay remains the binding
check, but an earlier adversarial fixture would expose the density mismatch
more cheaply.
