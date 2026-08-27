# LV-003 — bounded-output live validation of TC-014 opportunity admission

**Type:** registered frozen-context live reader comparison  
**Status:** pre-registered; not yet runnable  
**Date:** 2026-08-26  
**Authorization:** successor required to complete the program owner's requested live test

## 1. Question and predecessor

Does TC-014 opportunity admission's 32k evidence-delivery change convert into
more correct reader answers than full-budget CC80 on the questions where their
offline complete-evidence outcomes differ?

LV-002 registered the same comparison and passed Preflight, but stopped before
scoring because at least one of 170 answers reached its 192-token allowance and
the runner discarded the invalid batch before serialization. No answer or arm
outcome was preserved. LV-003 changes only response allowance and persistence.

This is selected LoCoMo development characterization, not an overall benchmark
score, fresh-corpus confirmation, production-adoption gate or tuning study.

## 2. Frozen inputs and population

- LV-003 Part 1 SHA-256:
  `3cf4fc6750a44a7c0d0f704d6e0a6bb20b74c28b8d3b1dff9ee9158501a52829`;
  commit `154df94b`.
- Frozen prompt artifact SHA-256:
  `c01cf11a5e2750c2ed8c03e90c813af7263de8a7fd2c4b78bacb72aa1207d5d8`.
- LoCoMo, TC-014 selection and TC-014 outcome anchors remain respectively
  `79fa87e9…`, `32b1db4d…`, and `ce73bfcb…` as fully recorded in LV-002.
- The exact closed-think prompt bytes from LV-002 Amendment 001 are reused.
- Population is unchanged: all 17 32k availability-discordant questions. The
  primary is 16 answerable items—11 opportunity gains, 5 losses; 9 targeted,
  5 breadth, 2 other. One category-5 item is refusal-only secondary.

Stable comparison keys are canonical question content hashes. No item, arm,
budget, prompt, replicate or stratum may be added after registration.

## 3. Arms and runtime

- **C0 `FULL_CC80`:** frozen TC-014 full-budget CC80 payload.
- **T1 `OPPORTUNITY`:** frozen TC-014 50/50 CC80-parent fan-out after exact
  opportunity admission and CC80 slack return.
- **F0 `NO_MEMORY`:** identical reader prompt with the explicit no-record block,
  used only for the Preflight contamination floor.

Only the memory block differs between C0 and T1. Gold answers and evidence
labels are forbidden from prompt construction.

Runtime remains Ollama 0.33.0, `qwen-custom:latest` manifest `3516cd593f43`,
Qwen 3.5 27.3B Q6_K, blob `sha256-773f…`, on one RTX 5090 at 100% GPU.
Raw mode, `think:false`, sealed closed-think suffix, `num_ctx=65536`,
temperature `.6`, top-p `.95`, top-k `20`, min-p `0`, repeat penalty `1.0`,
and seeds `5005+r` remain unchanged.

**The sole runtime change is `num_predict=512`, carried from HH-001 before any
LV-002 answer was preserved or scored.** Judges retain `num_predict=128`,
temperature `.2`, top-p `.9`, top-k `20`, seeds 9005–9007.

## 4. Schedule and persistence

Five reader replicates per item and arm. Within each item-replicate, arm order
is fixed by the parity of SHA-256(`comparison_key || replicate`), exactly as in
LV-002. Requests are serial, `keep_alive=30m`, with no best-of-five selection.

Every reader response is appended to a JSONL artifact, flushed and fsynced
before the next request. The completed file is then validated for exact keys,
schedule, duplicates, truncation and count. A failure preserves the file and
stops judging. The final expected count is 170: 160 primary and 10 adversarial.

Failed individual calls are not retried except a mechanically absent response
or server error; the original error is recorded and the whole run is qualified.
A response reaching 512 tokens is preserved and stops the study without score.

## 5. Blinding and endpoints

All answers are committed before scoring. A seeded SHA shuffle hides arm,
replicate, context, offline direction and delivery state. Each of 160 primary
answers receives three blind semantic-correctness judge passes using the frozen
HH-001 binary rubric. Majority of three is the answer verdict; majority of five
answer verdicts is the item-arm verdict. Unparseable or truncated judging stops
before unblinding.

Normalized gold-string containment is a cross-check only. The category-5 item
is scored only for exact `I don't know` refusal. Report reader unanimity, judge
disagreement, unsupported correct majorities and all complete artifacts.

For 16 primary items report paired semantic-correctness gains, losses, ties,
net and descriptive exact McNemar p for combined, targeted, breadth, other,
offline-gain and offline-loss strata.

## 6. Locked disposition

- **`CONVERTS`:** overall net at least `+3`; targeted and breadth nets
  nonnegative; no endpoint-sign reversal; all validity gates pass.
- **`WEAK_CONVERSION`:** overall net `+1` or `+2`; targeted and breadth nets
  nonnegative; no sign reversal; all validity gates pass.
- **`NO_CONVERSION`:** overall net zero with no validity failure.
- **`REGRESSES`:** overall net negative, or targeted or breadth net negative,
  with no validity failure.
- **`NOT_INTERPRETABLE`:** contamination, truncation, prompt/runtime drift,
  incomplete schedule/judging, mapping-order failure or opposite nonzero signs
  between semantic correctness and containment.

The `+3` bar remains half the answerable offline complete-evidence net of `+6`.
No result authorizes deployment or a new parameter sweep.

## 7. Preflight — binding before replacement generation

- **PF1:** hash/count this registration, Part 1, frozen prompts, corpus, TC-014
  inputs, Ollama model/runtime and GPU.
- **PF2:** reproduce the 17-row population, all 34 payload/prompt digests,
  Part 1 distributions and mechanism identity; only output cap/persistence may
  differ from LV-002.
- **PF3:** prove prompt seal precedes generation, append+flush+fsync precedes
  the next request, answers precede blind scoring, and judgments precede mapping
  opening. Planted early gold and mapping access must fail.
- **PF4:** synthetic rows reach all five dispositions, floor pass/fail,
  truncation stop and sign reversal. Both real offline directions are nonempty.
- **PF5:** content-hash keys only; reject duplicates and incomplete joins.
- **PF6:** reproduce all 34 TC-014 payload identity sequences, costs and digests,
  and all sealed prompts twice.
- **PF7:** one full C0 prompt at `num_predict=512` rerun with seed 5005 is
  byte-identical, nonempty and untruncated; Ollama reports the registered model
  fully on GPU. No feedback state exists between prompts.
- **PF8:** five replicates support item majority and instability reporting;
  16 enriched items cannot resolve overall accuracy, small effects or transfer.
  No stateful/120-turn run makes a 35-turn ablation applicable.
- **PF9:** guessed correctness, containment blindness to composition, same-model
  judge bias and availability enrichment remain residuals. Floor, support audit,
  three blind passes and claim limits mitigate but do not erase them.
- **PF10:** this is the required live reader test; availability is an input.

Binding gates: F0 semantic correctness must be at most 3/16; no reader or judge
response may truncate; exactly 5 C0 and 5 T1 answers per item and 3 judgments
per primary answer must exist. Any failure stops without a directional verdict.
