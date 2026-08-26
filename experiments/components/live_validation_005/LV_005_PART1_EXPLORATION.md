# LV-005 — TC-014 context organization Part 1

**Status:** exploration only; no live probe is registered or runnable yet  
**Date:** 2026-08-26

## Behavioral identity

At 32k, every frozen TC-014 opportunity spread episode has exactly one selected
semantic parent. Parent–child adjacency can therefore reorganize every frozen
payload without adding, removing or duplicating an episode.

Across all 871 questions, opportunity selects 87,732 episodes: 56,563 semantic
episodes and 31,169 spread episodes. All 31,169 selected spread episodes map to
a selected parent. The live discordant population contains 1,686 selected
episodes, including 617 spread episodes, and all 617 map cleanly.

Grouping materially changes order. It changes 871/871 full-population payload
orders and 17/17 live-population orders. Chronology is not already implied by
the edge direction: 16,030/31,169 children occur earlier in the conversation
than their parent, while 15,139 occur later.

## Name audit and design consequence

- A **group** is one selected TC-014 query-ranked parent plus its one selected
  spread child, if present. It is related evidence, not a certified entity.
- **Chronology** is the adjacent-pair position in the LoCoMo conversation. It is
  not a wall-clock timestamp.
- **Latest** means the greater conversation position inside that related pair.
  It is not automatically the true or current fact.
- **Supersession** is not identifiable here. Unlike SUP-001, LoCoMo has no
  explicit memory key or `supersedes` edge. Inventing those labels would make
  the intervention capable of certifying false updates.

The probe may therefore test: parent–child grouping; chronology within each
group; and explicit `earlier`/`later` rendering. It must not call natural
statements `current` or `superseded`.

## Degenerate states

There are zero unmapped selected spread episodes and no feedback state. Groups
without children occur naturally. Earlier-child and later-child cases both
occur in volume, so chronological sorting is not inert or one-directional.

The complete distributions and all 871 per-question values are recorded in
`artifacts/part1_exploration.json`. Exploration used zero embedding and zero
generative calls.
