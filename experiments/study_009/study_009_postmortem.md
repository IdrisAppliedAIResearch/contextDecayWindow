# Study 009 Postmortem

## What Worked

- Registration, implementation, gates, amendment, run artifacts, blinded
  inputs, and scores landed in auditable git order.
- Arm S is structurally minimal and loaded no LTM, dream, promotion, or digest
  module.
- The 35-turn ablation and full run matched byte-for-byte across fresh server
  lifecycles.
- Blinded scoring occurred before the mapping or full-run mechanism logs were
  opened.
- The null test produced a decisive result: L beat S by 1.5 points, localized
  to Q5 and Q8.
- The 17-item matrix linked the breadth difference to prompt delivery without
  counting any answer-only lucky hits.

## What Failed

The digest's density surrogate selected information-rich decoys rather than
rubric-critical facts. Increasing both span count and budget never restored
all four domains, so S+D was correctly dropped.

The original registration also combined structural subtraction with cross-arm
byte parity. An absent tier necessarily changes prompt bytes when L renders an
empty `<retrieved_ltm/>` frame. The original protocol stopped correctly, but
the contradiction should have been caught before the ablation.

Arm L still failed Q11 and earned only 0.5 on Q14. LTM proved useful relative
to pure STM, but it did not solve breadth recall.

## Repair and Prevention

Amendment 001 selected architecture-aware parity: same script, runtime, seed,
and shared components, while allowing the registered treatment to change
prompt structure. Within-arm fresh-lifecycle determinism replaced impossible
cross-arm response identity.

Future subtraction studies must lock one coherent parity unit before
implementation. Component ranking gates must also prove target-fact recovery
on a small adversarial fixture before broad replay calibration.

Study 010 should retain the accepted LTM configuration, reject the digest, and
avoid interpreting L's relative win as breadth success.
