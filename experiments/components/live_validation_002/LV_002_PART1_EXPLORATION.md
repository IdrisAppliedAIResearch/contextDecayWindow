# LV-002 — TC-014 opportunity reader validation: Part 1

**Status:** `PART_1_COMPLETE; NOT REGISTERED`  
**Date:** 2026-08-26  
**Candidate treatment:** TC-014 exact opportunity admission at 32,000 characters

## Behavioral identity

The control renders TC-014 full-budget CC80. The treatment renders TC-014's
50/50 CC80-parent fan-out after its exact opportunity-admission filter. The
candidate store, question, reader template and 32,000-character ceiling are
identical; only the already-frozen memory block differs.

This is a frozen-context reader test, not another conversation simulation. It
avoids the path divergence that qualified LV-001: both arms answer the same
question from contexts derived from the same completed conversation.

## Population

At 32k, TC-014 opportunity and full CC80 differ on complete-evidence delivery
for 17 of 868 eligible LoCoMo development questions:

- 12 opportunity gains and 5 opportunity losses;
- 9 targeted, 5 breadth and 3 other questions;
- 16 answerable questions form the prospective primary population;
- one category-5 adversarial question is a refusal-only secondary.

The population is deliberately availability-discordant. It can test whether a
known delivery change converts into a reader change; it cannot estimate either
arm's overall LoCoMo accuracy or transfer beyond these selected questions.

## Prompt and block behavior

All 34 frozen blocks reproduce TC-014's selected identity order, character
count and payload SHA-256 exactly.

| Measure | Full CC80 | Opportunity |
|---|---:|---:|
| Block chars, min / median / max | 31,881 / 31,985 / 31,999 | 31,891 / 31,983 / 31,998 |
| Selected pairs, min / median / max | 91 / 105 / 123 | 86 / 98 / 116 |
| Full prompt chars, median | 32,347 | 32,340 |

The arms share a median 89 selected pairs. Their symmetric difference is
9–52 pairs, median 30. No selected set or prompt is identical, so the treatment
is active on all 17 questions.

## Degenerate and surrogate states

Literal normalized gold-answer containment is identical between arms on 13/17
questions; neither block contains the complete gold string on those 13. Only
four questions expose a literal containment difference despite all 17 having a
complete-evidence difference.

Therefore gold-string containment can pass or tie while the reader has enough
source statements to compose a correct answer. It cannot be the primary live
endpoint. A registration must use blinded semantic correctness, retain
containment as a cross-check, and separately score the category-5 refusal.

The opposite surrogate also remains: semantic correctness can arise from
pretraining or guessing when evidence is absent. A no-memory floor and
support/attribution audit are required before interpreting conversion.

## Runtime observation

The historical llama.cpp endpoints on ports 8000 and 8080 are not running.
Ollama 0.33.0 is available on port 11434 with `qwen-custom`, reported as Qwen
3.5, 27.3B parameters, Q6_K, 262,144-token context. The prospective
registration must bind this runtime rather than silently inheriting LV-001 or
HH-001's different reader.

## Integrity boundary

- LoCoMo SHA-256:
  `79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4`.
- TC-014 selection SHA-256:
  `32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7`.
- TC-014 outcome SHA-256:
  `ce73bfcb0b3c9a1d7d94e89023ce7ef7b9fbf928eb44a1669699ec3f37324bb0`.
- Zero embedding, reader or judge calls were made.
- No live bar, prompt schedule or disposition is locked by this exploration.
