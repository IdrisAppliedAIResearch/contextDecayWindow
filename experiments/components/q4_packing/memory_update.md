# AS-001 Research Memory Update

- Status: PASS; Branch D, `PRIMACY MECHANISM LIVE`.
- Design locked at `7c90235a`; evidence committed at `f6d5d79c`.
- Historical Q4 packing reproduced exactly at 15 episodes and 59,708
  characters with matching identity order and payload SHA-256.
- The turn-55 Q4 episode is N rank 27 of cap 32.
- Compact N-first packing fits 9 episodes at 32k and 16 at 64k. Turn 55 never
  enters anywhere in the locked 16k-64k sweep.
- The Q4 gap is late-rank character packing, not verbose episode tags. LTM's
  observed advantage remains primacy under the current packer.
- A pinned durable-fact tier is a live proposal, not a result; test it only in a
  separately pre-registered CC-001 study.
- The turn-55 cosine is corrected from 0.16612689197063446 to
  0.12042197585105896. Both are below K=0.48.
- The corrected Tier 6 seal lists an ignored database that was never committed.
  AS-001 reconstructs from committed logs; all 264 tracked seal entries match
  canonical LF or deterministic CRLF representation.
- No inference call, conversation run, architecture change, or rescore occurred.
