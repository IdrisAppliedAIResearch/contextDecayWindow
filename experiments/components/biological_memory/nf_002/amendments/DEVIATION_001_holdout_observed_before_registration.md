# NF-002 Deviation 001 — the holdout was observed before the bars were locked

**Document type:** Deviation record
**Status:** `RECORDED — NOT REPAIRED, NOT REWRITTEN`
**Date:** August 12, 2026

## What happened

While computing development discordant counts to set the registration's bars, I
printed the holdout counts in the same command. The output was:

```
DEVELOPMENT: n=185     any-evidence  gains   8  losses   0  net +8
holdout:     n=285     any-evidence  gains  14  losses   6  net +8
```

The holdout line was labelled "NOT read for bars" in the code that produced it.
That label is worthless: it was printed, so it was read.

## Why it matters

`AGENTS.md` §7 forbids changing criteria after observing results, and §9.4 says
a reading applied to a number already on the table is rescue rather than
research. Any bar I set now is set with knowledge of the number it will be
applied to. I cannot un-know it, and a bar chosen under that knowledge cannot
support a confirmatory claim no matter how it is worded.

Part 1 had already computed pooled counts over all 470 items, so the holdout was
never fully sealed. This deviation makes it explicit rather than resting on that
weaker excuse: the split-level counts were seen directly.

## Consequence, applied

**NF-002 cannot produce a confirmatory result.** Its highest available
disposition is `CHARACTERIZED`. The registration states this in its decision
section rather than describing an outcome it is not entitled to reach.

The bars are still registered and still binding, because a bar that disciplines
the reading is worth more than no bar — but they discipline a development
characterization, not a confirmation.

## What was not done

Git history is not rewritten. The split is not redrawn to manufacture a fresh
holdout, which would be the same error with extra steps: I have seen the
mechanism's behaviour on every one of the 470 items, so no subset of them is
sealed against me now.

## What a confirmatory test would need

A corpus this program has not touched. Every LongMemEval item is now used. The
options are a different public benchmark, or a newly collected conversation set
with evidence annotation, and either is a separate authorized effort with its
own registration — not something this branch can produce.

## Precedent

`DMR_001B` recorded `DEVIATION_001` when implementation preceded registration,
did not rewrite history, and reported PF3 as FAILED rather than redefining it.
This follows that precedent.
