# BEAM-001 Part 1 Exploration

**Status:** PASS  
**Outcome surface:** sealed; no ideal answer, rubric, evidence location, prior result, reader call or judge call was opened  
**Question-arms:** 5,400 (1,800 questions x 3 arms)

## Corpus and mechanism

The admitted normal-scale population is 90 conversations and 1800 questions: 100K=20, 1M=35, 500K=35. Strict adjacent user/assistant pairing remained lossless.

A0 is the public CC80 default with additive last-32 continuity. C0 is the public static ASPECT option. T1 gives every half-budget CC80 parent one finite child opportunity, retaining it only when its marginal value covers the CC80 value displaced by exact packing. All three use the same cached Qwen embeddings and CC80 ranking; Part 1 loaded no model.

## Overall mechanics

| Arm | LT episodes median / p95 | Retrieval chars median / p95 | Latency median / p95 (s) |
|---|---:|---:|---:|
| A0 | 8 / 12 | 31,744 / 31,982 | 0.1591 / 0.4355 |
| C0 | 9 / 13 | 31,640 / 31,970 | 0.3097 / 0.9056 |
| T1 | 9 / 12 | 31,752 / 31,980 | 0.5520 / 1.7393 |

## Pair contrasts

| Pair | Selection identical | Changed | Payload identical |
|---|---:|---:|---:|
| A0_C0 | 13 | 1,787 | 0 |
| C0_T1 | 47 | 1,753 | 31 |
| A0_T1 | 424 | 1,376 | 59 |

## Viability gates

- **G-SCHEMA: PASS.** 90 conversations and 1800 questions mapped losslessly.
- **G-SEPARATION: PASS.** Planted outcome fields were rejected and the exploration import graph had no outcome reader.
- **G-ANCHOR: PASS.** The committed CC-007 and TC-014 identity/payload anchors passed before exploration.
- **G-BASELINE: PASS.** 1800/1800 A0 rows used no ASPECT trace or protected allocation.
- **G-TREATMENT: PASS.** C0/T1 produced 1753 changed and 47 identical selected sets.
- **G-BUDGET: PASS.** 5400/5400 rows stayed within 32,000 retrieval characters with disjoint recent/LT identities.
- **G-RUNTIME: PASS.** The full run and shuffled replay completed with 19 peak processes and 12139270144 peak aggregate working-set bytes.

## Degenerate states

Real witnesses and explicit absences are recorded by stable key in `artifacts/exploration/trace_audit.json`. The shuffled replay processed every conversation in a changed question order and reproduced every payload digest. T1 made exactly one finite outcome per parent; proposed children were unique and never re-entered as parents.

## Preflight checklist

- **PF1 Inputs:** source revisions, licenses, hashes, counts, parser, embedder, package tree and anchors are hash-bound in the manifests listed below.
- **PF2 Mechanism identity:** the corpus adapter and all retrieval components are stated falsifiably above and verified in the trace audit.
- **PF3 Gate ordering:** source lock, surface separation and reproduction anchors precede this report. The live registration and implementation do not yet exist, and no reader or judge call has occurred.
- **PF4 Reachability:** 1,800 paired questions exist across ten balanced families and three scales. Exact scoring units, practical bars, statistical branches and synthetic dispositions must be frozen in the standalone live registration after the outcome schema is opened.
- **PF5 Stable keys:** content-hash keys survived canonical rebuilds, path-independent adapter tests, duplicate occurrences and the complete shuffled replay.
- **PF6 Reproduction:** all 871 TC-014 opportunity identities/payloads and all 4,355 CC-007 trace groups passed before BEAM summaries.
- **PF7 Feedback:** all 5,400 shuffled payload digests match; read-only store counters remained unchanged; every T1 parent terminated once with no child re-entry.
- **PF8 Adequacy:** this population can size a normal-scale paired BEAM test only. It cannot establish 10M behavior, real-user transfer, reader generality or production-concurrency latency.
- **PF9 Surrogates:** child count, facet breadth, overlap, speed, compactness and evidence availability can all improve while reader correctness falls. None authorizes adoption.
- **PF10 Live requirement:** only the separately registered complete GPT-4o mini reader and blind scoring run can test T1 versus C0 with the required A0 non-regression guardrail.

## Artifact anchors

- `contexts`: `1ece50518448b19dc3b4ae4eb2c9d5d51a9417263f8070e98f58fee05ea3b8ae`
- `rankings`: `82e89405d0ba5de52b7b6c4c2e542b3ae0974716289596c6e8178b6f19625c6a`
- `facet_representation`: `4a4c03d65b0dcb476f4d7703091b3cbce0fa5de70e430c57ac65c4913439aad8`
- `shuffle_replay`: `ec047d13b1bc3cdab497c53aec4da935c603468d5154696fbd7d1adcab19e4bc`
- `resources`: `9ab161c7c43cdee1996bdffacf678459f0d51d2ee9bc99f77f3d04a45e9cf3e3`
- `schema_report`: `1ea9269ab7241ba1b1a693dae5036faae82e5bab6c4cceaf7147d0304658c0f3`
- `source_manifest`: `c648d36d3519f3a45192534e50c43092e620c493ea745f9ff51737a3b8d3e942`
- `surface_manifest`: `3daa18d3019ebae7797072d1de9a673cc85e32080d8695d83a2801b8100c4c90`
- `reproduction_anchor`: `42edcca2ec614fd3500a4d624521b67f0cd6ed680c517e0a4af9bcdd00d8506f`
- `distributions`: `bbf3fc07cec299f17ce5a869a1d3767ec28a04341263e37ab5523fbded7fea90`
- `trace_audit`: `17063f72eb5a038ddcd971886d06173060194a15f222bddfcae90d6312ca20dd`

Part 1 establishes mechanical viability only. It contains no answer-quality result.
