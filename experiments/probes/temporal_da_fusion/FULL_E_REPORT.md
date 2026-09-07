# Full Study E single-arm relevance reader

Plan SHA: 2519aff9. EXPLORATORY expanded validation, September6,2026. No new control, generalization verdict, or production adoption.

The frozen uncapped cosine>=.48 plus anchor chronological timeline scores **106/128 (82.8125%)** on immediately-before questions. Latest and absence score32/32 each; total170/192 (88.5417%). All22 wrong answers have complete required evidence delivered.

## Results

| Stratum | Correct | Accuracy |
|---|---:|---:|
| straight | 23/32 | 71.88% |
| irrelevant | 29/32 | 90.62% |
| future | 27/32 | 84.38% |
| proposal | 27/32 | 84.38% |
| latest | 32/32 | 100.00% |
| absent | 32/32 | 100.00% |
| before | 106/128 | 82.81% |
| all | 170/192 | 88.54% |

The prior16-question sample scores15/16 again (before11/12 and four guards correct); the remaining176 score155/176. The remainder is not a sealed holdout: its offline evidence and source family informed development. This run expands reader coverage, not generalization evidence.

## Setup and interpretation

All192 distinct E questions receive one fresh answer at seed5005. Full source records with raw query cosine>=.48 are unioned with existing anchors and sorted chronologically. No retrieval count/character cap, additive last32, compression or new embeddings. The same HH001 payload and pinned Qwen3.8-27B UD-Q4_K_XL reader are used as the small relevance probe. Native thinking remains OFF; output allowance4096 and context32768; serial/cachefalse and carried sampling unchanged.

Availability is160/160 across answerable questions (128before plus32latest), with absence not assigned a positive-evidence denominator. This establishes delivery on this exposed synthetic corpus. The22 before errors remain evidence-use failures under this reader setting; no causal explanation of its internal process is established. The full before score is lower than the small sample’s11/12. A single arm cannot isolate causal gains over historical controls, whose presentation/output allowance/replication differed. Earlier Study E confirmation remains unchanged.

## Runtime and scoring

Measurement took 17.68 minutes. Actual output consumption was 2,200 tokens total, median 3, maximum 414. Median input was 18015, maximum 18707; every input fit uncropped. All192 stopped at EOS, none truncated. The owned server26204 was verified and stopped.

179 final answers were scored by the unchanged canonical scorer;13 prose exceptions received authorized single-agent judgments (8correct,5incorrect). Three correct prose responses explicitly retract a wrong opening and end with the correct answer. Scoring follows final conclusions, not every explanatory claim. No independent three-pass or human audit is claimed. This deviation carries prior user authorization.

Integrity sequence: plan2519aff9; implementation7ec5b2bc; inputgatef9b47817; duplicate arithmetic calibrationd0280749; raw completeness52d61701; mechanical scoresdaee2ce6; judgments024bed06; resolved scores7fe9b86a before aggregate. Exact192 source/threshold replays and16 native prompt identities pass; negative gate and parser fixtures preceded inference. Frozen worktrees were clean. No automatic retries, parameter tuning or label-dependent selector changes.

## Every incorrect answer

All rows below have complete required evidence in the supplied timeline. Full source context, raw output, scores and gold answers remain in the linked artifact directory.

| Question | Type | Expected | Returned final response |
|---|---|---|---|
| What was the delivery location for "Meadow-637" immediately before "Meadow-637 review"? | future | depot | studio |
| What was the delivery location for "Orchard-892" immediately before "Orchard-892 review"? | irrelevant | studio | depot |
| What was the delivery location for "Harbor-580" immediately before "Harbor-580 review"? | straight | workshop | The delivery location for "Harbor-580" immediately before the "Harbor-580 review" meeting was the depot. |
| What was the delivery location for "Harbor-795" immediately before "Harbor-795 review"? | straight | warehouse | The delivery location for "Harbor-795" immediately before the "Harbor-795 review" was the depot. |
| What was the delivery location for "Riverside-152" immediately before "Riverside-152 review"? | proposal | depot | annex |
| What was the delivery location for "Harbor-269" immediately before "Harbor-269 review"? | straight | annex | office |
| What was the delivery location for "Riverside-405" immediately before "Riverside-405 review"? | proposal | depot | office |
| What was the delivery location for "Harbor-374" immediately before "Harbor-374 review"? | straight | annex | warehouse |
| What was the delivery location for "Meadow-327" immediately before "Meadow-327 review"? | future | warehouse | depot |
| What was the delivery location for "Meadow-840" immediately before "Meadow-840 review"? | future | warehouse | The workshop |
| What was the delivery location for "Harbor-553" immediately before "Harbor-553 review"? | straight | laboratory | The delivery location for "Harbor-553" immediately before the "Harbor-553 review" meeting (turn 92) was the workshop. |
| What was the delivery location for "Meadow-940" immediately before "Meadow-940 review"? | future | depot | studio |
| What was the delivery location for "Riverside-281" immediately before "Riverside-281 review"? | proposal | hangar | The delivery location for "Riverside-281" immediately before the "Riverside-281 review" (which occurred at turn 93) was the **laboratory** (set at turn 90, with no changes in turns 91 and 92).  Answer: laboratory |
| What was the delivery location for "Harbor-152" immediately before "Harbor-152 review"? | straight | workshop | studio |
| What was the delivery location for "Harbor-788" immediately before "Harbor-788 review"? | straight | workshop | studio |
| What was the delivery location for "Riverside-978" immediately before "Riverside-978 review"? | proposal | annex | warehouse |
| What was the delivery location for "Meadow-219" immediately before "Meadow-219 review"? | future | workshop | office |
| What was the delivery location for "Orchard-428" immediately before "Orchard-428 review"? | irrelevant | laboratory | The workshop |
| What was the delivery location for "Harbor-447" immediately before "Harbor-447 review"? | straight | hangar | The delivery location for "Harbor-447" immediately before the "Harbor-447 review" meeting (turn 92) was the **studio** (set in turn 83, with no changes in turns 84-91). |
| What was the delivery location for "Harbor-493" immediately before "Harbor-493 review"? | straight | studio | office |
| What was the delivery location for "Riverside-604" immediately before "Riverside-604 review"? | proposal | hangar | laboratory |
| What was the delivery location for "Orchard-199" immediately before "Orchard-199 review"? | irrelevant | annex | The laboratory |

## Artifacts and next step

Artifacts: [full reader directory](relevance_artifacts/full_e_reader), including schedule.json, input_gate.json, complete.json, scores.json, agent_judgments.json, scores_resolved.json, scoring_gate_resolved.json and result.json. Result rows contain all192 answers and evidence status.

Keep the setup frozen for any transfer test. The next diagnostic can examine the22 complete-evidence errors, while an untouched natural-conversation temporal set is needed to evaluate broader generalization. No threshold adjustment or extra inference was performed at closeout.
