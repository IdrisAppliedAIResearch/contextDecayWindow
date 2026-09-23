# BERT-SWAP Stage 0 Report — Options 1 and 2

**Disposition: G1 DEAD, G3 NO_SIGNAL. Option 2 (Stage 0b): G1b DEAD, G3b
NO_SIGNAL — both consolidation extremes closed for the MLM objective.**
See Stage 0b section at the end. The hot-swap continual fine-tune stream is
closed *at this objective and these budgets*. What is and is not closed is
written down per §9.1.

- Spec: `STAGE0_SPEC.md` (commit `f001e22d`), Amendment 001 (Q3 materialization)
  before any measurement. Harness `bert_swap_stream.py`, analysis
  `analyze_stage0.py`. Seed 5005, CPU, deterministic (smoke double-run
  metrics byte-identical, SHA `3523b27f011a…`).
- Stream: Study 005 user turns 1–121, script SHA `D8BA73FD…0752F01`.
  Mechanism code never read `q_facts_key.md`; probe scoring consumed only
  `probes.json` (derived from key SHA `C1B5C9C4…4731ECA7`).
- Runs: `small_train`, `small_notrain`, `base_train`, `base_notrain`
  (prajjwal1/bert-small ~28.9M; bert-base-uncased ~110M; warm-continued MLM,
  1 epoch/turn, lr 2e-5, no replay).

## Q1 — Memorization floor: DEAD

Mean cloze accuracy over 13 planted-fact probes (never-planted controls
verified at 0.000 in all runs, so the instrument reports chance correctly):

| model | pre-plant | post-plant (train) | post-plant (frozen) | net vs frozen | margin Δ vs frozen |
|---|---|---|---|---|---|
| bert-small | 0.308 | 0.308 | 0.308 | 0 | −0.002 |
| bert-base | 0.308 | 0.308 | 0.231 | +1 | −0.112 |

- Training on the source turn produced **no learnable gain**: net 0 (small),
  +1 (base, on `art_patron_role`, a probe answerable from pretraining world
  knowledge). Margins did not move; at base they moved *worse*.
- Forgetting curve is vacuous because there was nothing to forget: t+10/t+50
  readings equal pre-plant readings. Warm-continued stream training at ≤2
  steps/turn neither binds nor appears to unbind.
- Instrument honesty: the pre-plant floor is 0.308 because 5–6 of 13 probes
  reuse real-world knowledge (dual mandate, Julius II, Taylor Rule, mantle
  photophores) or favorable distractors (`847` at small). The **purely novel**
  bindings (Dr. Anara Bekova, 92.4 t/axle, S460ML at small, the fictional
  2.3% threshold, 900 m) read 0 correct at both sizes after exposure and
  stayed 0 under up to 50 further turns. Contamination raised all conditions
  equally; paired nets are unaffected.
- G1 per registered bars: not WORKS (imm < 0.50), not SIGNAL (no margin gain).
  **DEAD.**

## Q2 — Geometry drift: characterized, small but real

- Per-swap identity cosine mean on a 100-sentence set:
  small 0.99988–0.99998, base 0.99986–0.99997 across 121 swaps. Drift exists
  (instrument check passes: exactly 1.000 in no-train, <1.000 in train) but is
  small enough that retrieval ranks were near-unaffected (Q3 nets).
- Re-embedding the whole 121-text store costs **0.07–0.25 s** (CPU, bert-base):
  full re-embed per swap is cheap at this scale.
- **The proposed swap acceptance gate is an instrument failure.** Slice MLM
  loss *improved* over the stream (small 3.33→2.93; base 2.76→2.42); max
  per-turn ratio 1.0003/1.0007 vs the 1.2 bar: **0/121 fires, and no plausible
  firing point exists.** MLM loss on held-out text is a surrogate that cannot
  see novel-fact forgetting. Any future acceptance gate must probe planted
  facts / retrieval utility, not fluency. Per §9.2, this is the instrument,
  and the instrument named above would work.

## Q3 — Adapted-scorer relevance: NO_SIGNAL

Paired (checkpoint × query) complete-evidence hit@3, 26 items, train vs same
frozen encoder:

- bert-small: net 0/0. bert-base: net 3/4 (sign p=1.0), per-checkpoint
  {10: 0, 61: 0, 65: 0, 102: −1, 121: 0}.
- Below SIGNAL (net ≥ +1 with a defensible direction): at small the net is 0;
  at base the net is −1 and dominated by noise.

## What this closes, and what it does not (§9.1)

Closed, for this design and corpus:
**"Fine-tune a (tiny) BERT on every turn (≤2 MLM steps, warm continuation, no
replay), and the model itself becomes the retrieval system" — no evidence at
28.9M or 110M params.** Neither the memorization channel nor the relevance
channel showed gain; there is no forgetting cliff to manage because there was
no learning.

Not closed:
1. **Higher consolidation budgets** (multi-epoch, replay, nightly batch =
   Option 2 territory). Stage 0 deliberately spent 1–2 steps/turn — the
   hypothesis's own definition of "train every turn" — but did not test the
   opposite extreme.
2. **Training objective.** Only MLM-on-own-text was tested. Alias/contrastive
   objectives are different mechanisms; Stage 0's null does not speak to them.
3. **Adapter-on-frozen-base swaps** (geometry-preserving variant) — not run.
4. **Probes:** clean novel-fact binding is 4 probes; a successor should plant
   wholly novel facts (no world-knowledge contamination) if Q1 is revisited.

Per the registered kill logic (G1 dead + G3 NO_SIGNAL), the arc closes as a
characterized negative **in the per-turn stream regime**. The remaining honest
successor is the retrain-with-replay consolidation design (Option 2), which
Stage 0 does not address.

## Cost note (for any successor)

Per-turn wall (CPU, 16 threads): small 1.2 s, base 3.2 s, including training;
store re-embed ≤0.25 s per swap for a 121-text store. Real-time "train between
turns" is operationally trivial at these sizes; the finding is that the
*learning*, not the *compute*, is absent.

## Artifacts

`runs/{small,base}_{train,notrain}.{metrics.jsonl,q3.jsonl,timing.jsonl,meta.json,log}`,
smoke runs incl. determinism duplicate. Final weights (`*.final.pt`, 115 MB)
are deliberately not committed (GitHub 100 MB limit); they are rebuildable from
seed 5005 and the committed harness.

---

# Stage 0b — Option 2 (shadow-as-retrain on replay buffer)

Spec: `STAGE0B_SPEC.md`. Harness: same runner, `--mode retrain`
(re-init from base weights at every 10th turn, then MLM 2 epochs over user
turns 1..u past-only, lr 2e-5, fresh optimizer; final retrain at 121;
13 swaps). Controls: Stage 0 `small_notrain`/`base_notrain` reused unmodified.
Determinism re-verified (retrain smoke double-run byte-identical). Runs:
`opt2_small`, `opt2_base`.

**Disposition: G1b DEAD, G3b NO_SIGNAL — both at the registered bars.**

## G1b — Memorization under consolidation

| model | imm (post-swap) | imm frozen | pre | net | margin Δ | novel-fact controls |
|---|---|---|---|---|---|---|
| bert-small | 0.308 | 0.308 | 0.308 | 0 | +0.003 | 0.000 |
| bert-base | 0.308 | 0.231 | 0.308 | +1 | +0.075 | 0.000 |

- The base +1 is `monetary_threshold` — a **wholly novel** fact (the fictional
  2.3%), so not world-knowledge contamination. It is the single binding the
  entire program has produced: first correct at swap 70, then flickers
  off/on across swaps (wrong at 80 and 110). Its margin is ~+0.0002 vs the
  frozen −0.002 — a flip at the argmax boundary, not a stable trace.
- The registered SIGNAL bar required margin Δ ≥ +0.10; measured +0.075 at
  base, +0.003 at small. The SIGNAL tier does not fire and §9.4 forbids
  reading it as if it did. **DEAD at the registered bars, with the near-miss
  and its flicker named as the one datum a budget/objective successor would
  start from.** ~24 steps/fact (2 epochs × 12 appearances-worth of buffer
  passes) at 110M produced one marginal, unstable binding out of 13.

## Q2b — Geometry and cost under retrain

- Per-swap identity cos: small 0.975–0.986, base 0.961–0.979 — an order of
  magnitude more movement than the stream (0.9999). The store must be
  re-embedded every swap (still ≤0.25 s for 121 texts).
- **Retrain cost is the headline engineering result:** per-swap wall grows
  linearly with buffer — small 1.9 s → 20.2 s, base 6.4 s → 64.0 s (16 CPU
  threads). Total for one 121-turn conversation: ~3 min (small), ~7.4 min
  (base). Over a conversation the cost is quadratic in length; 10k turns at
  this cadence is ~8.5 CPU-hours (base, 2 epochs). "Train on everything,
  often" is affordable for minutes of conversation, not as a per-turn loop
  at 121 turns — before asking whether it learns anything.

## Plant-margin gate (the instrument §9.2 named)

Probing planted-fact margins (−0.05 common-set rule) at each swap:
**0/13 fires at small; 3/13 at base (swaps 40, 100, 120)** — regressions the
fluency gate never saw (0/121 in Stage 0). Confirms the Stage 0 instrument
finding: fact-probe gates see forgetting that MLM loss is blind to.

## Q3b — Adapted-scorer relevance

26 paired items, retrain vs same frozen encoder: small net 0/0; base net 4/4
(sign p=1.0), per-checkpoint all 0. **NO_SIGNAL.** The retrained encoder moves
geometry (Q2b) but moves rankings in no useful direction.

## What Stage 0b closes (§9.1)

Closed, for MLM on turn text: **neither extreme of consolidation budget makes
a ≤110M BERT a fact store** — not 1–2 warm steps/turn (Stage 0), nor ~24
steps/fact fresh-from-base retrain with full replay (Stage 0b). The MLM
objective itself is the binding constraint, plus a documented scaling wall.
Also closed for free: "swap-adapted encoders help retrieval relevance" at
both budgets (nets 0 and ±wash).

Not closed, honestly: (1) an objective that trains the fact *as a fact*
(alias/contrastive binding of cue→answer), (2) adapter-on-frozen-base swaps,
(3) budgets ≥2 orders of magnitude larger — the `monetary_threshold` flicker
is consistent with MLM learning slow, weak, and near-threshold, but nothing
here demonstrates a crossing point. Per the registered kill logic in
`STAGE0B_SPEC.md`, the bert-swap arc **closes here as a characterized
negative**; reopening it requires a different objective, which is a new
probe, not a continuation.
