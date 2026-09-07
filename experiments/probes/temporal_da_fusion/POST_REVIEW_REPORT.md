# Post-review removal reader probe

Plan5085934f; implementation82d82e90; inputgatee4038d78; calibration915cb214. Failure-selected diagnostic, no production change.

Removing post-review records recovers **22/22** previously wrong answers; **0** remain wrong.

Each treatment retains exactly the already retrieved records through the existing selector-identified review anchor. No gold labels choose the cutoff; no preceding selected record is changed or newly admitted. Full original native prompts reproduce22/22. The review itself remains. Same native-off Qwen reader,HH001,seed5005,serial/cachefalse,4096 output,32768 context and sampling.

Retained records range55–95; removed records range15–55. All22 responses complete. Measurement takes91.6seconds and generates61output tokens.

All source evidence was already present in the original wrong prompts. Recoveries show sensitivity to the removed later history under this intervention. Shorter input and removal of specific distractors are bundled; no internal reasoning cause is identified. These22 are selected failures and the original arm is historical rather than a fresh repeated control. Do not extrapolate this recovery rate to all questions or claim broader generalization.

All22 answers scored canonically; no prose adjudication was needed. No human or three-pass audit. Raw captures were committed before scores, resolved scores before this report. Negative input gate and parser fixtures and duplicate arithmetic45 calibration preceded inference.

| Question | Gold | Original wrong answer | Prefix answer | Correct |
|---|---|---|---|---|
| What was the delivery location for "Meadow-637" immediately before "Meadow-637 review"? | depot | studio | depot | 1 |
| What was the delivery location for "Orchard-892" immediately before "Orchard-892 review"? | studio | depot | studio | 1 |
| What was the delivery location for "Harbor-580" immediately before "Harbor-580 review"? | workshop | The delivery location for "Harbor-580" immediately before the "Harbor-580 review" meeting was the depot. | workshop | 1 |
| What was the delivery location for "Harbor-795" immediately before "Harbor-795 review"? | warehouse | The delivery location for "Harbor-795" immediately before the "Harbor-795 review" was the depot. | warehouse | 1 |
| What was the delivery location for "Riverside-152" immediately before "Riverside-152 review"? | depot | annex | depot | 1 |
| What was the delivery location for "Harbor-269" immediately before "Harbor-269 review"? | annex | office | annex | 1 |
| What was the delivery location for "Riverside-405" immediately before "Riverside-405 review"? | depot | office | depot | 1 |
| What was the delivery location for "Harbor-374" immediately before "Harbor-374 review"? | annex | warehouse | annex | 1 |
| What was the delivery location for "Meadow-327" immediately before "Meadow-327 review"? | warehouse | depot | warehouse | 1 |
| What was the delivery location for "Meadow-840" immediately before "Meadow-840 review"? | warehouse | The workshop | warehouse | 1 |
| What was the delivery location for "Harbor-553" immediately before "Harbor-553 review"? | laboratory | The delivery location for "Harbor-553" immediately before the "Harbor-553 review" meeting (turn 92) was the workshop. | laboratory | 1 |
| What was the delivery location for "Meadow-940" immediately before "Meadow-940 review"? | depot | studio | depot | 1 |
| What was the delivery location for "Riverside-281" immediately before "Riverside-281 review"? | hangar | The delivery location for "Riverside-281" immediately before the "Riverside-281 review" (which occurred at turn 93) was the **laboratory** (set at turn 90, with no changes in turns 91 and 92).  Answer: laboratory | hangar | 1 |
| What was the delivery location for "Harbor-152" immediately before "Harbor-152 review"? | workshop | studio | workshop | 1 |
| What was the delivery location for "Harbor-788" immediately before "Harbor-788 review"? | workshop | studio | workshop | 1 |
| What was the delivery location for "Riverside-978" immediately before "Riverside-978 review"? | annex | warehouse | annex | 1 |
| What was the delivery location for "Meadow-219" immediately before "Meadow-219 review"? | workshop | office | workshop | 1 |
| What was the delivery location for "Orchard-428" immediately before "Orchard-428 review"? | laboratory | The workshop | laboratory | 1 |
| What was the delivery location for "Harbor-447" immediately before "Harbor-447 review"? | hangar | The delivery location for "Harbor-447" immediately before the "Harbor-447 review" meeting (turn 92) was the **studio** (set in turn 83, with no changes in turns 84-91). | hangar | 1 |
| What was the delivery location for "Harbor-493" immediately before "Harbor-493 review"? | studio | office | studio | 1 |
| What was the delivery location for "Riverside-604" immediately before "Riverside-604 review"? | hangar | laboratory | hangar | 1 |
| What was the delivery location for "Orchard-199" immediately before "Orchard-199 review"? | annex | The laboratory | annex | 1 |

Full artifacts: [reader directory](relevance_artifacts/post_review_reader). No changes to prior scores or retrieval defaults.

Raw captures71ee6741; canonical scorese6d16320; resolved175d6039 before aggregation. All22 gold source sets and literal statements survived unchanged (support_preserved.json). Owned server17168 verified/stopped.
