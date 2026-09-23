# AF-PRE-003 RESULTS — the user's single-model proposal, tested: **INTERFERENCE**

Registered (`3ec83128`) before data, training, or evaluation. Frozen config; no post-hoc tuning.

## Numbers (bars as registered)

| surface | BM25 | zero-shot CE | regex event rule | **fine-tuned CE** | bar |
|---|---|---|---|---|---|
| E-17 gap anchors | 0 | 0 | 17/17 | **17/17** | ≥15 → **PASS** |
| LoCoMo sample-120 | 29 | 25 | — | **8/120** | ≥29, net ≥0 → **FAIL** (net −21, p=1.04e-4) |

Verdict per the registered matrix: **INTERFERENCE** — exactly one bar passed. The event skill was trained in; the answer skill was trained away, despite 1,411 answer-shaped pairs (3× more data than event pairs): the fine-tuned model scored *below its own frozen starting checkpoint* on natural questions (8 vs 25).

## Descriptive anatomy (post-verdict, non-binding)

- Per category (ft/bm25 of n): cat-4 **5/21** of 57, cat-2 2/8 of 33, cat-1 0/0, cat-3 1/0 — the collapse is broadest exactly where answer-token overlap is the winning cue.
- ft_only=4 vs bm25_only=25: not a shuffle, an overwriting.
- Mechanism reading consistent across three probes: the event task's whole lesson is *ignore answer-token overlap* (the training negatives were literally the lexical-answer lines BM25 picks). That lesson transfers globally; on natural questions it deletes the very cue BM25 and the base CE used. AF-PRE-002 saw the same law from the score side (hybrid 29→17); AF-PRE-003 shows it from the gradient side. The two skills conflict through one shared decision — trust or distrust lexical answer overlap — and one score cannot conditionally trust it.

## What this settles and what it doesn't
- **Settles (for this design space):** one cross-encoder, one scalar score, trained on this mixture, cannot hold both skills; consolidation by shared weights inherits the conflict, it does not dissolve it. The regex keeps the event surface: 17/17 at zero cost.
- **Does not settle:** a single *artifact* with a task signal (prompt prefix, task head, routing feature) was never tried and is not excluded by these results — but note it concedes the point: a task signal is the second mechanism, relocated inside one file. "One model" survives as engineering packaging; "one score for both jobs" is dead on this evidence.
- Contamination guards held (sample-120 and E gaps absent from training, asserted in build). No bar was moved; `INTERFERENCE` was one of four registered outcomes and is reported with its full margin.

Artifacts: `artifacts/pairs.json`, `artifacts/ckpt/`, `artifacts/ft_ce_results.json`.
