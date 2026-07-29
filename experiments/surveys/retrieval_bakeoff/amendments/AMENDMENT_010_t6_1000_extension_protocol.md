# Amendment 010: Tier 6 1,000-Turn Extension Protocol

**Date:** 2026-07-29  
**Status:** Authorized before extension implementation, calibration, or inference  
**Applies to:** The conditional T6.1 extension in Amendment 004 only

## Trigger And Evidence

The registered 121-turn T6.1 arm scored **6.5/13.0**, below the committed
Study 009 Arm L score of 12.0. The blinded score was committed at `39423b02`
before the arm mapping was opened. Amendment 004 therefore requires the
1,000-turn Study 010 context-matched extension before either Tier 6 run's
mechanism logs are opened.

Amendment 004 does not define the extension's calibration window, payload
schedule, N/K grid, checkpoint-resume gate, or score denominator. Copying the
121-turn fixed-cap protocol would not match Study 010 Arm L. Its exact charged
payload on turns 967-986 is:

```text
65452, 88665, 106954, 63544, 72833, 62004, 92593, 100181, 66039,
89797, 107571, 64163, 74061, 63079, 94135, 101863, 66660, 90890,
108228, 64780
```

The median is 81,363 characters, but a constant 81,363-character delivery
would have 22.63% median absolute percentage error against that vector before
indivisible-episode effects. The 121-turn match gate is 5%. A single cap would
therefore certify "context matched" while the delivered resource differs by
tens of thousands of characters on individual turns.

Study 010's committed fact-order audit also found that interim probes I2, I5,
and I8 require facts planted after their probe turns. The standing pre-lock
rule prohibits inference against a rubric with unavailable required facts.
All fourteen terminal probes Q1-Q14 pass the same mechanical check, and their
committed comparison is Arm L 14.0/14.0 versus Arm S 12.0/14.0.

## Change

### Evidence Class And Comparison

The extension is a conditional, post-stop exploratory result. It does not
change the registered 121-turn interpretation or advance a candidate.

The extension runs the locked Study 010 script for all 1,000 turns and reports
the score on terminal probes Q1-Q14 only. Interim probe turns remain in the
conversation but are not scored. The extension is compared separately with
the committed Study 010 terminal scores, L 14.0 and S 12.0. There is no new
pass threshold and no degradation-curve claim.

Before artifact lock, a mechanical preflight must independently verify that
every Q1-Q14 required fact appears in a scripted user turn strictly before its
probe. Any failure blocks inference. The preflight records I2, I5, and I8 as
excluded construct-invalid interim items rather than treating them as valid
zeroes.

### Source Artifacts

The immutable sources are:

- Script: `experiments/study_010/script_1000.json`
- Arm L prompts:
  `experiments/study_010/runs/study_010_full_001/arm_l/constructed_prompts`
- Candidate raw store:
  `experiments/study_010/runs/study_010_full_001/arm_s/study.db`

Their pre-implementation identities are:

- script file SHA-256:
  `8edcfbf0085a8809d4bd069b885dccc53ab69e2d6a4d52a0c859458cd6289482`
- script post-decode LF digest:
  `2d186e1b7f4c89d7095d01d7ac267d981abb0996c60c922a35f78cf2c6d38521`
- Arm L prompt-set aggregate SHA-256, numeric turn order with
  length-prefixed relative paths and bytes:
  `31d18b3ce357afedf228798987313858e7effc2536cc3e8d0a2b2c1bb00039b3`
- Arm S database SHA-256:
  `022d196222a75bd868d9f4e5c848c1cde53d1d83bf7412e23f33d907ed5ebe15`

The settings artifact records and rechecks these values before and after the
run.

### Charged Payload And Turn Schedule

The charged payload definitions from Amendment 007 are unchanged:

```python
# Historical Arm L
"\n\n".join([recent_context, retrieved_stm, retrieved_ltm])

# Context-matched STM
"\n\n".join([recent_context, retrieved_stm])
```

For each turn `t`, the widened-STM character cap is the exact charged Arm L
payload length at the same historical turn. The 1,000 integers are extracted
and committed in the settings artifact before inference. Their canonical
compact-JSON vector SHA-256 is:

`a6c8623da47b17a14889797e929ebb6344c873ab8c650c45354f0ee2fe410f4c`

Runtime mechanism code may read only the committed integer schedule. It may
not read historical prompts, the rubric, a key, a score, or a live answer.
The schedule changes allocation volume only and conveys no retrieved text.

Packing remains whole-episode, N first and K-only second, with identity
deduplication and the production XML renderer. A candidate that would exceed
that turn's cap is skipped while later smaller candidates remain eligible.
No padding, truncation, synthetic content, or hidden uncharged block is
permitted. Per-turn accounting must prove delivered characters never exceed
the target.

### Calibration

Calibration uses only mature non-probe turns 967-986. At turn `t`, only raw
episodes with source turn `< t` are eligible. The target is the exact Arm L
character vector above. Terminal turns 987-1000, all answers, all keys, and all
rubric criteria are prohibited from selecting N or K.

The carried N/K policy is widened over this locked grid:

- N caps:
  `12, 16, 20, 24, 28, 32, 36, 40, 60, 80, 100, 120, 140, 160, 180, 200, 220`
- K cosine thresholds:
  `0.48, 0.45, 0.40, 0.35, 0.30, 0.25, 0.20`

All 119 cells are evaluated. The primary loss is mean absolute character
error over turns 967-986. Ties resolve by lower maximum absolute error, then
lower N cap, then higher K threshold. The selected cell must have median
absolute percentage error at most 5%. Failure blocks inference and requires a
new authorized amendment; the grid may not be widened after inspecting a live
answer.

The calibration replay must process turns 1-986 and verify temporal
eligibility, exact renderer accounting, the 80% context monitor, source hashes,
and the mechanism/key leakage boundary at the maximum pre-probe corpus scale.
The settings artifact, every candidate row, selected settings, implementation
tests, and calibration report are committed before generation.

### Runtime, Ablation, And Resume

The extension carries Study 010's script, seed 5005, model, server build,
one-slot execution, response budget, context capacity, cache types, sampling
settings, disabled speculative decoding, explicit UTF-8, and authorized
parse-but-do-not-persist rule handling. It adds only context-matched raw
retrieval. Topic assignment and episode storage remain carried infrastructure;
no LTM, dreaming, digest, promotion, or answer-key module may load.

Two independent 35-turn ablations must begin on different freshly launched
server processes and match byte-for-byte on all prompts, user turns, and
answers. The second ablation is interrupted at a committed checkpoint and
resumed on its same server process before turn 35. This simultaneously verifies
the seeded prefix and the changed runner's checkpoint boundary. The full run
uses a third fresh server PID and writes atomic checkpoints every 100 turns.

A launcher restart may continue on the same live server process. If that
server process is lost, a fresh server may continue only after replaying every
completed generation request in order and proving every replayed answer
byte-identical to the sealed prefix; otherwise continuation is blocked. Every
launch or resume segment records command, code SHA, server PID and build,
model hash, settings hash, script digest, checkpoint hash, and output-byte
ledger.

### Scoring And Commit Order

The scoring surface contains only turns 987-1000 and is sealed separately from
mechanism artifacts. Completeness and fact-presence checks are committed before
rating. Three clean-context blind passes use the locked Study 010 terminal
rubric and the standing scorer calibration, including a planted `NO_ANSWER`.

Amendment 009 governs the new arm: H3 is not evaluable, H1/H2 are unchanged,
H4 independently adjudicates Q11 and Q14, and H5 draws a deterministic 10%
sample from otherwise self-consistent eligible items. The extension-specific
H5 salt is:

`retrieval-bakeoff-t6-1000-h5-2026-07-29-v1`

The final terminal score and every rationale are committed before the private
arm mapping is opened and before any 121-turn or 1,000-turn mechanism log is
read. Only then may mechanism analysis compare delivery, displacement,
retrieval composition, and historical arms.

## Rationale

A per-turn cap measures the resource named by the registration and cannot pass
while missing the historical arm's large volume swings. It changes no ranking
signal and uses no answer content. Restricting the score to the valid terminal
instrument preserves the exact committed 14-versus-12 comparison that
motivated the extension while obeying the newer mandatory plant-order gate.

The interrupted second ablation tests the failure-prone resume path without
adding a separate long rehearsal. Processing the full pre-probe corpus during
calibration revalidates retrieval and accounting at the planned scale before
generation.

## Exclusions

This amendment does not edit the locked bakeoff registration, Study 010
script, historical prompts, stores, rubric, key, answers, or scores. It does
not repair the three invalid interim probes, rescore either historical arm,
weaken the 5% context-match gate, add a ranker, or authorize mechanism access
to measurement artifacts. It does not alter the committed 121-turn score or
permit either run's sealed logs to be opened early.

## Authorization

The repository owner authorized necessary amendments and directed the
121-turn run first, followed by the 1,000-turn version if the short arm did not
reach 12.0. The 6.5 result triggered that direction. This amendment resolves
only the genuine execution and measurement blockers in the conditional
extension.
