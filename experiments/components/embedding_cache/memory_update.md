# Memory update — CC-006

- CC-006 PASS on registration
  `d2ddc1ca0a2c12cf7cdae2ae6f6a10d567c3a0fc`.
- `episodic.EmbeddingCache` persists exact solo-call float32 vectors and binds
  both the SQLite file and canonical text-to-vector contents by SHA-256.
- Read-only reuse requires both hashes, refuses every miss, and makes no model
  call.
- C1-C9 pass; full suite 1,028.
- EC-002 legacy cache adoption PASS: 96,585 entries, 1,050,013,696 bytes,
  file `e8a315…a7ad`, content `d60d72…6a180`, zero misses/model calls.
- The guarantee applies only where exact vectors were retained. EC-001's
  missing cache is unrecoverable, so its historical run remains permanently
  non-bit-replayable.

