# Full E immediately-before miss audit

Plan16f1820b; implementation7a5b71ed. Offline audit only; no new inference or score changes.

All22 incorrect answers were checked against literal scheduled reader prompts, full source records and gold statements. All22 source-to-prompt replays pass. Independently choosing the last explicit effective update before the review agrees with all22 references. Target raw cosine ranges0.597031–0.741467, above.48; there is no target-threshold miss. Anchors and required qualifiers are present.

17/22 wrong values match the first explicit location update after the review.8/22 match the update immediately preceding the correct target.9/22 match an unaccepted proposal or future announcement near the anchor (all9 also match the later update). These counts overlap; recurrent values prevent identification of which record drove an answer. The two cases matching neither adjacent alternative, Orchard892 and Orchard428, still match older effective locations. One target record contains the wrong value in its operational filler; this does not establish filler causality.

The leading hypothesis is incorrect temporal state selection despite complete evidence, especially using a later state. Retrieval absence and a target cutoff failure are ruled out for these22. Native thinking was off; matching emitted values does not expose the model’s internal process.

Corpus caveat: four wrong future cases (Meadow327,Meadow840,Meadow940,Meadow219) contain a statement that the announcement is explicitly not effective anywhere in the recorded history, followed after the anchor by an explicit update to the same location. The later update might be a separate decision, but the wording is potentially confusing. The latest effective state strictly before the anchor remains unambiguous and agrees with gold. This audit does not change scores or isolate the effect of that wording.

| Case | Type | Correct update | Review | Wrong | Previous state match | First later update |
|---|---|---:|---|---|---|
| Meadow-637 | future | 76: depot | 85 | studio | yes | 89: workshop |
| Orchard-892 | irrelevant | 54: studio | 60 | depot | no | 99: warehouse |
| Harbor-580 | straight | 61: workshop | 68 | depot | no | 75: depot |
| Harbor-795 | straight | 51: warehouse | 56 | depot | yes | 71: depot |
| Riverside-152 | proposal | 59: depot | 64 | annex | yes | 66: annex |
| Harbor-269 | straight | 52: annex | 62 | office | no | 70: office |
| Riverside-405 | proposal | 50: depot | 58 | office | no | 66: office |
| Harbor-374 | straight | 87: annex | 92 | warehouse | yes | 95: warehouse |
| Meadow-327 | future | 62: warehouse | 71 | depot | no | 73: depot |
| Meadow-840 | future | 64: warehouse | 76 | workshop | no | 80: workshop |
| Harbor-553 | straight | 82: laboratory | 92 | workshop | no | 95: workshop |
| Meadow-940 | future | 64: depot | 70 | studio | no | 75: studio |
| Riverside-281 | proposal | 81: hangar | 93 | laboratory | no | 102: laboratory |
| Harbor-152 | straight | 63: workshop | 72 | studio | no | 81: studio |
| Harbor-788 | straight | 57: workshop | 69 | studio | no | 79: studio |
| Riverside-978 | proposal | 59: annex | 69 | warehouse | no | 76: warehouse |
| Meadow-219 | future | 43: workshop | 55 | office | no | 64: office |
| Orchard-428 | irrelevant | 83: laboratory | 89 | workshop | no | 95: annex |
| Harbor-447 | straight | 84: hangar | 92 | studio | yes | 100: annex |
| Harbor-493 | straight | 88: studio | 95 | office | yes | 99: office |
| Riverside-604 | proposal | 51: hangar | 56 | laboratory | yes | 74: laboratory |
| Orchard-199 | irrelevant | 62: annex | 67 | laboratory | yes | 71: warehouse |

Artifact: [misses_audit.json](relevance_artifacts/full_e_reader/misses_audit.json) contains literal intervening statements, source matches, cosines and input hashes. First execution stopped at a missing Python Path import before checks/output; fixed in7a5b71ed and rerun without changing design or artifacts.

Next diagnostic, if pursued: a small paired reader probe preserving all pre-anchor evidence while removing post-anchor records would test sensitivity to later history. A separate thinking-enabled probe could test reader recovery. Neither was run here; do not change the relevance threshold to repair these evidence-use errors.
