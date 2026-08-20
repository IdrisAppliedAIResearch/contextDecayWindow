# What HH-001 does not test, and one framing it must not carry

Recorded after the run, before the report is written.

## 1. A4 is not NF-004's control, and A2 ≈ A4 does not touch NF-004

NF-004 registered one comparison: **adjacent-turn pair ranking against
session-score inheritance**. It confirmed it on the sealed LoCoMo holdout,
843 → 935 complete-evidence deliveries, 140 gains / 48 losses, p = 6.19e-12.

A4 `RAG_FIXED` is fixed-width chunking. NF-004 never claimed to beat it and
never tested against it. So the A2 ≈ A4 result here — 0.563 against 0.550
judged — is a fact about a comparison NF-004 did not make, and it neither
confirms nor weakens NF-004's finding.

**An earlier draft of this analysis said the ranking apparatus "is not earning
its keep against a trivial baseline."** That inference does not follow and is
withdrawn. What the number supports is narrower and should be written as:
*on this corpus's question mix, at a 16,000-character budget, pair ranking and
fixed-width chunking produce downstream accuracy within 1.3 points.*

## 2. The breadth mechanism was never in the test

A2 is NF-004's `P_PAIR_RANK`: cosine ranking with greedy skip-on-overflow
packing. It contains **no set-level coverage objective and no diversity
floor.** E005's diversity selection — the mechanism that reached 12/17 at 4/4
domains, and the one the architecture's multi-domain claim rests on — is not
in this arm.

So HH-001 has not tested the component's breadth behaviour at all. It tested
its ranking granularity. Any sentence in the report about multi-domain or
chained retrieval would be about a mechanism that did not run.

## 3. The corpus cannot test it either

LoCoMo's question mix is dominated by lookups against one or two evidence
turns. Delivery by category, measured exactly with no model:

| A2 − A4 | single-hop | multi-hop | temporal | open-domain |
|---|---:|---:|---:|---:|
| | +0.033 | +0.016 | +0.053 | +0.019 |
| n | 61 | 62 | 19 | 157 |

Flat and small. **This is not evidence that the categories behave alike** — at
these sample sizes the differences are inside the noise, and the correct
reading is that the instrument cannot resolve them. LoCoMo's `multi-hop` is
also typically two evidence turns, which is not the four-domain breadth probe
the internal Q11 instrument was built for.

## 4. What would test it

A corpus whose questions require evidence from several distinct topics at
once, scored on whether every required domain appeared. The internal probe is
exhausted (NF-007 closed the coverage-count family on that store), so this
needs a fresh corpus and a registration of its own. Recording it here so the
gap is visible rather than inferred from the report's silence.

## 5. What HH-001 does support

Unchanged by any of the above:

- A2 over A3 on judged accuracy, +7.7 points, 46 gains / 23 losses,
  p = 0.0038, with the containment endpoint agreeing in sign.
- Mem0's write path cost 1,646 generative calls and 284 minutes; this
  component's cost zero.
- 21% of answers stated verbatim in the source were absent from Mem0's store,
  bounded above by a containment test.
- A1 full context scored highest at 222x the prompt tokens of the cheapest
  arm, so on this corpus the memory layer is a cost mechanism and not a
  capability one.
