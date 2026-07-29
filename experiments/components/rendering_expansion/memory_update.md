# DR-001 Research Memory Update

- Component status: PASS; no inference study or score.
- Design locked at `094cbea2`; implementation followed at `202b1883`.
- G-R1 reproduced Study 010 Q13/Q14 LTM blocks character-for-character.
- The historical 31,991/31,847 values were charged source-content totals, not
  serialized blocks. Actual lengths were 53,726/53,839; `ERRATA.md` records the
  correction.
- Compact episode tags preserve turn, speaker, identity/order, and all source
  text while removing model-irrelevant retrieval metadata.
- G-R2 reduced the same historical blocks to 37,619/37,545 and the bakeoff Q4
  historical payload from 59,708 to 58,808.
- Production LTM budgeting now charges the exact complete serialized block.
- Re-derivation retains `B_ltm=32,000`, N cap 32, `k_min=1`, and containment
  dedup. N-first packing remains an open question owned by AS-001.
- At exact 32k, Study 010 Q13/Q14 select 69/71 episodes; Study 007 probes select
  8/9.
- The Q4 turn-55 episode remains rank 27 within N=32. Its post-fix fitted-slot
  result was not opened before AS-001's decision rule.

