# HH-001 Amendment 001 - Mem0 Ingest Token Window

**Status:** `POST-OUTCOME CORRECTION OF A REPORTED VALUE`
**Trigger:** reader question about extrapolating Mem0's ingest cost to LoCoMo
**Date:** August 21, 2026
**Direction:** the correction **reduces** Mem0's measured cost. It runs against
this programme's own argument and is recorded for that reason.

## Trigger and evidence

A reader asked whether HH-001's per-pair ingest token rate could be used to
project Mem0's cost on LoCoMo. Checking whether the rate was fit to extrapolate
showed that it is not, because the quantity it derives from is not what it was
labelled.

`cost/mem0_ingest_tokens.json` samples llama-server's **cumulative** prompt-token
counter every 180 s. That counter is process-wide. It was not reset for the
ingest and is not scoped to Mem0. `window_prompt_tokens` is the delta across the
whole sampling window, and C5 reported that delta as Mem0's ingest cost.

Mem0's own history table dates every write:

| | |
|---|---|
| Mem0 first write | `2026-08-20T15:43:57Z` |
| Mem0 **last** write | `2026-08-20T20:31:29Z` |
| Token sampling window | `16:21:15Z` -> `22:15:19Z` |

**The counter ran 105 minutes past Mem0's last write and accrued 4,376,100
prompt tokens in those minutes - 73% of the reported total.** Those tokens
belong to the reader phase, which ran on the same llama-server.

The window's 287.5-minute write span agrees with `cost/mem0_ingest.json`'s
independently recorded `total_seconds` of 283.7 minutes, so the ingest is bounded
by the write log and the overrun is not ingest that merely stopped writing.

Two further checks, both in the derivation script:

1. **The uncovered head cannot be added back.** Sampling began 37 minutes into
   the ingest, at a counter value of 317,062. Treating that as ingest would
   assume a fresh counter. The head's cumulative prompt/predicted ratio is
   **1.424** against the overlap's **1.010**, so the head contains non-ingest
   work - a pilot ingest and the timing and contamination probes ran earlier on
   the same server. The head is excluded and the overlap is scaled instead.
2. **The per-pair cost does not climb with store size.** Regressing the
   per-interval token rate on memories-already-stored, inside the overlap only,
   gives a slope of **-0.444 tokens/min per stored memory** across 246 -> 1,816
   memories: a fall of about 697 tokens/min on a base of 6,476. The rate is flat
   to mildly declining.

## Change

C5 is superseded. The values below replace it, with their provenance class.

| | value | class |
|---|---:|---|
| Prompt tokens measured inside the ingest overlap (86.6% of it) | **1,612,718** | MEASURED |
| Prompt tokens, whole ingest, overlap scaled by wall clock | **1,862,108** | RECOMPUTED |
| Prompt tokens per ingested pair (1,646 pairs) | **1,131** | RECOMPUTED |
| Completion tokens, whole ingest, same scaling | **1,843,446** | RECOMPUTED |
| Published figure's inflation | **3.22x** | derived |

The withdrawn claim "the cost per pair climbs as the store grows" is replaced by
the finding that it does not. The drift that does exist is in **latency**, at
1.13x first-to-last decile, already reported from
`cost/mem0_ingest_latency.json` and already correctly captioned on Figure 4.

New artifact: `cost/mem0_ingest_tokens_corrected.json`, written by
`scripts/hh001_ingest_token_correction.py`. Every field is derived; none is
typed. The original artifact is not edited.

## History of this value

This is the **second** correction to C5, and the two run in opposite directions.
The first found that an earlier draft divided a short early window by *memory
writes* and labelled the result per *turn*, understating Mem0's cost roughly
fourfold. That correction fixed the denominator and left the numerator alone.
The numerator was the defect.

The spine's own note on the first correction said it plainly: the gate checks
that a number is in the spine, not that the spine is right. That remains true,
and it is why the derivation is now a script with hashed inputs rather than a
figure carried in prose.

## What does not change

C1 (1,646 generative calls), C2 (1.0 per pair), C3 (284 minutes), C4 (zero calls
for this component), every L-series retention number, every R-series read-side
number, and the registered contrast H1-H6 are untouched. This amendment changes
no corpus, split, population, score, endpoint, statistic, threshold, or gate, and
no bar's outcome depends on it.

**The architectural claim is unaffected.** 1,646 generative calls against zero
is the load-bearing comparison and it was never a token count.

## Exclusions

This amendment makes no criterion easier. It reduces a number this programme had
been quoting in its own favour.
