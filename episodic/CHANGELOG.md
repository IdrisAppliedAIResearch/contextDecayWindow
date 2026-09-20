# Release notes

## 0.3.0 — 2026-09-19

New stores default to a chronological relevance timeline. Raw cosine >=0.48
selects complete exchanges without a character or item packing cap. The latest
32 complete exchanges are included for continuity by default. Set
`EpisodicConfig(recency_window_n=0)` to disable continuity. Evidence is deduplicated
and the whole union is presented in source-turn order.

`context(query, through_turn=..., anchor_turn=...)` accepts explicit source-turn
boundaries and protected anchors. Neither is inferred from the question.
`through_turn` is inclusive and also limits the continuity pool. It concerns
when evidence was recorded, not when the described event occurred.

### Migration from 0.2

- `EpisodicConfig(read_policy="legacy_cc80")` retains last-32 + budgeted CC80.
  Add `aspect_enabled=True` to retain the old optional ASPECT route.
- `EpisodicConfig.from_json(old_config_json)` interprets a config without a
  policy field as legacy. Retain any customized old settings when reopening.
- To migrate an existing store, supply the desired new config and
  `override_config=True` once. Source rows and embeddings are preserved; model
  and vector-identity checks still apply. Reopen subsequently with that config.
- Timeline calls reject the positional character budget. Remove that argument
  when migrating, or choose the legacy policy. The `retrieval_budget_chars`,
  BM25 and ASPECT config fields belong to the legacy path. The old `k_threshold`
  remains private historical compatibility; `timeline_threshold` controls the
  current raw-cosine threshold.
- Timeline report allowances and `chars_available` are `None`. Callers must
  handle this explicitly. `truncated=False` means no capacity packing occurred;
  it does not certify evidence completeness or reader context-window fit.

No store schema migration, generative retrieval call, implicit anchor resolver,
contextual traversal, or automatic summarization is added. The caller owns the
final model prompt and its capacity. An uncapped timeline can approach the full
history. The optional embedding backend still performs encoder inference.

This is a user-authorized product composition. Historical no-recency timeline
scores and 0.2 benchmark scores are not measurements of the new default.
See the repository's `experiments/components/episodic_chat/TIMELINE_REPORT.md`.

## 0.2.0

CC-007 introduced additive last-32 continuity, a 32,000-character CC80 retrieval
allowance, and optional static ASPECT. The distribution became `episodic-chat`;
the Python import namespace remained `episodic`.
