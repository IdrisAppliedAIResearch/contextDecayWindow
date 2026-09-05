# DA-022 NF Immutable-Pack Continuation Report

**Status:** `NO_NF_IMMUTABLE_PACK_CAPACITY_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `494c4d49`
**Blind allocation commit:** `356fed76`
**Standing:** spent NF-004 exact-availability result

## Result

Joint coding plus immutable additive links raises complete evidence from 970 to
**973**, with **3 gains and 0 losses** (`p=.25`). The locked signal bar requires
at least five gains, so the result is below threshold.

Gains occur one each in conv-43, conv-49 and conv-50. The other conversations
tie control; every cell is nonnegative. Direct remains 935 and the one-hop
ceiling remains 986.

## Mechanism

The codec recovers median 480.5 characters (p10 306.7, p90 660.3) and admits
2,582 extra actions: 1,544 pairs and 1,038 singleton turns. Only six added
actions carry missing evidence, completing three questions.

Decisive payloads cost median 244.5 characters versus 189 for all additions.
Their seed rank median is 8.5 and original-order position median is 2. Capacity
reaches some useful shallow skipped carriers, but most newly admitted text is
not answer evidence. The remaining gap is 13 items to the fixed one-hop ceiling.

This is a clean no-displacement result: every control payload remains present,
so zero losses are structural rather than predicted. The limited conversion
from 2,582 admissions to three completions shows that phrase capacity alone is
no longer the main NF bottleneck.

## Boundary

The exact phrase codec uses only 2–6-word, at-most-80-character dictionary
entries and pays declarations. A stronger representation may test
declaration-free backward span references while retaining the immutable-pack
invariant. This result does not authorize changing order or selecting additions
with outcome labels.

Blind selection SHA-256 is
`705a156aacb7143f7b23c9b1297701235c1b3c02ec567580f4b81c35e7114bd7`;
outcomes replay byte-identically at
`31327315b661a0a50728dd561e577df6044df7817ec4856f5d608fb2212bd5df`.
There were zero model, embedding and cache calls. Reader interpretation of
dictionary references remains untested; no tuning or adoption follows.

