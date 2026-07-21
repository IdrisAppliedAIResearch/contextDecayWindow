# Study 004 — Script Payload Verification

**Date:** July 21, 2026  
**Status:** PASS

The Study 004 script was copied from the Study 003 script before Q14 was appended. The serialized turn-object payload for turns 1–120 was extracted from each file, line endings were normalized to LF for cross-platform reproducibility, and the payloads were compared byte-for-byte.

| Artifact | Turns | SHA-256 |
|---|---:|---|
| `experiments/study_003/script.json` | 1–120 | `d2260351c3de6ce88a9bfce16a92fbaaa4311aef7bfd50e589513c2f245de7f9` |
| `experiments/study_004/script.json` | 1–120 | `d2260351c3de6ce88a9bfce16a92fbaaa4311aef7bfd50e589513c2f245de7f9` |

**Payload result:** byte-identical after line-ending normalization.  
**Payload length:** 33,852 bytes.  
**Study 004 turn count:** 121.

Turn 121 exactly matches the blockquoted probe text in `q14_criteria.md`. It follows all Study-003-equivalent probes and remains outside the promotion-emission window, which ends at turn 111.
