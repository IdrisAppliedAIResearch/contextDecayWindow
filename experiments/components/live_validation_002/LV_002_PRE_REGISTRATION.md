# LV-002 — live reader validation of TC-014 opportunity admission

**Type:** registered frozen-context live reader comparison  
**Status:** pre-registered; not yet runnable  
**Date:** 2026-08-26  
**Authorization:** program owner requested live testing after TC-014's offline result

## 1. Question and claim boundary

When TC-014 opportunity admission changes which evidence reaches a
32,000-character context, does that change what a fixed reader answers correctly
relative to full-budget CC80?

This is a conversion study over deliberately availability-discordant LoCoMo
development questions. It is not an overall benchmark score, a fresh-corpus
confirmation, a production-adoption gate, a budget-share test, or a tuning run.
The conversations are already complete and both arms use frozen contexts, so
assistant-path divergence cannot enter the comparison.

## 2. Frozen inputs and population

- Part 1 artifact SHA-256:
  `f1dcd160b8cdf4e78673a9795861fc6ffa6affdc0b16f19907922f53fb082e60`;
  commit `ead6ea1c`.
- LoCoMo SHA-256:
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- TC-014 selection SHA-256:
  `32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7`.
- TC-014 outcome SHA-256:
  `ce73bfcb0b3c9a1d7d94e89023ce7ef7b9fbf928eb44a1669699ec3f37324bb0`.
- Reader template SHA-256:
  `39eb518504e494d002c6e8903435a06a508f76a9427703f71a7c87f9ac4d35f8`.
- Population: all 17 questions whose full-CC80 and opportunity complete-evidence
  outcomes differ at 32k. Sixteen answerable questions are primary: 11 offline
  opportunity gains and 5 losses; 9 targeted, 5 breadth and 2 other. The one
  category-5 item is a refusal-only descriptive secondary.

No item, arm, budget or replicate may be added after registration. Stable keys
are canonical question content hashes and frozen candidate content identities.

## 3. Arms and prompts

- **C0 `FULL_CC80`:** TC-014's frozen full-budget CC80 payload.
- **T1 `OPPORTUNITY`:** TC-014's frozen 50/50 CC80-parent fan-out after exact
  opportunity admission and CC80 slack return.
- **F0 `NO_MEMORY`:** the question with the identical reader template's explicit
  no-record section. It is a Preflight contamination floor only and is not part
  of the treatment contrast.

Every arm receives the identical question and reader template. C0 and T1 differ
only in the frozen memory block. The reader is instructed to answer briefly
from the supplied conversation and to return exactly `I don't know` when the
answer is absent. Gold answers and evidence labels are forbidden from prompt
construction.

All 34 C0/T1 payloads and prompts are rendered and SHA-sealed before inference.
C0 is not produced by disabling treatment code: it is replayed from the prior
TC-014 selection artifact and must reproduce its committed digest.

## 4. Reader runtime and schedule

- Ollama `0.33.0`, endpoint `http://127.0.0.1:11434/api/generate`.
- Model `qwen-custom:latest`, manifest id `3516cd593f43`, content-addressed model
  blob `sha256-773f1bf0be0589d056ce05476a8a135b50494a3f2ecc3f8f0c4f2c3594bba02e`;
  reported architecture Qwen 3.5, 27.3B, Q6_K, context 262,144.
- GPU: NVIDIA GeForce RTX 5090. Preflight requires Ollama to report the loaded
  reader as 100% GPU; a CPU or split load stops inference.
- Raw prompt mode, thinking disabled, streaming disabled, `num_ctx=65536`,
  `num_predict=192`, temperature `.6`, top-p `.95`, top-k `20`, min-p `0`,
  repeat penalty `1.0`.
- Five reader replicates per primary arm and item. Replicate `r` uses seed
  `5005+r`. C0/T1 call order within each item-replicate is fixed by the parity
  of SHA-256(`comparison_key || replicate`) and cannot be changed after output.
- F0 runs once per primary item at seed 5005 during Preflight.
- `keep_alive=30m`; one request at a time. No failed call is retried unless the
  response is mechanically absent or the server returns an error; every retry
  and original response must be preserved and the run is then `QUALIFIED`.

## 5. Blinded scoring

All 160 primary answers and 10 adversarial-secondary answers are committed
before scoring. A seeded SHA shuffle assigns blind ids and hides arm, replicate,
offline direction, context and delivery state.

Primary scoring is semantic correctness against the LoCoMo reference answer.
The same local model performs three blind judge passes per answer with seeds
`9005`, `9006`, and `9007`, temperature `.2`, top-p `.9`, top-k `20`,
`num_predict=128`, using the frozen HH-001 binary correctness rubric. Majority
of three is the answer verdict. Majority of five answer verdicts is the
item-arm verdict. Unparseable judge output blocks unblinding; it is not silently
scored incorrect.

Deterministic normalized gold-string containment is computed on every answer as
a cross-check, never as the primary endpoint. The category-5 secondary is scored
only for explicit refusal/`I don't know`; its supplied adversarial answer is not
treated as ordinary gold correctness.

Answers, blind judge verdicts, and their commits precede opening the arm mapping
or any mechanism trace. Judge disagreement, reader unanimity, truncation,
unsupported correct answers and exact containment are all reported.

## 6. Registered outcome

For the 16 primary items, compare item-majority semantic correctness paired by
question. Report T1 gains, losses, ties, net, exact two-sided McNemar p, and the
same counts for targeted, breadth, other, offline-gain and offline-loss strata.

Apply these dispositions once:

- **`CONVERTS`:** overall net is at least `+3`; targeted and breadth nets are
  nonnegative; no endpoint-sign reversal occurs; and no validity gate fails.
- **`WEAK_CONVERSION`:** overall net is `+1` or `+2`, targeted and breadth nets
  are nonnegative, no sign reversal occurs, and no validity gate fails.
- **`NO_CONVERSION`:** overall net is exactly zero with no validity failure.
- **`REGRESSES`:** overall net is negative, or targeted or breadth net is
  negative, with no validity failure.
- **`NOT_INTERPRETABLE`:** contamination, truncation, prompt drift, judge
  completeness, endpoint-sign, runtime or ordering validity fails.

The `+3` primary bar is half the answerable offline complete-evidence net of
`+6`, rounded exactly. McNemar p is descriptive because the selected population
has only 16 items. No disposition authorizes deployment.

The endpoint-sign guard compares semantic-correctness net with normalized
gold-containment net at item-majority level. Opposite nonzero signs yield
`NOT_INTERPRETABLE`; a zero cross-check is not a reversal.

## 7. Preflight — binding before treatment generation

- **PF1 inputs:** hash and count registration, Part 1, corpus, TC-014 selections
  and outcomes, prompt templates, Ollama executable/runtime manifest, model
  manifest/blob and GPU. Missing, changed or empty inputs fail.
- **PF2 mechanism identity:** reproduce Part 1's population, block/prompt
  distributions and degenerate states. Verify only the memory block changes.
- **PF3 ordering:** seal all C0/T1/F0 prompts before F0 or treatment calls;
  commit treatment answers before judging; commit blind verdicts before arm
  mapping opens. Planted early label and mapping access must fail.
- **PF4 reachability:** synthetic five-replicate answer/judge rows must reach all
  five dispositions, both floor branches and the sign-reversal block. The real
  primary population must contain both offline gain and loss strata.
- **PF5 stable keys:** content hashes only; reject duplicate questions, prompts,
  missing joins and generated ids as comparison keys.
- **PF6 reproduction:** reproduce all 34 TC-014 payload identity sequences,
  character counts and digests plus all prompt digests twice.
- **PF7 runtime state:** one real C0 prompt run twice at seed 5005 must be
  byte-identical, nonempty and untruncated. Ollama must show 100% GPU and the
  registered model. No feedback state exists between single-turn prompts.
- **PF8 adequacy:** five replicates can take item majorities and expose reader
  instability; 16 selected items cannot estimate overall accuracy, population
  transfer or a small effect. A 35-turn ablation is not applicable because no
  120-turn or stateful run follows.
- **PF9 surrogate audit:** semantic correctness may be guessed without support;
  containment misses paraphrase and composition; judge majority may share one
  model's bias; availability selection enriches the measured population. F0,
  support reporting, three blind judge passes and the claim boundary mitigate
  but do not remove these residuals.
- **PF10 live requirement:** this is the reader test; availability is an input,
  not the verdict. A positive result remains development characterization.

Additional binding gates:

- **G-FLOOR:** F0 may be semantically correct on at most 3/16 primary items.
  Four or more yields `NOT_INTERPRETABLE` and treatment generation does not run.
- **G-PROMPT:** no prompt exceeds `num_ctx` according to Ollama's evaluated-token
  count and no reader or judge answer reaches its prediction limit.
- **G-COMPLETE:** exactly 5 C0 and 5 T1 answers exist per primary item, 5 per arm
  for the adversarial secondary, and exactly 3 parseable blind verdicts exist
  per answer.

No parameter tuning, additional reader, best-of-five selection, majority across
arms, post-result prompt revision or rerun after a valid score is authorized.
