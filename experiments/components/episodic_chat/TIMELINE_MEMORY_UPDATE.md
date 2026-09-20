# Handoff: chronological timeline release

2026-09-19. User selected timeline adoption, then retained last-32 continuity
as default with an explicit off toggle. Implementation uses `recency_window_n=0`
to disable it. New policy `timeline`; old `legacy_cc80` remains available.
No packing cap. Whole union sorted by source turn; explicit inclusive horizon
limits all routes. No automatic natural-language anchor. Legacy configs load as
legacy; migrating a store requires an explicit override and matching encoder.

Plan1c024e70/clarificationfbd5cd42 precede implementation; Part1 5e1431ae;
2,306 exact parity checks sealed bc7ffb39 before activation. See TIMELINE_REPORT.md
and timeline_artifacts for final verification. Package version0.3.0. Historical
0.2 benchmark scores and no-recency research scores do not label the default.

Extra LLM step paused; unified traversal not adopted; full generation stopped.
No live or judge calls are authorized by this release. Do not resume from old
handoffs or launch large runs. User files .claude/settings.local.json and demo/
were present before this task and must not be included in the release commits.
