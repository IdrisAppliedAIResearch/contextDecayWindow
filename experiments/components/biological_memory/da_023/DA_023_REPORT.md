# DA-023 Immutable Backward Span References Report

**Status:** `BACKREFERENCE_DELIVERY_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `88215376`
**Blind allocation commit:** `19d480c9`
**Standing:** spent cross-corpus exact-availability result

## Result

Declaration-free exact backreferences clear the registered +5/zero-loss bar on
both corpora while retaining every strongest-control payload.

| Corpus | Control | Treatment | Gains | Losses | Exact p |
|---|---:|---:|---:|---:|---:|
| NF-004 | 970 | **976** | 6 | 0 | .03125 |
| LongMemEval | 188 | **202** | 14 | 0 | .000122 |

All NF conversations and LongMem question types are nonnegative. NF gains are
two each in conv-30/43 and one each in conv-49/50. LongMem gains are knowledge
update 3, multi-session 2, single-session-user 3 and temporal reasoning 6.

## Capacity Mechanism

Backward references recover substantially more immutable baseline capacity than
declared phrases:

- NF median 1,028.5 chars (p10 826, p90 1,272), admitting 4,799 payloads.
- LongMem median 546 chars (p10 159.6, p90 1,024.8), admitting 694 payloads.

NF has 15 evidence-carrying added actions and six completions; LongMem has 22
and 14. Decisive payload cost medians are 272 and 265 characters. Decisive seed
rank medians are 9 on both; strongest-order positions are 3 and 5.5.

The representation succeeds because references pay no dictionary declaration
and can copy arbitrary exact spans, including punctuation and sequences longer
than DA-015's 2–6-word window. LongMem therefore regains capacity even after its
direct-derived phrase dictionary had nearly saturated.

Zero losses are structural, not predicted: direct and strongest linked payloads
remain exact and ordered; additions consume only recovered characters.

## Ceiling and Boundary

NF remains 10 below its one-hop ceiling of 986. LongMem remains 48 below 250.
More encoded capacity may not convert linearly: NF needed 4,799 admissions for
six gains, while LongMem needed 694 for 14. A residual audit should determine
whether remaining misses are initial payload size, prior additive consumption,
wrong singleton member, conjunction or reachability before extending the codec.

The reference syntax is machine-decodable but reader interpretation is untested.
The exact longest-match implementation is also slow and has no production
latency claim.

Blind allocation SHA-256 is
`2982a79056945933267525701281ce8ae7882224ad5e9f2427e008c53fa221e4`;
outcomes replay byte-identically at
`7d3a5f7a44dacc8b7b6a2a383f716b2a6b5b71dce21778f90bdbd9566013c4fd`.
There were zero model, embedding and cache calls. No adoption follows.

