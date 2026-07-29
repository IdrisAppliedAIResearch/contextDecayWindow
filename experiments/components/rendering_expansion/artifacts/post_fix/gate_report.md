# DR-001 Post-Fix Replay and Expansion Measurement

**Design commit:** `094cbea2`  
**Amendment commit:** `ad74b991`  
**Implementation commit:** `202b1883`  
**G-R2:** **PASS**

No inference call was made. Immutable inputs were unchanged. Every compact element parsed back to the original user and assistant text.

| Block | Episodes | Pre-fix chars | Post-fix chars | Reduction | Historical set fits budget | Identity/content |
|---|---:|---:|---:|---:|---|---|
| study_010_q13 | 80 | 53726 | 37619 | 16107 | NO | PASS |
| study_010_q14 | 81 | 53839 | 37545 | 16294 | NO | PASS |
| bakeoff_tier6_q4 | 15 | 59708 | 58808 | 900 | YES | PASS |

G-R2 is an identity-preserving serializer gate. Production re-selection under exact cost is a separate downstream re-derivation.
