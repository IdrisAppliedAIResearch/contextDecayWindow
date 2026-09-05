# AV-READER-001 — the reader, not the retrieval

**Status:** `PARTIAL — paired 305-item read, full 1,540 not run`
**Date:** September 2, 2026
**Cost:** ~1,400 reader + judge calls, local GPU. No paid API.
**Runners:** `src/analysis/av_variants.py`, `src/analysis/av_watchdog.py`
**Artifacts:** `experiments/components/aspect_v3/artifacts/av_reader_001/`

---

## 1. Why this exists

AV-MATRIX found six compositions within 2.38 points and nothing significant.
Decomposing its errors showed why:

| `A_CC80@32k`, 1,536 items with evidence annotations | count | share of errors |
|---|---:|---:|
| Total errors | 434 (28.3%) | |
| **Evidence WAS delivered** | **349** | **80.4%** |
| Evidence not delivered | 85 | 19.6% |

And accuracy *given* the evidence is flat across every composition and budget —
75.1%, 74.5%, 74.8%, 74.0%. One item in four has the answer in the context and
is still answered wrong, and no selection mechanism moves that number.

The binding constraint is downstream of retrieval.

## 2. The obvious objection, and the test for it

AV-MATRIX ran the vendor prompt, which is:

```
# Question:
{{QUESTION}}

# Context:
{{CONTEXT}}

# Short answer:
```

If the reader is not reasoning over the context, three ways of *selecting*
context would score the same because nothing exploits the difference. So
"composition does not matter" could have been an artifact of the prompt.

That is a real confound and it was tested rather than argued: the same three
compositions, at 32k, under an instructed prompt that asks the model to locate
the bearing turns, anchor dates to those turns rather than to today, combine
multi-hop turns, and avoid inventing absent facts. **Retrieval is byte-identical
between the two prompt conditions.** Native reasoning stays OFF, so this remains
portable to `gpt-4o-mini`, which has no thinking mode.

## 3. Result — paired, 305 items answered by all three arms under both prompts

| arm | vendor | reasoned | delta | gains/losses | p |
|---|---:|---:|---:|---:|---:|
| CC80 | 73.1% | 82.6% | **+9.5** | 36/7 | <.001 |
| CC80+ASPECT | 75.1% | 82.6% | **+7.5** | 31/8 | <.001 |
| CC80+ASPECT+DA | 75.1% | 83.3% | **+8.2** | 36/11 | <.001 |

| | composition spread |
|---|---:|
| under vendor prompt | 2.0 pts |
| under reasoned prompt | **0.7 pts** |

**The confound is refuted.** Compositions do not separate under a reader that
reasons — they converge. AV-MATRIX's flat result was not an artifact of a weak
prompt, and the prompt is worth roughly four times the entire composition space.

## 4. Where the gain comes from — one stratum

CC80 arm, n=305:

| category | n | vendor | reasoned | delta |
|---|---:|---:|---:|---:|
| 1 | 68 | 75.0% | 77.9% | +2.9 |
| **2** | **66** | **40.9%** | **77.3%** | **+36.4** |
| 3 | 22 | 59.1% | 63.6% | +4.5 |
| 4 | 149 | 88.6% | 89.9% | +1.3 |

Category 2 is the temporal stratum — the weakest one, and the one this
programme already measured at an 11.21% judge floor. Nearly the whole effect
lives there, and the mechanism is visible in the raw output:

| question | gold | vendor | reasoned |
|---|---|---|---|
| When did John start his 2D game? | approximately summer of 2022 | "The past few months" | "a few months before 20 September, 2022" |
| When did Gina design the hoodies? | June 2023 | "Last week" | "the week before 21 June, 2023" |

The vendor prompt answers relative to nothing. Its system message does say "if
the question involves timing, use the conversation date for reference", and
nothing enforces it. The instructed step makes the model anchor to the turn's
own date, and the answer becomes gradeable. The information was always in the
context.

## 5. Limits

- **305 items, one sample per arm, no replicate.** The prompt effect is large
  and consistent across three independent arms (p<.001 each). The *spread*
  comparison, 0.7 against 2.0, rests on much smaller differences and should not
  be over-read.
- **V2 is a bundled change** — system message, four reasoning steps, temporal
  rule, and output format all moved together. Which part earns the ~8 points is
  unattributed. The category-2 concentration points hard at the temporal rule,
  but that is inference, not measurement.
- **Same-model judging**, and the judge saw longer answers in the reasoned arm.
- Absolute scores are not comparable to HH-003's gpt-4o-mini numbers.
- The full 1,540-item run was not completed; this is the paired subset.

## 6. Two harness defects found, both of which would have corrupted results

- **Qwen3.8 is a hybrid reasoning model.** With reasoning on it spends the whole
  token budget on a `<think>` block and no answer arrives. Also,
  `reasoning_format: none` does not suppress it — the text moves to a separate
  `reasoning_content` field, which is how an earlier "zero thinking overhead"
  measurement here was wrong.
- **A lenient judge parser is worse than none.** An early version fell back to
  searching prose for "correct"; the model's own text says it constantly, so
  malformed judgements would have scored CORRECT.

Neither was caught by any guard — both by ad-hoc inspection, one only because
the user asked. `av_watchdog.py` is the check that should have existed: it reads
the checkpoints a run already writes and gates on truncation
(`finish_reason == "length"`), format misses, empty answers, degenerate answer
distributions, stalls, malformed judge labels, and server health.

## 7. What it changes

The aspect and DA line is closed by AV-MATRIX and is not reopened here — the
compositions converge rather than separate. The remaining measured headroom is
in the reader, and the largest effect found anywhere in this arc came from a
prompt, on frozen retrieval, in one afternoon.

Unattributed and worth isolating next: which of the four instructed steps
carries the temporal gain, and whether it transfers to `gpt-4o-mini`, where it
would apply to the published 79.09% result directly.
