# DA-048 Report

**Disposition:** `SECOND_HOP_CAPACITY_SIGNAL`

Directional continuation adds one exact temporal hop beyond every frozen
one-hop edge while leaving DA-038 and the DA-046 retained register unchanged.
The blind stream contains 4,273 new episodes and 8,546 members. Of the first-32
member actions, 6,670 fit the 2,048-character frame and 1,860 overflow.

The evidence-aware one-frame oracle raises complete LongMem availability from
DA-046's 250 to 295: 45 gains, zero losses, two-sided exact p=5.68e-14. Temporal
reasoning contributes 27 gains; multi-session 9; preference 4; update 3; user 2;
assistant 0. Every type is nonnegative.

Useful frames occur early: ordinal p50 5 and p90 14.2. Frame size is p50 309
chars and cumulative traversal through the useful frame is p50 1,361, p90
5,801.2 chars. This adds capacity by graph traversal rather than simultaneous
token flooding or payload substitution.

The oracle knows which frame to retain. Reader recognition, stopping, fresh
transfer, runtime, and answer use remain untested. No model, embedding, or cache
call occurred.
