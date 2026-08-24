# Memory update — CC-007 episodic-chat adoption

- Branch: `codex/episodic-chat-cc80-aspect`.
- Registration: `293df2d0649907451099d3da41d0c2f0ee576ead`.
- Distribution is `episodic-chat` 0.2.0; import remains `episodic`.
- Public context is additive latest 32 plus independently budgeted CC80,
  default 32,000 characters. Recent identities cannot appear in long-term.
- ASPECT is exact TC-011 static ASPECT, optional and off by default. Enabled
  allocation is protected 50/50 with wrapper/slack return to CC80.
- Pre-activation parity: 4,355/4,355 exact, zero mismatches after repairing two
  gate-found byte drifts (per-vector float normalization and exact source text).
- Post-activation composition: 871/871 exact final payloads, 0 duplicates, 0
  retrieval breaches; all 871 exceed 32k in total because recency is additive.
- Clean install passed; full suite 2,267 passed. Zero new embedding or LLM calls.
- No reader, transfer, concurrency or latency claim. Next work is external
  validation/benchmarking, not another LoCoMo tuning pass.
