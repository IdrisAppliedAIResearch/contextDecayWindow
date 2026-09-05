# DA-065 Scratchpad

## 2026-08-31 - Registration

- Immutable represented-episode prefix remains first.
- Each exact bigram occurrence expands within-session at alternating radius 1-5.
- Radius inherited from DA-048/050; no fitting on DA-064 residuals.
- One replaceable episode/frame; zero displacement.
- Seal before episode answer-marker join.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Complete reachability 416/465 (.8946), below the fixed .90 bar; any 449.
- DA-064 complete was 382; local expansion adds 34 complete questions.
- Last required position p50 24.5/p90 129; zero displacement.
- Residual 72 episodes: 35 session-unreachable, 37 no anchor in reached session.
- Zero residuals have a same-session anchor beyond radius five.
- Close larger radii; next expand from immutable represented episodes.
