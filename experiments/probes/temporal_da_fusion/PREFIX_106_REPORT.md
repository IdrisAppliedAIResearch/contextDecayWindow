# Prefix preservation on 106 previously correct before questions

Plan c6f99a6; implementation f13f6f75; input gate b94b1040; calibration c2218867; raw f7480f6f; canonical scores ab5d9a8e committed before aggregation.

The cutoff preserves **104/106** previously correct answers, with two regressions. Combined with the previous22/22 recovered misses, the same prefix configuration scores **126/128 (98.4375%)**, versus106/128 (82.8125%) for the full timeline:22gains,2losses,net20 (+15.625 percentage points).

This is a descriptive result assembled from two sequential diagnostic batches partitioned by previous correctness, not an independent confirmation. All128 distinct before questions are covered exactly once with prefix treatment. Latest and absence were not rerun under this cutoff. No production adoption or generalization claim.

## Regressions

| Question | Gold | Prefix answer |
|---|---|---|
| What was the delivery location for "Orchard-186" immediately before "Orchard-186 review"? | hangar | depot |
| What was the delivery location for "Harbor-371" immediately before "Harbor-371 review"? | workshop | depot |

All required source ids and literal gold statements remain in both regression prompts, as verified for all106 treatments before inference. No additional cause diagnosis or inference was performed.

## Combined before results

| Type | Correct |
|---|---:|
| straight | 31/32 |
| irrelevant | 31/32 |
| future | 32/32 |
| proposal | 32/32 |

## Integrity and runtime

Identical prefix rule: retain only already selected full records at or before the existing selector-identified review anchor, including the review. No preceding record changes, additions, threshold tuning or gold-based cutoff. Original106 native prompts replay exactly, previous22 transformed contexts replay exactly, and the two sets are disjoint with union equal to128before questions. Runtime binary manifests and launch commands match between batches.

Same native-thinking-OFF reader,HH001,seed5005,serial/cachefalse,4096output allowance,32768context and prior sampling. Input/negative gate, parser and duplicate arithmetic calibration passed before measurement. All106 responses completed and scored canonically; no prose adjudication was needed. Raw capture hashes were verified before scoring.

The106 calls took6.54minutes and generated274output tokens. Including the prior22, prefix measurement totaled484.15seconds and335output tokens across128questions. Owned server3856 was verified and stopped.

The improvement supports temporal-boundary restriction as a useful intervention on this corpus. It does not separate shorter input from removal of particular later statements, and two regressions show that it is not uniformly beneficial. Earlier studies and scores remain unchanged.

Artifacts: [result with all106 answers](relevance_artifacts/prefix_106_reader/result.json), scores.json,scoring_gate.json,complete.json,support_preserved.json and schedule.json in the same directory. Prior22 results remain in post_review_reader.
