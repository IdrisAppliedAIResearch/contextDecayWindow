# DR-001 Pre-Fix Replay and Expansion Measurement

**Design commit:** `094cbea2`  
**Amendment commit:** `ad74b991`  
**Execution commit:** `ad74b991`  
**G-R1:** **PASS**

No inference call was made. Immutable inputs were unchanged.

| Block | Episodes | Charged chars | Actual chars | Budget | Overrun | Replay |
|---|---:|---:|---:|---:|---:|---|
| study_010_q13 | 80 | 31991 | 53726 | 32000 | 21726 | PASS |
| study_010_q14 | 81 | 31847 | 53839 | 32000 | 21839 | PASS |
| bakeoff_tier6_q4 | 15 | 59708 | 59708 | 60595 | -887 | PASS |

Q13 and Q14 reproduce character-for-character and preserve the historical episode identity/order list. The previously published 31,991 and 31,847 values are charged content characters; the actual serialized blocks are 53,726 and 53,839 characters.

Per-episode rows and distribution summaries are in `expansion_rows.csv` and `summary.json`.
