# AR-001 Q11 Achievability Audit

**Design commit:** `b48e7501e733d56f94cd5ba442c1e5ce950439f2`
**Execution commit:** `15cdb1770d2dc935f7fa23f5df2779b40bd45e0d`
**Status:** **ACHIEVABLE_AT_32K**

## Result

The exact minimum for at least 14/17 Q11 items is **5,058 characters** across **5 episodes**, leaving **26,942 characters** of headroom against 32,000. The 14/17 bar exists within the enforced budget.

Greedy reached 15/17 at 5,455 characters, 397 above the exact optimum.

Omitted by the exact threshold optimum: art:Melozzo da Forli, art:Cardinal Giuliano della Rovere, art:1483.

## Domain Optima

| Domain | Facts | Minimum payload chars | Episodes | Turns |
|---|---:|---:|---:|---|
| civil | 5/5 | 826 | 2 | 112, 113 |
| art | 4/4 | 3,182 | 1 | 55 |
| monetary | 4/4 | 2,913 | 1 | 90 |
| marine | 4/4 | 824 | 1 | 118 |

Domain optima are independent and non-additive because wrappers and episodes can overlap.

## Exact Threshold Set

| Turn | Episode | Element chars | Q11 items present |
|---:|---|---:|---|
| 90 | `1dec9c9e-b948-4ef8-9eaa-aa889c083470` | 2,861 | monetary:Taylor Rule; monetary:Federal Reserve; monetary:Dr. Priya Mehta; monetary:2.3% |
| 112 | `5c4446e4-fc4b-40f8-8b27-04cb33c7be57` | 416 | civil:Halcyon Crossing; civil:847; civil:S460ML |
| 113 | `dd904725-094b-4f94-a8fc-ca18668ad246` | 357 | civil:Halcyon Crossing; civil:Dr. Anara Bekova; civil:92.4 |
| 115 | `7307e832-370a-43ea-b25b-449f929de49e` | 596 | art:The Annunciation of Forli |
| 118 | `77a1d148-12da-4a70-874d-42e816497c9a` | 772 | marine:Vampyroteuthis infernalis; marine:Dr. Kenji Watanabe; marine:600; marine:marine snow |

## Integrity

- Eligible committed episodes: 119.
- Episodes containing at least one Q11 item: 76.
- Store coverage: 17/17; missing: 0.
- Exact additive cost equals the complete rendered payload length.
- Dynamic programming is covered by a synthetic exhaustive-subset test.
- In-memory deterministic rerun: PASS.
- No model, embedding, retrieval, local database, or inference call.

## Interpretation Boundary

This audit determines bar achievability only. It does not change E002's registered KILL or establish that a deployable retriever can find the optimum set without answer-key access.
