The deployed library still used budgeted CC80 while the chronological relevance
work lived only in experiment code. This release makes the user-selected timeline
the default in episodic-chat 0.3.0 and closes the research arc at its existing
evidence. The proposed extra LLM step is paused.

The new default retrieves every exchange with raw cosine >=0.48, includes the
latest 32 complete exchanges for continuity, deduplicates, and presents the union
chronologically without a packing cap. `recency_window_n=0` disables continuity.
Optional source horizons also restrict continuity; anchors are supplied explicitly
by callers. There is no implicit anchor resolver, traversal fusion or generative
retrieval call. Existing stores require deliberate migration; `legacy_cc80`
retains prior budgeted behavior. Historical public-store consumers pin that policy.

Validation: 2,306 exact historical selection/payload checks with continuity off;
217 passing library/compatibility tests; offline wheel build and installation;
fresh-process output identity and continuity toggle checks; offline lockfile check.
The default continuity union has no new reader score. Prior synthetic diagnostic
results and 0.2 benchmark scores are not projected onto this product composition.

The root/package README, deployed settings and architecture diagram, migration
notes, reports, handoffs, version metadata and lockfile are updated. Historical
registrations and scores are unchanged; no numerical ERRATA is needed. Output
size is uncapped, so applications remain responsible for reader prompt capacity.

This PR is stacked on the completed experimental work in #98; it does not adopt
that PR's combined contextual/traversal configuration. Neither PR is merged by
this task, and no package-registry publication is performed.

- [x] Plan and continuity clarification committed before implementation
- [x] Characterization and exact parity sealed before activation
- [x] Public API, legacy compatibility and installed-wheel checks pass
- [x] Research closeout and current product documentation updated
- [x] Extra LLM step paused; no new inference or score changes

See `experiments/components/episodic_chat/TIMELINE_REPORT.md`,
`timeline_artifacts/activation.json`, and `episodic/CHANGELOG.md`.
