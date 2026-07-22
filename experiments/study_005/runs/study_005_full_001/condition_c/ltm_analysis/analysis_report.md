# Study 005 Distilled-LTM and Arbitration Analysis

**Run:** `study_005_full_001`

**Sequence:** Opened after score and structural lock commit `1bbfad7`.

## Summary

Dreaming and retrieval were mechanically active, but the distilled store did
not meet its factual-content contract. Four scheduled dream events wrote 12
faithful content records with no inference calls, markers, non-content records,
or deduplication. Only 2 of 4 domains contained a locked rubric-critical fact.

## Formation

| Event | Scope | Selected source turns | Records |
|---:|---:|---|---:|
| 31 transition | 30 | 4, 17, 20 | 3 |
| 61 transition | 30 | 31, 40, 41 | 3 |
| 91 transition | 30 | 61, 69, 84 | 3 |
| 111 flush | 21 | 92, 105, 108 | 3 |

- Extractor: `capitalized_sequence_fallback`
- Content records: 12
- Faithful to source provenance: 12/12
- Non-content: 0
- Marker records: 0
- Inference calls during dreaming: 0
- Near-duplicates collapsed: 0
- Compression: 12/111 dreamed episodes = 10.81%; 12/121 full-run episodes =
  9.92%

The locked fact matcher found `civil_steel`, `civil_load`, and
`monetary_taylor`. It found no Renaissance-art or marine-biology target.

## Selection diagnosis

The real-run topics all cleared the salience floor, so each event reduced to a
top-three ranking. Whole conversation episodes combined user facts with model
answers. Long model answers accumulated many incidental named entities and
numbers and outranked compact plants.

| Domain | Plant turns | Ranks | Selected plants |
|---|---|---|---|
| Civil | 3, 4 | 28, 3 | 4 |
| Art | 55, 56, 60 | 18, 28, 19 | None |
| Monetary | 61, 62, 65 | 1, 5, 6 | 61 |
| Marine | 100, 101, 102 | 11, 16, 17 | None |

The algorithm's extraction and cap were correct. The salience proxy and
whole-episode granularity were not aligned with durable factual value.

## Breadth probes

| Probe | STM candidates | Distilled candidates/final | Source turns |
|---|---:|---:|---|
| Q11, turn 120 | 0 | 5/5 | 4, 41, 61, 17, 92 |
| Q14, turn 121 | 0 | 5/5 | 4, 61, 84, 105, 17 |

Distilled LTM was the only arbitration source at both probes, but placement did
not imply usefulness. Q11 had nominal records from all four source regions but
art turn 41 and marine turn 92 lacked the locked facts. Q14 had no art source
record. Bar 2 remains not evaluable because Bar 1 failed.

The promotion control retained 14 records from turns 1, 2, 3, 4, 5, 6, 7, 8,
9, 14, 46, 48, 55, and 100. Under the same locked matcher, its store contained
facts from civil, art, and marine domains but not monetary policy. Its Q11 and
Q14 retrieval nevertheless favored early bridge/rule records and both breadth
scores were zero. This reinforces the precondition logic: both store content
and broad-query retrieval matter, but treatment failed the earlier stage.

## Consolidation and runtime

- Final topic count: 5
- Cross-domain purity events: 0
- Probe-bridge guard exercised in full run: no
- Treatment peak context: 16,171 tokens, 32.34% of capacity
- Control peak context: 10,006 tokens, 20.01% of capacity
- Treatment average throughput: 36.022 tokens/s
- Control average throughput: 37.318 tokens/s

The one topic merge at turn 20 remained within civil engineering. The full run
did not attempt a probe-bridge merge, so guard behavior is supported by the
synthetic run rather than credited here.

## Interpretation

The failed mechanism is selection. The write path captured the facts, the
dream cadence reached every domain, distilled records were faithful, and the
read path placed records into both breadth probes. The top-three episode score
discarded the relevant art and marine source turns before retrieval could act.

The next intervention should use atomic factual spans and role-aware or
length-normalized scoring. Retrieval diversity is not yet triggered because
the treatment did not pass the preregistered facts-in-LTM precondition.
