# HH-004 Findings - frozen DA-098 decoded arm

**Status:** `COMPLETE - CHARACTERIZED`

## Result

DA-098 decoded scored **606/842 (71.97%)** on the exact matched HH population.
Mean token F1 was `.4079`; exact match was `.0190`. Every conversation scored
between 59.26% and 76.27%.

| Matched arm | Score | DA-098 gains/losses | Net | Two-sided p |
|---|---:|---:|---:|---:|
| Episodic | 77.79% | 60 / 109 | -49 | .000202 |
| Episodic-aspect | 79.57% | 60 / 124 | -64 | 2.74e-6 |
| CDW | 77.79% | 50 / 99 | -49 | 7.33e-5 |
| RAG | 45.49% | 270 / 47 | +223 | 3.43e-39 |
| Full context | 73.87% | 85 / 101 | -16 | .271 |

The architecture did not beat the stronger episodic controls. Its small deficit
to full context was not significant in the registered paired test, while its
advantage over RAG was large. These comparisons are cross-date, as registered.

## Mechanism Reading

DA-098 reached NF-004's mechanical one-hop evidence ceiling, but model answers
did not inherit that ceiling. The decoded payload presents selected source
members as a flat sequence. Evidence availability is necessary, but locating,
integrating, and using that evidence remains a separate bottleneck. More
delivered evidence can coexist with lower answer accuracy than a smaller, more
coherent episodic context.

This run cannot distinguish context organization, distractor load, lost
conversational structure, and reader limitations. It does show that offline
availability was not sufficient as an adoption criterion.

## Operations

All 842 answers and 842 judgements completed with zero malformed judgements and
zero failed items. Decoded contexts were 52,798-58,091 characters, median
55,205. Median answer latency was 1.175 seconds (p90 2.308 seconds). Successful
sealed calls used 11,234,303 answer prompt tokens and 342,878 judge prompt
tokens; estimated synchronous model cost was $1.7434.

The watchdog detected one checkpoint stall, restarted the answer stage, and
resumed only missing stable keys. Successful-row accounting is exact; the
interrupted process may have completed up to eight uncheckpointed calls.

## Disposition

`CHARACTERIZED`. Do not adopt DA-098 from this result. The next question is
whether a reader-facing representation can preserve dependency and conversation
structure without restoring the full-context burden. Compact-wire
interpretation, fresh transfer, and production concurrency remain untested.
