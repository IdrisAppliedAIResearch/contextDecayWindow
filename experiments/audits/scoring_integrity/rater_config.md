# Rater Configuration

## AI Passes

- Rater class: independent clean-context Codex subagent.
- Model: inherited session default, recorded from each agent result when exposed.
- Passes: three.
- Context: no parent-thread history.
- Order: independently shuffled from stable item IDs using pass-specific suffixes
  `:pass-1`, `:pass-2`, and `:pass-3`.
- Input: anonymized ID, scoreable answer, question, locked criteria, and committed
  guidance only.
- Output: primary score, strict score where applicable, and answer-grounded
  rationale.

The model identifier is recorded as observed rather than guessed when the
subagent service does not expose it.

## Independent Adjudicator

The author amended the draft to use a fourth clean-context subagent as independent
adjudicator. It receives no parent history.

- H4/H5 packet: answer, question, criteria, guidance only. AI scores, original
  scores, arm identity, and Layer 1 are withheld until its decision is committed.
- H1-H3 packet: the surfaced conflict and evidence may be included.
- The adjudicator is an AI, not a human. Reports must state this limitation.
- Adjudicator values take precedence under this audit's authorized amendment.

## Calibration Gate

Before real answers are supplied, every AI rater must reproduce every expected
score in `calibration_set.json`, including `NO_ANSWER = 0`. Failure revises the
instructions and restarts calibration; it is never waived.

