# E006 Part 3 Query-Anchored Associative-Frontier Retrieval Report

**Date:** August 10, 2026
**Outcome:** **NO_DIFFERENTIATED_CUE - CHARACTERIZED**
**Pre-registration commit:** `12f5a3f2`
**Final design commit:** `80a5886a`
**Final design SHA-256:** `50DC8F74EA08CD41A92E8DD40360496A79BFCCB7C2F11DA8C424A192F8227030`
**Authorization commit:** `5e905f15`
**Preflight artifact commit:** `81299313`
**Parameter lock commit:** `ceb25d48`
**S4 execution commit:** `88ec1797`
**Results:** `artifacts/e006_p3_s4/results.json`
**Results SHA-256:** `5A6B8A6731B813E0BF63071838D1B14CEAF41362D6548C0BCED9777E2BBE49EF`
**Manifest SHA-256:** `8FC2E5179012582D8785DF020409BFC6A019D6C4F1D1A49E67D471A0C7463D15`
**Calls:** 48 embedding requests for the authorized historical-input repair;
zero additional embedding calls and zero model-generation calls

## 1. Gate Record

The draft was refactored into a committed exploration pre-registration before
implementation. Part 1 then found that Tier 4A had not persisted the 48 query
vectors needed for exact historical reproduction. Rev 1 authorized exactly 48
embedding requests to seal those missing inputs before any Q11 labels opened.

The first reproduction stopped at `114/144` Tier 4A rows. The failed artifact
was committed before Rev 2 identified that the auditor imported NumPy before
setting the registered single-thread environment. After the prospective runtime
repair, Tier 4A reproduced `144/144` rows and A1 reproduced `8/8` cells by
identity and payload digest.

Label-blind exploration then passed. The graph has 119 nodes, 676 retained
undirected edges, one connected component, and zero isolates. A2 is
mechanically distinct from Tier 4A global PPR and from A1's mean-context chain.
All registered degenerate traces executed, and the primary A0/A1/A2 cells each
admit 15 candidates while selecting 11/12/15 episodes and delivering
31,957/28,562/29,987 characters.

PF1-PF10 passed before the parameter lock and measurement run. PF7 passed all
16 feedback cells; there were no repeated candidate identities or frontiers,
no query-only selected fallback, and no constant-association cell. The evidence
runner reproduced all 24 exploration candidate, selected, and payload identities
before importing Q11 measurement.

## 2. Primary Result

The registered primary cell is `D=2, m=5` under the 32,000-character budget.

| Arm | Candidate facts | Candidate domains (civil/art/monetary/marine) | Packed facts | Packed domains (civil/art/monetary/marine) | Candidates | Selected | Characters |
|---|---:|---|---:|---|---:|---:|---:|
| A0 fixed query | 9 | 5/0/1/3 | 7 | 3/0/1/3 | 15 | 11 | 31,957 |
| A1 mean context | 9 | 5/0/1/3 | 9 | 5/0/1/3 | 15 | 12 | 28,562 |
| A2 local frontier | 5 | 5/0/0/0 | 5 | 5/0/0/0 | 15 | 15 | 29,987 |

`CUE_DIFFERENTIATED` fails: A2 has four fewer candidate facts than each
control and regresses in the monetary and marine domains. The first ordered
disposition therefore fires as `NO_DIFFERENTIATED_CUE`; later delivery rules
cannot rescue it. `DELIVERY_DIFFERENTIATED` also fails descriptively.

The local frontier does not preserve a bridge missed by the controls. It
collapses onto the civil neighborhood, returns no art, monetary, or marine facts
at the primary cell, and trails both controls despite equal candidate count.

## 3. Secondary Results and Predictions

A2's best packed availability is `6/17` at `D=3, m=5`, comprising five civil
facts and one monetary fact in 31,117 characters. No A2 cell retrieves an art
fact, and no A2 cell exceeds E005's historical `12/17`. A1 reaches `9/17` at
both `D=2, m=5` and `D=3, m=5`.

| # | Registered prediction | Result |
|---:|---|---|
| 1 | Historical Tier 4A and A1 reproduce | Pass: `144/144` and `8/8` |
| 2 | Equal primary candidate counts but unequal volume | Pass |
| 3 | A2 passes `CUE_DIFFERENTIATED` | Fail |
| 4 | A2 does not pass `DELIVERY_DIFFERENTIATED` | Pass |
| 5 | Every A2 cell has zero packed art facts | Pass |
| 6 | No A2 cell exceeds E005's historical `12/17` | Pass |
| 7 | A2 plateaus by depth 2 within one packed fact | Pass |
| 8 | At least four of six `D>0` arm triplets have unequal characters | Pass: 6/6 |

Two complete in-process evaluations produced the same result digest,
`75be1c005484f2dd8b02cc457907346ad177b9e56870fe101fb9e0404468e9d0`.
All 24 payloads match their recorded raw UTF-8 SHA-256 and exact character
count, and the artifact manifest covers all 27 result files.

Closeout verification passes 54 focused E006 Part 2/P3 integrity tests and the
complete repository suite, `1428/1428`.

## 4. Interpretation and Boundary

Under the registered Q11 diagnostic, query-anchored local-frontier propagation
does not separate positively from fixed-query retrieval or mean-context
chaining once exact delivered volume is exposed. Equal candidate quotas do not
certify equal evidence opportunity, and local graph continuity can reinforce a
single-domain neighborhood rather than recover breadth.

Tier 4A already refuted advancement for global PPR traversal over observed
co-activation edges and an exact-cosine top-8 graph. This diagnostic does not
reopen that result. It tests a different propagation operator over the same
broad cosine-graph family, with a matched-volume fixed-query control and the
E006 exact packing path. Any result remains `CHARACTERIZED`.

This is offline availability on one Q11 probe. The eight targeted probes still
lack committed full cosine traces; no answer was generated or scored. The result
authorizes no targeted claim, live run, promotion, adoption, or deployment
change.
