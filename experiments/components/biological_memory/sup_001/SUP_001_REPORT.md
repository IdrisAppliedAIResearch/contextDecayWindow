# SUP-001 - Explicit Supersession Lineage Report

**Pre-registration anchor:** `22abfc42b0cb70b3b7baebffdf52b97b14bd950e`  
**Pre-registration SHA-256:** `3651403d754eaecaa2f9baa7fe2de44f3eba48e0d9a2a4078491598ee41e3ebd`  
**Final design anchor:** `b81d01c6`  
**Passing Preflight anchor:** `a79925bb`  
**Offline outcome anchor:** `125d65b1`  
**Ablation stop anchor:** `713149c7`  
**Date:** August 11, 2026  
**Status:** `ABLATION_INTEGRATION_STOP - OFFLINE MECHANISM SUPPORTED`

## Result

SUP-001 tested the P5/P9 and F6 subset of
`HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md`: keep immutable old
and new traces, make only the current leaf naturally accessible, and recover
history through an explicit lineage route.

The offline mechanism passed all five gates:

| Measure | C0 | T1 | Binding result |
|---|---:|---:|---|
| Updated queries current-only | 0/64 | **64/64** | PASS; gain +64, bar +16 |
| Unchanged targets present | 32/32 | **32/32** | PASS; zero losses |
| Exact three-version histories | n/a | **64/64** | PASS |
| Stale versions in natural T1 payloads | n/a | **0** | PASS |
| Stored episodes / rewritten text or vectors | 256 / 0 | **256 / 0** | PASS |

C0 already retrieved the current version on all 64 updated queries, but also
retrieved both stale versions every time. T1 did not improve semantic matching;
it removed a stale-conflict class. Every current leaf ranked first after the
128 silent ancestors were excluded.

The required 35-turn Qwen reader ablation then stopped promotion:

| Reader measure | C0 | T1 |
|---|---:|---:|
| Exact answers | 7/9 | **8/9** |
| Current values | 3/4 | **4/4** |
| Unchanged values | 3/4 | **3/4** |
| Ordered history | 1/1 | **1/1** |
| Targeted regressions | - | **0** |
| Stale natural payloads | 4/4 | **0/4** |

T1's only failure was the unchanged donation probe. Its payload contained the
registered `$35`, but the reader output `$35.00`. The locked exact-string rule
does not normalize numeric formatting, so 3/4 unchanged answers fails the
all-four bar. The binding disposition is `ABLATION_INTEGRATION_STOP`; no
120-turn run, production promotion, or adoption is authorized.

## Plain-language meaning

The memory mechanism did what it was designed to do. It kept the old facts for
audit, hid them from ordinary recall, surfaced the newest fact, and returned
the full history when explicitly asked. This closed a real mechanical gap in
the prior append-only store, which had no way to distinguish current from
stale values.

That did not earn deployment. Once a reader was added, the system missed one
strict output contract even though it had delivered the right evidence. This
is not a stale-memory failure; it is a representation/answer-format failure.
The study's bar intentionally required both retrieval and reader behavior, so
the promising mechanism remains characterized rather than promoted.

## Integrity

The pre-registration preceded implementation. The 256-episode corpus and
sealed key reproduced byte-for-byte in independent processes. A retained cache
bound 352 solo-call float32 vectors; C0 reproduced every 256-way population,
cosine, top-8 identity, payload byte, character count, and digest. Part 1 ran
all 192 registrations, reached 64 accessible leaves and 128 silent ancestors,
rejected every registered degenerate state, and reproduced in a fresh process.
PF1-PF10 passed before the sealed key or T1 outcomes opened.

The ablation used Amendment 001 because unknown generated probe answers could
not both enter memory and exist in a pre-run read-only cache. The amendment
froze retrieval memory after the 26 planted exchanges while retaining all 35
user turns and nine reader calls. C0 ran from separate prior code at
`69b33275`; T1 ran from a separate worktree at `c87d962e`. Both used the same
35-vector cache, Qwen3.6-27B model hash `f3b4a622...`, llama.cpp build
`b9294-0f3cb3fc8`, seed 5005, one slot, no speculative decoding, and exact 32k
packing. The first two prompts in each arm repeated byte-identically.

One protocol deviation is retained: mechanism context summaries were inspected
during runtime validation before the mechanical score artifact was committed.
The scorer was fixed exact-string equality with no adjudication, so inspection
could not change a row, and the study fails independently. It nevertheless
violates the preferred score-before-mechanism-log ordering and limits the
ablation's procedural cleanliness.

`NEUROSCIENCE_LANDSCAPE.md`, named by the hypothetical reference, was not
present in this checkout and was not silently substituted. The executed study
was bound directly to the root hypothetical document's P5/P9/F6 claims.

## Limits

- Update metadata is explicit. Contradiction detection from natural text was
  excluded and remains unsolved.
- Binary accessibility was tested on four template domains and one 35-turn
  integration, not long-run or natural conversation ecology.
- The ablation failure does not refute supersession; it shows that correct
  delivery alone does not guarantee exact reader formatting.
- No retrieval-induced suppression, consolidation, gist, temporal capture,
  rewrite, deletion, or production integration was tested.

## Verification

Primary artifacts:

- `artifacts/sup001_corpus/`
- `artifacts/sup001_vectors/`
- `artifacts/sup001_control/c0_frozen.json`
- `artifacts/sup001_part1/part1.json`
- `artifacts/sup001_preflight/preflight.json`
- `artifacts/sup001_treatment/t1.json`
- `artifacts/sup001_measurement/measurement.json`
- `artifacts/sup001_ablation_lock/`
- `artifacts/sup001_ablation_vectors/`
- `artifacts/sup001_ablation_raw/`
- `artifacts/sup001_ablation_score/score.json`

Focused SUP-001 suite: 32 passed. Full repository suite: 1,593 passed and 11
inherited Windows/hash-anchor failures, exactly the pre-study failure set. No
historical locked hash was changed to hide them.
