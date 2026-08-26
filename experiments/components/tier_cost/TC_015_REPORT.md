# TC-015 opportunity-filtered utility packing — report

**Status:** `STOPPED_AT_PART_1; INERT_SELECTION`  
**Part 1 commit:** `37011f5a`  
**Date:** 2026-08-26

## Finding

The proposed composition cannot change evidence availability. TC-014's
opportunity filter leaves a median 17 children at 16k and 36 at 32k, and every
retained child fits in the protected half on every one of the 1,742 planned
question-budget cells.

Sorting those retained children by frozen TC-013 edge utility changes payload
order on 868/871 rows at 16k and 871/871 at 32k. It changes selected identity
sets on **0/871 rows at either budget**. Complete-evidence outcomes would
therefore be exactly identical to TC-014 opportunity by construction.

## Interpretation

The two TC-014 signals do not compose in this order. Utility-first packing can
matter only while more proposed children compete than the spread half can hold.
Sequential opportunity admission removes that contest before utility sorting
runs. The mechanism is active as an ordering operation but inert for the
registered property.

This is not a negative outcome measured with labels. Part 1 established that a
positive or negative availability result is unreachable, so PF4 stopped the
study before pre-registration and label opening. No answer run, tuning,
deployment change or adoption follows.

## Integrity

All 1,742 frozen TC-014 opportunity allocations reproduced by selected
identity sequence and payload digest before the new order was applied. The
opportunity-retained set was preserved 1,742/1,742. Seven focused mechanism
tests pass. The exploration used zero cache, embedding, LLM or generative calls.

Detailed distributions and anchors are in `TC_015_PART1_EXPLORATION.md` and
`artifacts/tc015/part1_exploration.json` (SHA-256
`355bd73af9c145ace978285094ce8f20de9fa030e404c1f74d098c3a336ba524`).
