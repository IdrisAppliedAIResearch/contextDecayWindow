# BERT-SWAP Stage 0 Report — Option 1 (shadow-as-continuation)

**Disposition: G1 DEAD, G3 NO_SIGNAL, G2 characterized.** The hot-swap
continual fine-tune stream is closed *at this training regime*. What is and is
not closed is written down per §9.1.

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
