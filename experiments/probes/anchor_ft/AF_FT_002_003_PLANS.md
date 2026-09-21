# AF-FT-002 — V1 landscape forensics + teacher-filtered reintroduction of the 519

**Status: PREREGISTERED (design below committed before implementation).**
**Depends on**: AF-FT-001 CLOSED (`7d9bad72`). **Budget**: zero LLM calls; ~5 GPU trainings; ~10 min.
**User authorization (2026-10-02)**: "move forward with the follow ups. Training cost is practically $0."

## Part A — forensics (distinguishes the poisoned-landscape account from alternatives)

For V1 seed 20261011 and R0 seed 20261011, re-score sample2 ungated and record per item:
predicted turn's BM25 rank, predicted turn's question-token Jaccard overlap, whether pred is in
the frozen training pool (A∪E), and the gold's ungated rank. The AF-FT-001 account predicts V1's
top-1s sit at **lower BM25 ranks and lower overlap** than R0's (landscape junk inflation), while
gated ranking stays sane. Alternatives it would falsify: V1 top-1s mostly still in-pool (then the
failure is different); V1 top-1s at high overlap (then not anti-lexical).

## Part B — teacher-filtered reintroduction

The 519 = eligible items whose gold is outside BM25-top-20∪event pool (excluded by 005, added
wholesale by V1, suspected poison). Teacher = champion `ckpt2` (original, frozen).
**Filter rule (the only new lever):** score pool∪gold with the teacher; keep the item iff
**teacher ranks its gold top-1** within that set. Survivors = hard rows the champion already has
signal for; rejects = rows requiring anti-lexical behavior.

| config | rows | head | seeds |
|---|---|---|---|
| **F1** | champion 772 + E 1287 + **survivor rows** (V1 build rule: all golds credited, multi-positive) | single | 5 (same seed block) |
| **F2** | F1 rows + 800 frozen nulls, 120 held out (V2 recipe on filtered data) | null, margin .5, LS .05 | 5 |

Report survivor count (expect 100–300 of 519; <30 → flag underpowered). F1 vs V1 isolates the
filter on ungated any/exact; F1 vs R0 the joint effect; F2 vs V2 the filter under the null head.

**Bars (same as AF-FT-001)**: WORKS = any ≥+8 vs R0 seed-mean, McNemar p<.05 all seeds, exact
≥R0−2, E 17/17. SIGNAL = ≥+4. Else DEAD. F-configs that reach SIGNAL move the reader arm forward;
DEAD closes "filtered hard rows" as a lever and the 519 stay out.

# AF-FT-003 — V2 bundle decomposition (null-rows vs margin vs smoothing)

**Status: PREREGISTERED.** Budget: 9 GPU trainings (~15 min). Data fixed = V1H (V1 minus 120
held-out), 120-item eval as registered.

| config | null rows | margin | LS | seeds |
|---|---|---|---|---|
| **N1** | yes (800 frozen) | 0 | 0 | 3 |
| **N2** | yes | 0.5 | 0 | 3 |
| **N3** | yes | 0 | 0.05 | 3 |

(V2 = N1+margin+LS already run, 5 seeds — reference; R0 reference.) Metrics: ungated any/exact vs
R0, E-17, plus **null quality** (H120 AUROC, coverage@leak from the frozen threshold table) for
each config's first seed. Interpretation pre-stated: if N1 alone restores the landscape, the null
**rows** carry the repair and margin/LS are accessories; if only N2/N3 restore it, the regularization
does, and null rows are not the mechanism the story claims. No bar — this study decomposes a
worked bundle, it doesn't test a new claim.

## Process
`experiments/probes/anchor_ft/af_ft002.py` (forensics + filter build + F grid),
`af_ft003.py` (N grid), shared eval reused from `af_ft001.py`; results appended under
`artifacts/ft002/`, `artifacts/ft003/`. Plans this commit, code after. RESULTS_002/003 files,
dispositions literal.
