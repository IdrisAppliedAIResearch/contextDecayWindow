# DA-082 Scratchpad

## 2026-08-31 - Diagnostic Lock

- Exact 13-row DA-079 population.
- Frozen DA-078 prompt membership and DA-045 baseline/frontier edges.
- States: present sibling, unary represented seed, or branch ambiguous.
- No text feature, score, threshold, answer, or edge-order change.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- States: 12 branch ambiguous, 1 present sibling, 0 unary represented seed.
- Every requirement has one matching seed.
- Represented-seed minimum branch degree p50 2/p90 4.
- The sibling case is already lexical-novel; union coverage does not increase.
- Payload-only frames omit the parent relation; explicit edge provenance is the
  next structural signal.
- Byte-identical replay; zero calls.
