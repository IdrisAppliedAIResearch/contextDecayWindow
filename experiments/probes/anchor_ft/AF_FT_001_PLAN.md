# AF-FT-001 (registered 2026-10-02, design committed before implementation): retrain the anchor cross-encoder — data fixes, multi-positive loss, native abstention

**User direction (verbatim, 2026-09-series):** the BERT should activate on the questions the deployed
resolver abstains on; success is measured on LoCoMo questions, with native confidence supporting an
abstain threshold. Reframing agreed in review: activation rate alone is gameable and unsatisfiable on
no-gold items; the target is **recall on anchorable questions + scored abstention on the rest**,
decided by reader-accuracy value later (a separate, call-spending study).

Champion: ckpt2 (AF-PRE-005 contract): MiniLM-L6-v2 (repo `cross-encoder/ms-marco-MiniLM-L-6-v2`,
revision `233902d2...`), full FT 2e-5/3ep/wd.01, single-positive pool softmax.
Recorded: **56/120 sample2 ungated (exact gold), 17/17 E**. AF-PRE-006 anchor-hide auxiliary: 57/120
(net +1, SIGNAL-AH — auxiliary supervision does not move it). This study changes **data and loss**,
not the auxiliary-task axis, and adds a **null class with calibration**.

## Part 1 findings (executed 2026-10-02, `pf1_data_probe.py`, stdout recorded in this dir)

1. LoCoMo cats: {1:282, 2:321, 3:96, 4:841, 5:446}; eligible cats1-4 with in-conv evidence: 1,531.
2. Cat-5 items all carry `evidence` pointers and `adversarial_answer`, and 444/446 have no `answer`
   field: adversarial = "not mentioned in conversation". They are **not** clean negative anchors —
   the evidence turns may discuss related entities. Cat-5 therefore **never trains**; descriptive slice.
3. Evidence-set sizes over cats1-4: 409/1531 items (27%) have >1 evidence turn. On frozen sample2:
   **30/120 items have >1 gold** — exact-gold metric under-credits multi-evidence hits; any-gold
   credit is reported alongside (champion 56/120 is exact-gold; any-gold champion is recomputed here).
4. The frozen 005 builder **discarded 519/1,291 eligible training items** because gold was outside the
   BM25 pool; it kept 772. Gold-in-pool insertion (add gold turns to the candidate set instead of
   dropping the item) restores 67% more training data under the identical task contract.
5. Training rows with >1 gold in pool: 61/772 — the multi-positive signal exists but is thin in LoCoMo.
6. Champion data mix is E-heavy: 1,287 E rows (429 × 3) vs 772 LoCoMo rows. E rows are kept (the
   17/17 no-trade clause depends on that supervision); E rows are single-gold by construction.

## Design

**Task contract (unchanged semantics):** given (question, conversation), select the anchor turn =
earliest evidence turn; any evidence turn counts as a hit under any-gold scoring (reported metric;
exact-gold stays the headline comparability metric vs 56/120).

**Data (build2):**
- Pool: `pool_ids()` frozen builder (BM25 top-20 ∪ event-entity turns) **∪ gold evidence turns**
  (insertion replaces 005's row-skipping). Negatives: BM25 top-6 non-gold (frozen choice; no new
  mining — AF-PRE-006 + the arc's own hard-negative history).
- Anchor rows: 1,291 LoCoMo training items (cats1-4 eligible minus sample1 minus sample2, frozen
  disjointness asserts from 005 preserved); positives = **all** evidence turns present in pool.
- E rows: unchanged from `pairs2.json` (1,287).
- Null rows (V2 only): synthetic — training-item question + pool built from a **different
  conversation** (rng 20261002; topical overlap not controlled, BM25-scored pools so some candidates
  lexically match), null rate ≈25% of rows. Cat-5 excluded from all training (finding 2).
- Held-out-120 (V2 only): 120 anchor training items (rng 20261003) removed from V2 training →
  calibration + null-eval anchor side. **V1-h120 control** trains V1 on the same 120-removed set so
  V2 vs V1 comparison is not confounded by the removed data.

**Model:** MiniLM-L6-v2 same repo/revision. Full FT (champion regime) — LoRA deferred (one factor at
a time; the data/loss levers come first, LoRA is a follow-up if the axis proves real).

**Loss:**
- R0, V1: pool softmax-CE. R0 positives: earliest gold only (champion reproduction).
  V1 positives: uniform mass over all in-pool evidence turns (multi-positive listwise CE).
- V2: pool softmax over [candidates…, **learned scalar null logit τ**]; anchor rows target the golds;
  null rows target τ. Reject margin m = 0.5 added to τ on anchor rows (El-Yaniv-style reject-option;
  guards the degenerate always-null). Label smoothing 0.05 on anchor rows only.

**Hyperparameters (all configs):** AdamW 2e-5, wd 0.01, batch 16 pools (8 if VRAM-bound), warmup 10%,
3 epochs, max_len 256, final checkpoint. Identical to champion — the registered claim is about data,
loss, and null class, not optimization.

**Grid:** 4 configs × 5 seeds = 20 trainings:
`R0` (champion repro), `V1` (gold-in-pool + multi-positive), `V1-h120` (control), `V2` (V1-h120 + null).
Seed list: 20261011, 20261012, 20261013, 20261014, 20261015. R0 seeds measure the seed SD this arc has
never had; **every claim below is made against R0's seed mean, not against the single 56.**

## Evaluation (frozen before results; per-item recorded)

- `sample2` (120, frozen from 005), **ungated** (score all conversation turns) — primary; gated arm
  reported secondary. Metrics per item: exact-gold hit, any-gold hit.
- **E gaps (17):** must stay 17/17 for every config claiming a bar — the AF-PRE-006 no-trade clause.
- `null-eval`: 120 synthetic held-out nulls (rng 20261003, disjoint from training nulls) + the 120
  held-out anchor items: AUROC of P(null); coverage–risk table; temperature-scaling reliability
  before/after. **Cat-5 descriptive slice:** top-50 cat-5 items (rng 20261003) with P(null) — reported,
  no bar (semantics caveat per finding 2).
- Calibration: temperature T fit on a 60/60 anchor/null calibration split drawn from Held-out-120 +
  held-out nulls; AUROC/coverage reported on the remaining items only.

**Statistics:** 5 seeds per config, mean ± SD. Paired comparisons vs R0: McNemar per seed on item
outcomes (exact test), and item-bootstrap (10k) of Δ(any-gold) with seeds averaged within item.
n=120 detects ≈±9pp as significant; smaller deltas are reported, not spun.

## Bars (binding; registered before any training run)

- **WORKS:** a V-config beats R0 seed-mean on sample2 any-gold by ≥ +8 items **and** every seed's
  McNemar p < 0.05 (vs same-seed R0) **and** exact-gold mean ≥ R0 exact mean − 2 **and** E 17/17.
- **SIGNAL:** V beats R0 any-gold mean by ≥ +4 items **and** E 17/17.
- Otherwise **DEAD** for that config; reported with per-seed SD so the axis itself is characterized
  (if R0 seed SD swallows ±8, that is a result about this 40-item-era program and closes "train
  better" claims until eval scales).
- Null/abstention: **no bar** — calibration numbers are descriptive this round; the threshold is a
  policy knob for the reader study. A degenerate always-null or never-null V2 is reported as a defect.

## Preflight

- **PF1** Inputs: `locomo10.json` (present, counted: 1,986 QA); frozen `sample2.json` (120, SHA in
  artifacts), `pairs2.json`, `blind.json`/E inputs via 005 code paths; PF-1 probe stdout committed.
- **PF2** Identity: ckpt2 repro = R0 config identical to `ft_pipeline.train()`; repro sanity: R0 mean
  within 3 items of recorded 56 on sample2 ungated — outside that band the harness is suspect and
  results are void (instrument failure, not mechanism).
- **PF3** Ordering: build2 runs (and asserts disjointness) before any training; eval script refuses
  missing configs; calibration fit executes only after all checkpoints saved.
- **PF4** Bars reachable: WORKS (+8 on 120) is inside the 56→66 label-identity gap measured by
  AF-PRE-009; kill branches (DEAD, R0-repro-fails) both demonstrably possible.
- **PF5** Keys: per-item comparisons keyed by `qid` (frozen format `conv-NN:idx`), content hashes of
  artifacts recorded; never by index or timestamp.
- **PF6** Reproduction anchor: R0 seed 20261011 must reproduce ckpt2's sample2 within the PF2 band
  by identity of qids (not counts).
- **PF7** Absorbing states: null head — run one seed, report null-fire rate on anchor rows and null
  rows; always/never-null is flagged as defect before interpretation.
- **PF8** Ablation adequacy: V1-h120 control isolates the removed-data confound; this design cannot
  separate "multi-positive" from "more rows" inside V1 (both are the same data fix); V2-vs-V1-h120
  isolates the null class. What this study cannot detect: deltas < ~±5 items at n=120 — stated.
- **PF9** Surrogate audit: any-gold credit can pass while earliest-anchor semantics are wrong —
  exact-gold reported jointly with a no-trade E clause; seed-mean gameable? No — bars require every
  seed p<.05 (WORKS). Can the gate pass while abstention is useless? Coverage–risk is reported raw;
  no bar attached. Residual: LoCoMo gold is annotation, 34-item earliest/latest audit remains open.
- **PF10** Availability is not a verdict: no reader claims, no deployment claims; the reader arm and
  deployed-library comparison are separate, call-spending studies requiring explicit authorization.

## Contamination

sample1 ∪ sample2 disjoint from all training rows — asserts extended to null rows (question side) and
Held-out-120 bookkeeping (removed rows recorded, never silently reused). Cat-5 items never train.
E gaps and their sources unchanged (005 asserts inherited).

## Runtime and exclusions

Serial GPU (RTX 5090 shared with llama-server; batch reduced if VRAM-bound — recorded, not tuned).
Fixed seeds above; no unseeded runs; no LLM reader calls; no contextual-embedding changes.
Excluded by design: LoRA/small-model sweep, 12-layer teacher distillation, question paraphrase
augmentation, session-date header inputs (PF-8: one factor group at a time; all are registered
follow-ups contingent on R0's measured seed SD).

## Follow-ups this study decides, in order

1. If R0 seed SD is large → variance is the story; eval must scale before any "better model" claim.
2. If V1 SIGNAL/WORKS → data fix is real; then LoRA + LR + early-stop sweep and distillation.
3. If V2 calibrates cleanly → reader-arm study with abstain threshold (needs call budget from user).
4. Deployed-library comparison at matched budgets (separate registration; engineering).
