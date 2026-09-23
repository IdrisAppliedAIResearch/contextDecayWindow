# AF-PRE-003 (registered before run, 2026-09-20): one fine-tuned cross-encoder for BOTH surfaces

**The proposal under test (user's):** fine-tuning a single BERT-class cross-encoder on both
answer-shaped and event-shaped supervision yields one model that handles both question types —
two mechanisms being architectural bloat. This probe gives the proposal its fairest shot and
the pre-registered right to kill the alternative.

**Specialists to match (all previously run, same items, same gold):**
| surface | regex event rule | BM25 | zero-shot CE |
|---|---|---|---|
| E-17 gap anchors (top-1) | **17/17** | 0 | 0 |
| LoCoMo sample-120 (top-1) | 17 (hybrid) | **29** | 25 |

## Training data (constructed by this probe; frozen before training)
- **Eval exclusion (contamination guard, asserted in code):** the 17 E-gap items and the
  120 sample-120 qids never appear in training.
- **Event pairs (E generator):** every E curve whose query parses to a unique
  `meeting "<name>" … took place` line (verified unique on all parseable curves), minus the
  17 eval gaps → pos = anchor event line; hard negatives = BM25 top-3 non-anchor turns of the
  same history (the answer-shaped record lines that fooled every retriever — the model is
  explicitly punished for picking them). Oversampled ×4 against the LoCoMo stream (template data is scarce).
- **Answer pairs (LoCoMo):** every eligible cat 1-4 item outside sample-120 (pool = the 1,527
  eligible from Part 1e) → pos = earliest-evidence gold turn; negatives = BM25 top-3 non-gold
  + the echo turn (max token-Jaccard with query, non-gold) — the failure class diagnosed in
  AF-PRE-001/002 is built in as a negative, not left to emerge.
- No other data. No LLM readers at any point; the model is a BERT classifier (user-authorized), GPU-serial.

## Model & config (frozen; no post-hoc tuning)
`cross-encoder/ms-marco-MiniLM-L-6-v2` at pinned revision (same weights AF-PRE-001 scored
zero-shot — the test is what supervision adds to the exact prior we measured). Pairwise
cross-entropy over 1 pos + 4 negs per query, AdamW lr 2e-5, wd 0.01, warmup 10%,
3 epochs, batch 16 queries, max_len 256, fp32. Checkpoint = final (no dev selection).

## Bars and verdicts (binding, registered before training)
- **PASS-EVENT:** FT-CE top-1 on the 17 E gaps ≥ 15 (regex = 17; zero-shot = 0).
- **PASS-ANSWER:** FT-CE top-1 on sample-120 ≥ 29 and net discordant vs BM25 ≥ 0.
- **CONSOLIDATION_WINS** — both pass: the user's single-model proposal matches both
  specialists in this setting; the regex folds into weights and the two-mechanism design is dead.
- **STRONG** — additionally net ≥ +10 vs BM25 with McNemar p < .05: the single model
  *beats* the lexical floor; consolidation with margin.
- **INTERFERENCE** — exactly one passes: report which skill was trained away; first
  empirical evidence about multi-task capacity sharing on this axis (informative either way).
- **FAIL** — neither: template-to-generalization transfer failed; the probe dies honestly.

Per-category (1-4) breakdown and E-type breakdown reported. Seed 20260920 throughout.

## Interpretation limits (pre-stated)
PASS-EVENT with near-template training data proves learnability of the *mapping*, not of
event semantics in the wild; if both pass, the open question becomes whether the single model
generalizes beyond the E generator's phrasings (a successor surface), which no result here can settle.
