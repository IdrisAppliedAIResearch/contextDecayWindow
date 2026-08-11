# SUP-001 Memory Update

SUP-001 supports explicit P5/P9 supersession mechanically but stops at reader
integration. Offline, binary accessibility changes current-only retrieval from
0/64 to 64/64, preserves 32/32 unchanged targets, recovers 64/64 exact
three-version histories, and selects zero stale versions naturally. In the
35-turn Qwen ablation, C0 scores 7/9 and T1 8/9 with zero regressions; T1 fails
the all-unchanged bar because the reader formats delivered `$35` as `$35.00`.
Disposition: `ABLATION_INTEGRATION_STOP`. No 120-turn run or adoption. Explicit
metadata works; natural contradiction detection remains untested.

