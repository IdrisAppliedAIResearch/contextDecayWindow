# Amendment 003 - Study 003 Cross-Reference Resolution

**Date:** 2026-07-26  
**Disposition:** first Layer 2 sequence invalidated

Study 003's accepted rubric bundle stores Q9, Q10, and Q12 as textual
cross-references to the exact Q6, Q7, and Q3 responses. Q13 is an assessment over
the Q1-Q11 probe outputs. The first parser treated the cross-reference sentences
as though they were model answers, incorrectly removing credit.

The parser now resolves Q9 to Q6, Q10 to Q7, Q12 to Q3, and Q13 to the applicable
late-turn response set. This changes Layer 1 flags and the blind-corpus selection
from 81 to 79 items.

Accordingly, commits `44d9d74` through `3d925aa` preserve an invalid first Layer 2
attempt and do not contribute scores or adjudications to the audit result. No value
from that sequence may be reused. The replacement sequence begins from the
corrected corpus SHA-256
`13ffe3937aa879ab18302ab29d353192208c0bcf973d98ad1b6b91f899e8090c`.

