# Arm S Protocol Notes

**Evidence status:** post-stop exploratory
**Governing amendments:** 004, 005, and 006
**Result:** 1,000 turns complete

Arm S ran from fresh state in one process and exited successfully without a
resume. Final verification found:

- 1,000 unique response turns ending at turn 1000;
- 1,000 constructed prompts, snapshots, and context-size rows;
- checkpoints at every 100 turns through 1000;
- all 23 registered interim and terminal rubric responses present;
- zero literal rule-detection tags and zero positive rule-detection rows; and
- peak estimated context of 17,541 tokens, below the 40,000-token monitor.
