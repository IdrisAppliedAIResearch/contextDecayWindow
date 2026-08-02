# DECISION 001 — DX-002 returns Branch B; CC-003 is blocked until the STM block is budgeted

**Component:** `deployment_closeout`
**Pre-registration:** `CC_003_004_005_deployment_closeout.md` at `43588944`
**Decision rule applied:** section 0.4
**Artifacts:** `artifacts/dx002/`
**Status:** COMMITTED — recorded before any Part 1 or Part 3 work begins

## Finding

**Branch B — terminal growth is positive and the cause is an unbudgeted
component.** The component is the `<retrieved_stm>` block, in both arms.

| Series | 501–600 | 601–700 | 701–800 | 801–900 | 901–1000 | Change | Verdict |
|---|---:|---:|---:|---:|---:|---:|---|
| `arm_l.retrieved_ltm` | 55,135 | 54,518 | 53,512 | 53,512 | 54,268 | −867 | saturated |
| `arm_l.retrieved_stm` | 25,253 | 33,312 | 41,556 | 35,110 | 48,491 | **+23,238** | still climbing |
| `arm_s.retrieved_stm` | 30,442 | 41,396 | 45,875 | 52,829 | 59,143 | **+28,701** | still climbing |
| `arm_l.recent_context` | 5,042 | 5,082 | 5,112 | 5,049 | 4,929 | −113 | saturated |

Bucketed 95th percentiles, 100 turns per bucket.

This is section 0.5's committed prediction — H-A for the LTM block, H-C
overall — confirmed on both counts. The greedy frame does fill its budget
and then flatten: the LTM block saturates at roughly 52–54k characters from
turn 500 and declines slightly thereafter. Alongside it, a second block
outside that budget keeps setting new highs through the final turn of the
run. What the prediction got wrong is the size: it expected "a small
positive residual slope", and the residual is the largest single mover in
the terminal window.

## What was ruled out

- **Rule pinning**, the named 118-false-rule candidate, contributes exactly
  zero: detection fired on 0 of 1,000 turns in both arms and
  `<pinned_rules/>` is a constant 15 characters. This does **not** clear the
  path — persistence was disabled before this run, so the behaviour is
  absent by configuration rather than shown harmless.
- **The recency window** is flat in both arms (−113 and +8 characters).
- **TopicManager** has no block of its own in the serialized prompt; the
  topic digest was dropped pre-run in Study 009.

## Consequences, as registered in section 0.4

1. **This blocks CC-003.** Section 0.4's Branch B is explicit: name the
   component and bring it inside the budget or remove it before anything
   ships. A hard ceiling applied to the LTM block alone would leave the
   growing block untouched while `ContextReport` says `truncated=False`.
2. **CC-005's design is decided, and not the way section 3.1 assumed.**
   Row 1 of that table anticipated "if H-A, bounded by budget". Context is
   not bounded by construction at the measured horizon, so eviction cannot
   be scoped as a disk-and-latency policy on the strength of a plateau that
   only one of the two retrieval blocks exhibits.
3. **The leak is a property of the Study 010 runner, not necessarily of
   `episodic`.** The extracted library already routes the recency window
   and the K-threshold hits through one `budget` in `pack_stm_payload`.
   CC-003 must verify that directly rather than assume it; that
   verification is the gate that unblocks Part 1.

## The methodological correction

This diagnostic first returned **Branch A**, on a decision rule that asked
only whether the terminal OLS slope's 95% interval contained zero. It does,
for every part in both arms — the sawtooth variance is large enough that
nothing clears the bar, and the smallest slope the data could have
distinguished from zero is about 17 characters per turn on `arm_l.total`,
or 17,000 characters per 1,000 turns.

Branch A is a conjunction: *terminal slope ≈ 0; LTM saturated; **no
unbudgeted component climbing***. Checking only the first clause let a part
whose 95th percentile rose from 25,253 to 48,491 characters be reported as
flat.

That is the failure class in `AGENTS.md` §3 reproduced exactly — a check
that passes while the property it certifies is false. The interval was
measuring statistical power and was read as evidence of boundedness. The
saturation and window-over-window readings were added in response, and both
are assumption-free: no noise model, no significance test, no fitted growth
law. A materiality floor of 320 characters — one percent of the 32,000
budget, stated in the system's own units rather than fitted to the observed
series — keeps a five-character drift in `<current_turn>` from being
reported as a leak beside a 23,000-character one.

## Boundary

Every claim here is at **the tested horizon only**: 1,000 turns, one
scripted conversation shape, one model, one quantization, one machine.
Section 0.6 names "a plateau at 1,000 turns says nothing about 10,000" as a
surrogate that can pass falsely, and it is not mitigated here. The LTM
saturation claim inherits that limit in full.

The climbing verdict says the block had not stopped growing by turn 1,000.
It does not fit a growth law and does not project one.
