# DA-055 Scratchpad

## 2026-08-31 - Registration

- Build one out-of-band directory root over deterministic session chains.
- Store identities/coordinates/pointers only; payload stays immutable.
- Resolve 134 absent members only after blind sidecar seal.
- Zero rendered chars and zero model/embedder/cache calls.

## 2026-08-31 - Result

- Blind graph: 22,182 sessions, 106,412 episodes, 212,824 members; exact replay.
- Resolves 134/134 absent members, zero ambiguity and zero rendered chars.
- Session ordinal p50 27.5, while episode order p50 0/p90 2.
- Next materialize exact session-local members into the protected retained set;
  session-head choice remains oracle-only.
