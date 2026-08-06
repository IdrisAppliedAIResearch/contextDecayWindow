# EC-001 Amendment 009 — Manual-switch Codex-agent evaluators

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Scoring amendment anchor:** `37864822e4c429412b81f67db8af4af804308b8f`  
**Latest completed rater commits:** Phi `53fb26fc`; Mistral `06b6b3dd`  
**Status:** AUTHORIZED BEFORE IDENTITY UNSEALING, TRIGGER PREPARATION, OR FINAL AGGREGATION  
**Authorization:** Program author, August 3, 2026: “We will use these as
replacements for the API models,” followed by “Make amendment.”

## Trigger and evidence

The registered GPT-4o benchmark pass and GPT-5.2 adjudicator are unavailable:
the provisioned `OPENAI_API_KEY` returns HTTP 401 for both pinned models. The
failure and the zero-unsealing boundary are committed in
`runs/scoring_001/openai_access_gate_failure.json`.

The program author can select hosted Codex models in the desktop model picker,
but the current subagent interface exposes only Sol and Terra as explicit model
overrides. Other selected parent models can be passed to a child only through
model inheritance. The current session is too large for the smallest requested
model, so each evaluator needs a fresh child context after a manual parent-model
switch.

## Change

### Claims withdrawn

- Do not produce or impute the registered **benchmark-protocol GPT-4o score**.
- Do not compare a Codex-agent score directly with published LongMemEval
  numbers.
- Withdraw the claim that the replacement panel contains distinct architecture
  families. These are hosted OpenAI/Codex model variants and may share biases.
- The committed Phi and Mistral passes remain reported as supplementary local
  diagnostics, not members of the replacement consensus panel.

### Replacement panel and fixed order

Run five blind Codex-agent rater passes in this order:

1. **GPT-5.4 mini**
2. **GPT-5.4**
3. **GPT-5.5**
4. **GPT-5.6 Luna**
5. **GPT-5.6 Terra**

Use **GPT-5.6 Sol** only as the independent Codex-agent adjudicator. Sol must
not contribute a panel vote.

Each rater receives the existing 140 masked packets and the existing four
planted calibration cases. Each produces an exact binary label and a separate,
answer-grounded rationale for every non-mechanical-zero item. The five
mechanical-zero labels remain fixed without a model call.

### Consensus and adjudication

- Report every model-specific score separately.
- The replacement **Codex-agent consensus score** is a new, non-benchmark
  diagnostic.
- Unanimous five-rater labels are final unless selected by H5.
- Any disagreement among the five labels is H2 and is adjudicated by Sol.
- H1, H3, H4, and H5 retain Amendment 004's definitions. H3 and H4 remain zero
  applicable. H5 remains the deterministic 10% sample under
  `sia-h5-2026-07-26-v1`.
- Sol receives masked item content and the registered adjudication view. It
  receives disagreement rationales without model identities for H2 and no
  panel labels for H5.
- Sol adjudication takes precedence for triggered items.

### Manual-switch, fresh-context protocol

Every model stage has two manual steps:

1. **STOP / SWITCH.** The orchestrator commits a checkpoint naming the exact
   next display model and stops. The user changes the parent task's model in
   the desktop picker, then sends the checkpoint's exact resume phrase.
2. **SPAWN / RUN.** The selected parent spawns one child with
   `fork_turns="none"` and no explicit model override. The child therefore
   inherits the manually selected parent model while receiving no conversation
   history. The child reads only the registered evaluator instructions,
   calibration set, masked packet file, and its named output target.

The fixed stages and resume phrases are:

| Stage | Parent model selected by user | Role | Resume phrase |
|---|---|---|---|
| C1 | GPT-5.4 mini | rater | `EC001 RESUME C1 GPT-5.4-MINI SWITCHED` |
| C2 | GPT-5.4 | rater | `EC001 RESUME C2 GPT-5.4 SWITCHED` |
| C3 | GPT-5.5 | rater | `EC001 RESUME C3 GPT-5.5 SWITCHED` |
| C4 | GPT-5.6 Luna | rater | `EC001 RESUME C4 GPT-5.6-LUNA SWITCHED` |
| C5 | GPT-5.6 Terra | rater | `EC001 RESUME C5 GPT-5.6-TERRA SWITCHED` |
| C6 | GPT-5.6 Sol | adjudicator | `EC001 RESUME C6 GPT-5.6-SOL SWITCHED` |

After each child finishes, the parent validates and commits that stage's
artifact, advances the checkpoint, and stops before the next model switch.
Partial, malformed, or uncalibrated output is never carried into the next
stage. A retry uses a new inherited child under the same manually selected
parent model and records the failed attempt first.

### Model identity and reproducibility boundary

The user-selected display model and resume phrase are a manual attestation.
The Codex subagent interface does not expose an immutable API snapshot, fixed
seed, temperature, or model-build hash for inherited hosted agents. Therefore:

- report display-model identity and parent/child task identifiers where
  available;
- report these results as hosted Codex-agent judgments, not seeded API
  inference;
- do not claim byte-level rerun reproducibility or checkpoint equivalence;
- record any model-picker or inheritance mismatch as a binding stop.

### Blindness boundary

The child is instructed not to read the sealed identity map, other model
outputs, trigger files, mechanism logs, or final aggregation artifacts. It
must not use web search or external tools. `fork_turns="none"` removes parent
conversation history, but filesystem blindness is instruction-enforced rather
than sandbox-enforced; this is an accepted and reported limitation.

## Rationale

This substitution makes progress without pretending that Codex product access
is the pinned Platform API. Manual switching is necessary because four of the
requested models are visible in the desktop picker but unavailable as explicit
spawn overrides. A no-history inherited child gives each model the smallest
fresh evaluator context and makes the handoff feasible for GPT-5.4 mini.

Separating all model-specific results and renaming the aggregate prevents the
replacement from inheriting benchmark-comparability or family-independence
claims it cannot support.

## Exclusions

- Do not edit or reinterpret the committed reader answers, packets, local
  rater outputs, mechanical-zero decisions, calibration labels, or rubrics.
- Do not open `SEALED_MASK_MAPPING_DO_NOT_OPEN.json` before all five rater
  outputs, trigger registration, and Sol adjudications are committed.
- Do not let a parent model score items directly; scoring occurs only in its
  fresh inherited child.
- Do not use an explicit Sol or Terra override during C1-C5; every child must
  inherit the manually attested parent model.
- Do not count Sol as both rater and adjudicator.
- Do not call the replacement output human adjudication, official LongMemEval
  scoring, or a three-family integrity score.
