# Arm L Protocol Notes

**Evidence status:** post-stop exploratory
**Governing amendments:** 004, 005, and 006
**Result:** 1,000 turns complete

The initial process ran through turn 596 after writing checkpoints through
turn 500. Its terminal wrapper reached a one-hour observation limit and the
detached Python child was subsequently reaped during turn 597. No turn-600
checkpoint existed.

The original launch manifest was preserved as
`study_010_full_001_l_initial_launch_manifest.json`. The arm resumed from the
registered atomic checkpoint at `checkpoints/turn_0500`. Restore verified the
checkpoint hashes, truncated uncheckpointed output after turn 500, restored
the database and runner state, and regenerated turns 501-1000.

The resumed process exited successfully. Final verification found:

- 1,000 response turns ending at turn 1000;
- checkpoints at every 100 turns through 1000;
- zero literal rule-detection tags and zero persisted rules;
- peak estimated context of 27,154 tokens, below the 40,000-token monitor; and
- terminal rubric responses present.
