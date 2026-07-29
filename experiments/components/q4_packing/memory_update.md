# AS-001 Research Memory Update

- Status: DIAGNOSTIC; Branch D interpretation invalidated post-result.
- Design locked at `7c90235a`; evidence committed at `f6d5d79c`.
- Historical Q4 packing reproduced exactly at 15 episodes and 59,708
  characters with matching identity order and payload SHA-256.
- The turn-55 Q4 episode is N rank 27 of cap 32.
- Compact N-first packing fits 9 episodes at 32k and 16 at 64k. Turn 55 never
  enters anywhere in the locked 16k-64k sweep.
- The locked rule was unsound: exact charging reduced the historical 15 fitted
  episodes to 9, but no branch interpreted `S' < 15`; Branch A could not fire
  meaningfully and Branch D was nearly foreordained.
- Decision 001 was raised after output, so this is an invalidation, not a
  pre-result amendment. Generated artifacts remain unchanged as diagnostics.
- Post-result reachability finds turn 55 first enters at 108,432 characters.
  This indicts N-first ranking/packing and budget jointly; it does not identify
  primacy as a separate mechanism.
- No pinned-tier or CC-001 study is authorized by AS-001.
- The turn-55 cosine is corrected from 0.16612689197063446 to
  0.12042197585105896. Both are below K=0.48.
- The corrected Tier 6 seal lists an ignored database that was never committed.
  AS-001 reconstructs from committed logs; all 264 tracked seal entries match
  canonical LF or deterministic CRLF representation.
- No inference call, conversation run, architecture change, or rescore occurred.
