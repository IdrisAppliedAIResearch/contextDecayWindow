# EC-002 — K-First Packing Counterfactual

**Status:** PRE-REGISTERED, NOT RUN  
**Date:** 2026-08-03  
**Parent evidence:** EC-001 through `f4ceeac5`  
**Integrity anchor:** the commit containing this file, before implementation

## 1. Trigger

EC-001 reports pooled median evidence-session rank 2 but any-session recall
109/470. Its post-run path audit finds evidence in the top four on 401/470
questions but delivery on only 96/401. Every block is truncated; median
composition is 16 recency, 0 non-recency K, and 1 coverage exchange. At least
one exchange clears `K = 0.48` on 232/500 questions, while a non-recency K
exchange survives packing on only 20/500.

The audit identifies N-first exact-budget exhaustion as the dominant observed
gate, but it does not run a counterfactual. This diagnostic tests that
attribution directly and offline.

## 2. Question

Holding the EC-001 store, embeddings, candidate sets, thresholds, selector,
budget, rendering, and scoring fixed, does giving K-threshold candidates
admission priority over recency improve Tier 1 retrieval?

## 3. Frozen inputs

- Cleaned LongMemEval-S dataset: the byte size and SHA-256 pinned by
  `EC_001_ADAPTATION_RECORD.json`.
- EC-001 source adaptation and measurement labels, unchanged.
- `EpisodicConfig` unchanged: seed 5005, recency window 32, `K = 0.48`,
  full-store A3 selector, lambda 0.1, cost exponent 0.0, 16 clusters.
- Qwen3-Embedding-0.6B Q8_0 artifact and solo call shape pinned by EC-001.
- Exact serialized budget: 32,000 characters.
- Same 500 questions; no generation and no rater calls.
- Original EC-001 Tier 1 scores and mechanism log at `08e90fa3` and
  `7511ebc`.

No reference label or rubric artifact may enter retrieval, selection, packing,
or rendering. Labels are used only after both blocks exist.

## 4. Arms

### A0 — reproduction

The unchanged EC-001 path:

1. recency candidates;
2. K-threshold candidates;
3. A3 coverage candidates.

### A1 — K-first

Change only candidate admission order:

1. K-threshold candidates;
2. recency candidates;
3. A3 coverage candidates.

Candidate sets and within-tier order are byte-for-byte identical to A0.
Selected episodes keep their original render tier: an episode in the recency
window is rendered in `<recent_context>` even when K gives it earlier admission
priority; other K and coverage episodes are rendered in `<retrieved_stm>`.
K/recency overlap is considered once, at K priority. The final order inside
each rendered block is the same order A0 would use for the selected members.
A candidate that does not fit is skipped and the walk continues.

No K floor, new budget, retuned threshold, session-level retrieval, or changed
selector is permitted.

## 5. Binding replay gate

Before A1 results may be read or aggregated, A0 must reproduce all 500 EC-001
questions:

- 500/500 delivered blocks byte-identical by SHA-256;
- 500/500 reports identical after removing `latency_ms`;
- Tier 1 score rows byte-identical after deterministic JSON serialization;
- aggregate Tier 1 summary identical;
- dataset, embedder, configuration, and original-artifact hashes PASS.

Any failure stops the diagnostic. A1 output must not be interpreted.

The implementation must prevent A1 aggregation until this gate passes.

## 6. Measurements

All measurements compare A1 with reproduced A0 on the same question.

Primary:

- any evidence-session recall, count and percentage over 470 answerable
  questions;
- paired delta in questions.

Secondary:

- all evidence-session recall;
- any and all exact annotated answer-turn availability;
- all four metrics by registered stratum;
- gained, lost, and unchanged question identities;
- delivered recency, non-recency K, and coverage counts;
- block characters, truncation, and dropped episodes;
- the 401 questions whose best evidence session was in the cosine top four;
- single-session preference separately.

Abstention has no Tier 1 retrieval score and remains excluded from recall and
availability denominators.

## 7. Outcome interpretation

The author did not register a numerical threshold for “material.” None may be
chosen after results are read.

- If A1 changes neither any-session recall nor any-turn availability, packing
  priority does not explain a recovered EC-001 item under this replay.
- If either metric increases, packing priority is a causal gate for the
  specifically recovered items because A0 and A1 differ only in admission
  order.
- Losses and mixed movements must be reported alongside gains. A positive
  gross gain is not sufficient if the net metric is unchanged or worse.

This offline diagnostic cannot promote a production change. A “one-line fix”
claim requires a separately registered live Tier 2 test because LV-001 already
showed that offline availability can move opposite to answer correctness.

## 8. Artifacts and order

1. Commit this registration alone.
2. Commit implementation and tests.
3. Run and commit the A0 reproduction gate.
4. Only after the gate commit, aggregate and commit A1 results.
5. Commit a report with this registration commit SHA in its header.
6. Update the relevant ledger, memory, README, and AGENTS digest.
7. Open a separate PR.

Planned paths:

```text
src/analysis/ec002_k_first_packing.py
scripts/run_ec002_k_first_packing.py
tests/test_ec002_k_first_packing.py
experiments/external/longmemeval/runs/ec002_k_first/
experiments/external/longmemeval/EC_002_REPORT.md
```

## 9. Exclusions

- No EC-001 locked registration, score, mechanism log, or run artifact is
  edited.
- No new inference, reader answer, rater pass, or adjudication.
- No reserved K floor or floor sweep.
- No claim that the external benchmark is officially scored.
- No mechanism promotion from this offline result.

## 10. Authorization

The author requested this same-store, same-configuration, offline packing-order
measurement on 2026-08-03. K-first is selected because it introduces no new
budget parameter; a reserved floor would.
