# DX-002 - The Context Growth Question

**Status:** PASS
**Branch:** B - An unbudgeted component is climbing
**Scope:** committed Study 010 serialized prompts. Offline. No run.

## The question

The record holds a peak - 27,154 estimated tokens for arm L - and a
peak cannot say whether the curve was still climbing. This reads the
same 2,000 prompts and fits the terminal
300 turns of every part.

## Gates

| Gate | Certifies | Result |
|---|---|---|
| G1 | every prompt reconstructs byte-exactly from its parts | **PASS** |
| G2 | recomputed `chars // 4` matches committed telemetry | **PASS** |
| G3 | compact re-render reproduces DR-001's 37,619 / 37,545 | **PASS** |
| G4 | input tree unchanged across the read | **PASS** |

G3 is what licenses the post-DR-001 column below. The re-render is
certified against a committed result before it is applied to the
other 998 turns.

## Terminal slopes

Ordinary least squares over the last 300 turns, with a two-sided 95%
interval on t(n-2). A slope whose interval contains zero is not
distinguishable from flat. Theil-Sen is the median-of-pairs
robustness check: these series are heteroscedastic, and agreement
between the two estimators is what rules out a handful of extreme
turns driving the fit.

### arm_l

| Part | Terminal mean chars | Slope chars/turn | 95% CI | Theil-Sen | Flat? |
|---|---:|---:|---|---:|---|
| `preamble` | 149 | 0 | constant | 0 | yes (constant) |
| `pinned_rules` | 15 | 0 | constant | 0 | yes (constant) |
| `recent_context` | 4,841 | -0.045 | [-0.182, +0.092] | +0.000 | yes |
| `retrieved_stm` | 16,254 | +4.273 | [-12.869, +21.415] | +0.930 | yes |
| `retrieved_ltm` | 52,607 | -1.796 | [-2.671, -0.922] | -2.141 | **NO** |
| `current_turn` | 209 | -0.012 | [-0.029, +0.005] | +0.000 | yes |
| `separators` | 8 | 0 | constant | 0 | yes (constant) |
| `assistant_cue` | 12 | 0 | constant | 0 | yes (constant) |
| `total` | 74,095 | +2.419 | [-14.784, +19.622] | -0.696 | yes |

### arm_s

| Part | Terminal mean chars | Slope chars/turn | 95% CI | Theil-Sen | Flat? |
|---|---:|---:|---|---:|---|
| `preamble` | 149 | 0 | constant | 0 | yes (constant) |
| `pinned_rules` | 15 | 0 | constant | 0 | yes (constant) |
| `recent_context` | 5,511 | -0.174 | [-0.302, -0.047] | -0.123 | **NO** |
| `retrieved_stm` | 21,530 | +16.694 | [-5.487, +38.875] | +8.232 | yes |
| `retrieved_ltm` | 0 | 0 | constant | 0 | yes (constant) |
| `current_turn` | 209 | -0.012 | [-0.029, +0.005] | +0.000 | yes |
| `separators` | 6 | 0 | constant | 0 | yes (constant) |
| `assistant_cue` | 12 | 0 | constant | 0 | yes (constant) |
| `total` | 27,432 | +16.508 | [-5.672, +38.688] | +8.062 | yes |

## What this fit can and cannot rule out

A flat verdict is a statement about detectable growth, not about
growth. The half-width of each interval is the smallest slope
this data could have distinguished from zero, so any growth
below it is compatible with the measurement.

| Arm | Series | Terminal mean | Smallest detectable slope | Undetectable drift over 1,000 turns |
|---|---|---:|---:|---:|
| arm_l | `total` | 74,095 | 17.20 chars/turn | 17,203 chars |
| arm_l | `retrieved_stm` | 16,254 | 17.14 chars/turn | 17,142 chars |
| arm_l | `retrieved_ltm` | 52,607 | 0.87 chars/turn | 875 chars |
| arm_s | `total` | 27,432 | 22.18 chars/turn | 22,180 chars |
| arm_s | `retrieved_stm` | 21,530 | 22.18 chars/turn | 22,181 chars |

Read the `arm_l.total` row before treating Branch A as settled:
growth of up to 17 characters per turn is inside the noise here, which over 1,000
further turns is 17,203
characters of drift the fit would not have caught. Branch A means
*no growth was detected at this power*, on this conversation
shape, at this horizon.

### Why the interval is not the whole answer

These series are sawtooths - retrieval ramps up over a topic run
and resets - so the residuals are strongly autocorrelated and an
OLS interval built on independence assumptions cannot be taken at
face value. Durbin-Watson on the terminal residuals (2.0 would
mean no serial correlation):

| Arm | Series | Durbin-Watson |
|---|---|---:|
| arm_l | `total` | 1.84 |
| arm_l | `retrieved_stm` | 1.83 |
| arm_l | `retrieved_ltm` | 2.33 |
| arm_s | `total` | 1.94 |
| arm_s | `retrieved_stm` | 1.94 |

So the verdict does not rest on the fit. The blunt check below
assumes nothing about residual structure: it compares the fitted
window against the 300 turns immediately before it. A series that
is still climbing has to show up here.

| Arm | Series | Turns 401-700 mean | Turns 701-1000 mean | Change |
|---|---|---:|---:|---:|
| arm_l | `total` | 69,019 | 74,095 | +7.4% |
| arm_l | `retrieved_stm` | 12,221 | 16,254 | +33.0% |
| arm_l | `retrieved_ltm` | 51,560 | 52,607 | +2.0% |
| arm_l | `recent_context` | 4,843 | 4,841 | -0.0% |
| arm_s | `total` | 20,566 | 27,432 | +33.4% |
| arm_s | `retrieved_stm` | 14,666 | 21,530 | +46.8% |
| arm_s | `recent_context` | 5,507 | 5,511 | +0.1% |

### Saturation: is the part still setting records?

The decisive reading. A part that has stopped growing stops
reaching further; a part that is still climbing keeps setting
new highs. Below is the 95th percentile of each part within each
of the last five 100-turn buckets. If the final bucket holds the
maximum, the part had not saturated when the run ended.

A part is only called a growth concern if it also moved by at
least 320 characters - one percent of
the LTM budget - across these five buckets. That floor is in the
system's own budget units, not fitted to the data.

| Arm | Series | 501-600 | 601-700 | 701-800 | 801-900 | 901-1000 | Change | Verdict |
|---|---|---:|---:|---:|---:|---:|---:|---|
| arm_l | `recent_context` | 5,042 | 5,082 | 5,112 | 5,049 | 4,929 | -113 | saturated |
| arm_l | `retrieved_stm` | 25,253 | 33,312 | 41,556 | 35,110 | 48,491 | +23,238 | **STILL CLIMBING** |
| arm_l | `retrieved_ltm` | 55,135 | 54,518 | 53,512 | 53,512 | 54,268 | -867 | saturated |
| arm_l | `current_turn` | 226 | 228 | 228 | 228 | 231 | +5 | record set, below floor |
| arm_s | `recent_context` | 5,663 | 5,746 | 5,724 | 5,721 | 5,671 | +8 | saturated |
| arm_s | `retrieved_stm` | 30,442 | 41,396 | 45,875 | 52,829 | 59,143 | +28,701 | **STILL CLIMBING** |
| arm_s | `current_turn` | 226 | 228 | 228 | 228 | 231 | +5 | record set, below floor |

## Rule pinning

**arm_l.** Rule detection fired on 0 of 1,000 turns and the <pinned_rules/> block is a constant 15 characters on every turn, so rule pinning contributes exactly zero growth in these artifacts.

*Limitation.* This does not clear the rule-pinning growth path. Persistence was disabled before this run, so the 118-false-rule behaviour is absent by configuration rather than shown harmless. The candidate is untested at this horizon, not refuted.

**arm_s.** Rule detection fired on 0 of 1,000 turns and the <pinned_rules/> block is a constant 15 characters on every turn, so rule pinning contributes exactly zero growth in these artifacts.

*Limitation.* This does not clear the rule-pinning growth path. Persistence was disabled before this run, so the 118-false-rule behaviour is absent by configuration rather than shown harmless. The candidate is untested at this horizon, not refuted.

## LTM against its 32,000-character budget

- **arm_l**, 1,000 of 1,000 turns carry an LTM block.
  - Historical renderer: max 55,184 chars; 668 turns over the 32,000 budget.
  - Post-DR-001 compact renderer: max 37,934 chars, mean 26,070; 561 turns over budget.
- **arm_s** carries no `<retrieved_ltm>` block; it is the STM-only arm.

**The compact renderer alone does not bring the block under
budget.** Re-serializing the historically selected episode sets
at exact cost still exceeds 32,000 characters on the majority of
turns. This is not a contradiction of DR-001: those sets were
*chosen* under the undercharged accounting, so they contain more
episodes than the budget can hold, and cheaper tags cannot undo
an over-large selection. It is the measured case for CC-003 -
the ceiling has to bind during selection, not after it.

## Decision

**Branch B - An unbudgeted component is climbing.**

the budgeted LTM block saturates, but `arm_l.retrieved_stm`, `arm_s.retrieved_stm` has not: it is still setting new highs in its final 100-turn bucket. Name it and bring it inside the budget before anything ships.

Against section 0.5's committed prediction - H-A for the LTM
block, H-C overall, at about 60% - this is the predicted
outcome. The greedy frame does fill its budget and then flatten,
and there is a second component outside that budget which does
not. The prediction understated the size of the residual: it
expected "a small positive residual slope", and the measured
leak is the largest single mover in the terminal window.

### The near miss

This diagnostic first returned **Branch A**, on a decision rule
that asked only whether the terminal OLS slope's interval
contained zero. It does, in every part, in both arms - the
sawtooth variance is large enough that nothing clears the bar.
But Branch A is a conjunction, and its third clause is *no
unbudgeted component climbing*. Checking only the slope let a
part whose 95th percentile rose from 25,253 to 48,491 characters
over the final five buckets be reported as flat.

That is the failure class in AGENTS.md section 3, reproduced
exactly: a check that passes while the property it certifies is
false. The confidence interval was measuring statistical power,
and it was read as evidence of boundedness. The saturation and
window-over-window readings were added because of it, and both
are assumption-free.

## Consequences

- **This blocks CC-003** (section 0.4, Branch B). The STM block
  has to come inside a budget or be removed before enforcement
  can claim a bounded context. Enforcing a ceiling on the LTM
  block alone would leave the growing component untouched while
  the report says `truncated=False`.
- **CC-005's design is decided** (section 3.1, row 1). Context is
  not bounded by construction, so eviction cannot be scoped as a
  pure disk-and-latency policy on the strength of a plateau that
  only one of the two retrieval blocks exhibits.
- The extracted library already routes both the recency window
  and the K-threshold hits through a single `budget` in
  `pack_stm_payload`, so the leak measured here is a property of
  the Study 010 runner, not necessarily of `episodic`. CC-003
  should verify that directly rather than assume it.

## Boundary

This is a statement about **the tested horizon only**. A plateau
at 1,000 turns says nothing about 10,000; section 0.6 names that
surrogate explicitly and it is not mitigated here, only stated.
The LTM saturation claim inherits that limit in full.

The decomposition is over one conversation shape - a scripted
1,000-turn run on one model, one quantization, one machine.

The climbing verdict rests on bucketed percentiles and a
window-over-window mean, not on a significance test. It says the
part had not stopped growing by turn 1,000; it does not fit a
growth law and does not project one.

## Integrity

- Input files: 2,002
- Input tree SHA-256 before: `b169659853eda44d84a7072395bd8405c5fb6841b0def8f36d471ee51f6a1b99`
- Input tree SHA-256 after: `b169659853eda44d84a7072395bd8405c5fb6841b0def8f36d471ee51f6a1b99`
