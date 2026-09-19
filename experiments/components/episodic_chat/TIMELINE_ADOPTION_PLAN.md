# Chronological relevance timeline: engineering adoption

Date: 2026-09-19. Status: authorized engineering implementation; no new inference.

The user paused the extra LLM step, requested arc closeout and a core product
update, and explicitly selected the chronological relevance timeline over the
later contextual/traversal fusion. This is a product decision based on existing
exploratory evidence, not a revision to a study disposition or success bar.
Historical registrations, answers and scores remain immutable.

## Contract

Release episodic-chat 0.3.0 with a `timeline` default read policy. Select every
eligible complete stored exchange with raw cosine >=0.48 and render original
text in ascending source-turn order. No automatic recency, item cap, character
packing, lexical fusion, traversal or generative call. Keep the existing XML
renderer, embedding identity/cache gates and durable append-only store.

Expose an optional caller-supplied inclusive `through_turn` boundary, with an
optional `anchor_turn` that explicitly protects that source exchange even below
threshold. Reject missing/invalid anchors and inconsistent boundaries. Never
infer an event boundary from natural language. A source turn is recording order,
not an inferred event date; later retrospective testimony requires no cutoff.
This general API replaces the synthetic quoted-name grammar; parity checks
receive the old explicitly recorded anchors/boundaries, not answer labels.

Retain CC-007 as explicit `read_policy="legacy_cc80"`, including its old settings,
budget override and ASPECT option. Reject a character budget or ASPECT on the
timeline path rather than silently changing policy. Preserve old serialized
configs as legacy when loaded explicitly; an implicit reopen under new defaults
must fail the config gate. Migration requires explicit `override_config=True`.
No re-embedding or schema rewrite is needed. New report fields expose policy,
selected identities, cutoff and anchor; an unbounded allowance is `None`.

## Part 1 and implementation order

Before package implementation, characterize committed timeline selections and
prefix transformations: counts, size distributions, empty/full cases and exact
source identities. Commit this record. Implement the selector behind an internal
entry point first. Do not switch the public default until the recorded parity
gate passes. Then test the public API, old-config migration, durable reopening,
vector purity, error paths and explicit legacy behavior. Update current product
documentation and add an arc closeout; mark LLM planning paused.

## Preflight and acceptance

All following evidence belongs in `timeline_artifacts/` and the adoption report.
No model calls or new answer scoring are part of this release.

| Gate | Required evidence |
|---|---|
| PF1 | Hash and count committed E source/score/selection/prefix artifacts and LoCoMo selections/adapters. |
| PF2 | Inclusive .48 filter, stable chronological order, exact original renderer, explicit anchor and cutoff fixtures; count/size distribution on real traces. |
| PF3 | Commit passing package-selector parity before public activation. Mutation fixtures must fail before a passing report is written. |
| PF4 | Below/equal/above threshold, empty/all-selected, oversized evidence and invalid boundary cases. No effectiveness bar is introduced. |
| PF5 | Replay keys use retained source IDs/content and context SHA-256; generated store UUIDs are not cross-rebuild keys. |
| PF6 | Reproduce 192 E anchored timelines, 128 E prefixes, and 1,986 LoCoMo selections by identity; reproduce E payloads and LoCoMo source-adapter blocks by SHA. |
| PF7 | Selector has no feedback; repeated selection exact and store context calls leave database state unchanged. |
| PF8 | Full committed replay plus boundary fixtures tests port correctness; it cannot establish new reader efficacy or endurance. |
| PF9 | Exact port can still retrieve insufficient evidence or lead to wrong answers. Public API tests supplement replay; no surrogate success claim. |
| PF10 | Existing live evidence is reported with its scope: 5/12→8/12 chronology probe, 106/128→126/128 two-batch synthetic prefix result; natural timeline30 and shared-chronology unified subset do not isolate chronology or certify this release. No new inference authorized. |

Package checks must pass before closeout. Update root/package README, deployed
settings, diagrams, migration/release notes, package metadata/lockfile, AGENTS,
active handoffs and relevant PRs. Preserve historical results and their scopes.
Do not publish to a package registry or merge a PR as part of this operation.
