# BERT-SWAP Stage 0 — Continual Fine-Tune Stream (Option 1: shadow-as-continuation)

**Type:** exploratory probe (`experiments/probes/`), offline, zero reader/LLM calls.
**Branch:** `feat/bert-swap`. **Date:** 2026-09-23. **Seed:** 5005.

## Hypothesis under test

The next-arc hypothesis (hot-swap two BERTs; fine-tune the shadow on every
conversation turn; the tiny adapted model becomes the retrieval system).
Stage 0 tests three falsifiable questions, in order of binding force:

- **Q1 Memorization floor.** Can a BERT-class encoder, fine-tuned turn by turn
  with MLM on the stream text, bind planted facts into weights and express them
  through a cloze readout? At what offset does warm-continued stream training
  forget them?
- **Q2 Geometry drift.** How far do embeddings move per swap (identity cosine),
  what does that do to retrieval scores on a frozen candidate store, and what
  does full re-embedding cost?
- **Q3 Relevance gain.** After adapting on *k* turns, does the adapted encoder's
  cosine rank planted gold turns better than the same frozen encoder — the
  "model as fast-adapting scorer, store stays in bytes" reading.

Option 1 is deliberately naive: shadow warm-continues from the previous shadow;
training signal is MLM on the current turn's user text only, one epoch, no
replay. The forgetting curve this produces is the measurement, not a bug to
avoid. The swap acceptance gate is measured retrospectively (logged per turn,
never fed back) so the mechanism stays feedback-free in Stage 0.

## Corpus and boundary

- Stream: user turn texts 1..121 of the locked Study 005 script.
  `experiments/study_005/script.json`
  SHA-256 `D8BA73FD02BFD41BEC156904FB6A3328BBED3D0DA8BFF05E4667D2E450752F01`.
  Assistant half is excluded (plants live in user turns; deviation recorded).
- Measurement-only: `experiments/study_005/q_facts_key.md`
  SHA-256 `C1B5C9C484C1BD82A13D7B1599BFEBC78A3200FDBD684A35DBA4D3BB4731ECA7`
  → `probes.json` (cloze probes + control probes + query→gold map).
  Mechanism code reads neither the key nor `probes.json`; the runner consumes
  `probes.json` only in scoring functions. Verified by grep at closeout (§
  Leakage).

## Models (capacity ladder)

| role | checkpoint | params |
|---|---|---|
| tiny bet | `prajjwal1/bert-small` (4L×512, MLM head) | ~28.9M |
| capacity ceiling | `bert-base-uncased` | ~110M |

If even the ceiling cannot memorize, the "tiny is enough" version is dead; if
the ceiling memorizes and tiny does not, the capacity story is characterized.

## Training (mechanism)

Per turn t: 1 epoch MLM, all-segment batch, AdamW lr 2e-5, deterministic
15% masking seeded `random.Random(1000+t)`, max_seq 128, CPU,
`torch.use_deterministic_algorithms(True)`, threads fixed 16,
`torch.manual_seed(5005)`. Runs: `{model} × {train, no-train}`.
No-train = the frozen control and the probe instrument control (Q1 accuracy
must sit at chance; if it rises, the probe leaks).

## Measurements

**Q1 Cloze probes** — 13 planted-fact probes (one per key row), 4 choices each,
scored by MLM pseudo-likelihood: fill the cloze with each choice, mean logP of
answer-span tokens under the filled sequence. Metrics: argmax accuracy, margin
(gold − best distractor, nats). Offsets per fact: immediately after training on
its source turn, +10, +50 (where in range). Pre-plant readings of the same
probes are the chance control. Plus 3 never-planted control probes (expected:
flat ≈ 25% everywhere; a rise invalidates the instrument).

**Q2 Drift** — after every turn: identity cosine (same sentence, model before
vs after swap) over a fixed 100-sentence set, mean and p10; per-swap wall-clock
to re-embed the store. Mean cosine ≡ 1.0 in train runs ⇒ training never touched
the encoder ⇒ instrument failure, reported as such.

**Q3 Relevance** — checkpoints c ∈ {10, 61, 65, 102, 121} (after each domain's
plants); queries = turns 112, 113, 115, 116, 117, 118, 119; gold turns from the
key (112→{3,4}, 113→{3,4}, 115→{55,60}, 116→{56}, 117→{55,60}, 118→{100,102},
119→{101}). Mean-pooled, L2-normalized last hidden state. Complete-evidence
hit@3 / hit@5 over candidates = user turns ≤ c; paired train-vs-no-train per
(checkpoint × query) item.

**Gate audit (retrospective, no feedback)** — fixed 24-sentence regression
slice (even turns 2..48), MLM loss every turn at fixed mask seed; logged
against a 20% degradation bar. Reports what an acceptance gate would have done.

## Disposition bars (registered before the run; §9.3 two tiers)

- **G1 (Q1, model-as-store).** WORKS: adapted post-plant accuracy ≥ 50% (mean
  of 13 probes at immediate offset) AND pre-plant ≤ 30% AND ≥ +2 net probes vs
  frozen same-model at the same offset. SIGNAL: accuracy 25–50% at immediate
  offset with mean margin improvement ≥ 0.10 nats over frozen. Below: the
  literal hypothesis dies at this capacity; report where.
- **G2 (Q2, characterization, no kill).** Report drift trajectory, gold-rank
  instability, re-embed cost. Instrument check: cosine ≡ 1 fails the run.
- **G3 (Q3, adapted scorer).** WORKS: paired net hit@3 wins ≥ +3 over 35 items
  with no checkpoint at ≤ −2 losses. SIGNAL: net ≥ +1. Else NO_SIGNAL.
- **Kill logic:** G1 dies and G3 NO_SIGNAL ⇒ arc closes as characterized
  negative. G1 dies but G3 SIGNAL ⇒ reframe the arc to adapted-scorer-over-
  immutable-store. G1 works at base but not tiny ⇒ capacity floor established.

## Preflight (PF1–PF10)

- **PF1** Inputs exist, hashed: script.json, q_facts_key.md (SHAs above,
  measured this session); models cached (`prajjwal1/bert-small` @
  `0ec5f86`, `bert-base-uncased` @ `86b5e09`).
- **PF2** Mechanism identity: MLM training verified to change weights
  (loss finite, cosine < 1 vs prior) in smoke; cloze scorer verified on a
  hand-planted fact (smoke check).
- **PF3** Gate ordering: dispositions written here, before any run artifact
  exists; analysis script only reads artifacts.
- **PF4** Bars reachable both directions: chance controls exist (pre-plant,
  never-planted, no-train); a positive control exists (post-plant immediate);
  no bar assumes a level the instrument cannot produce — smoke run bounds it.
- **PF5** Comparison keys: paired by (probe id, turn offset, checkpoint),
  content-derived, no timestamps.
- **PF6** Reproduction anchor: smoke doubled-run → metrics.jsonl byte-identical
  (SHA compared).
- **PF7** Absorbing state: the stream is feedback-free (gate retro-audited);
  no-train control bounds drift.
- **PF8** Ablation adequacy: no-train vs train isolates training as the sole
  difference; 121-turn stream cannot show >t+50 forgetting (reported as
  range-limited).
- **PF9** Surrogate audit: accuracy could inflate via distractor bias → 3
  never-planted controls measure exactly that; margin reported alongside
  accuracy; pseudo-likelihood scores whole answer spans, not first token.
- **PF10** Availability ≠ verdict: this is an offline probe; no reader claim
  is possible from it, and none is made.

## Runtime

CPU only (GPU held by other processes). Estimated: bert-small ≈ 10–15 min,
bert-base ≈ 25–45 min, no-train runs cheaper. Four runs total.

## Artifacts

`probes.json`, `runs/{run_id}.metrics.jsonl`, `.q3.jsonl`, `.meta.json`,
final weights for train runs, `artifacts/` logs, then `REPORT.md`.
