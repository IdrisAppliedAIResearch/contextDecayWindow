# Saved T1 trace inspection

Plan anchor: d9377308. POSTHOC descriptive inspection; no new inference, counterfactual allocation, scoring or changed Study D result.

Frozen-packer replay exactly reproduces temporal and final selection IDs for all 32 immediately-before traces. Sixteen have complete support and sixteen do not. All temporal admissions survive final packing. All 16 missing cases have the correct meeting (turn 45) delivered, with the required update (turn 44) eligible. None admit that update in the 8k temporal selection or the final 32k retrieval selection.

Missing-target temporal ranks are 20-39 (including anchor); global CC80 ranks 47-87; merged final ranks 48-88. Whole-record marginal costs are 693-703 chars. At the target attempt, temporal capacity remaining is 292-323 and final capacity remaining is 537-676. Thus all 16 are exact fit rejections under the selected ranking and budget, not missing anchors, excluded source facts, absent storage, or removal of an already-admitted temporal record.

Positive controls: 16 complete cases, nine targets admitted by temporal selection and seven recovered during final CC80 fill. Their global target ranks are 5-45. Both populations exist and replay exactly; this is a joint rank/packing/budget finding, not independent causal attribution to any one factor.

Mechanism distinction: latest queries sort matched subject records by descending turn. Before queries identify a unique anchor, filter subject records to earlier turns, then retain CC80 similarity order, with the anchor prepended. They do not sort by proximity to the boundary. This is the registered implementation, not a new code defect or a basis to edit the locked run.

Example session-92003: target turn44 ranks 24 in temporal order (699-char cost; 313 remaining), then 60 in merged order (699 cost; 660 remaining). Anchor turn45 is delivered, target is omitted.

Implication for DA fusion: finer packing is relevant, but a nearest-prior-update order is a separate, more direct hypothesis. No counterfactual was executed. The 105-char setting sentence is inside a 595-605-char user message plus a 29-char acknowledgment and serialization. DA individual-message granularity would not by itself separate that sentence from the operational prose in the same user message. Sentence extraction or lossless text compression is a different intervention, with its own exact reader cost and semantic fidelity requirements.

All required target updates happen at turn44 in this generator; do not hardcode that ordinal or generalize this pattern to arbitrary histories. Thirty-seven existing primary responses still failed despite complete support; repairing availability does not establish their recovery. Any new architecture test must measure actual reader answers.

Artifacts: inspect_traces.py and trace_inspection.json preserve input hashes, every row, exact attempt costs, ranks and fit decisions. No original source, mechanism, score or registration artifact changed.
