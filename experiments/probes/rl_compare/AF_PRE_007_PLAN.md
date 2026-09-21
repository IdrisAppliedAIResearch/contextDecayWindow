# AF-PRE-007 (registered before any training): RLHF (surrogate-human feedback) vs RLCD (contrastive pair mining) for the anchor reranker

**No web access in this environment.** The two methods are defined here from the
implementer's knowledge, frozen before any number exists. RLHF follows the standard
two-phase recipe (reward model on preference labels + KL-anchored policy optimization).
RLCD follows the 2025-style formulation: preference pairs auto-constructed by contrasting
document/query styles, **no human feedback**, DPO-style margin optimization. If either
published formulation differs from this frozen adaptation, that is a limitation of this
probe, stated up front.

## Shared substrate
Reference arm `R` = AF-PRE-005 checkpoint (`ckpt2`), re-evaluated per-item in this probe.
All new arms initialize from `R`. Eval surfaces unchanged: sample2-120 (primary, paired
McNemar vs R), E-17 (must stay 17/17; any arm dropping below is disqualified from PASS
regardless of answer-side gains — no trading the anchor skill for ranking).

## Arm H — RLHF with surrogate-human feedback
1. **Uncertainty pairs:** 40 (candidate_a, candidate_b) pairs from training items where R's
   top-2 gap is smallest (max model uncertainty), gold hidden, order randomized.
2. **Feedback:** the implementer (AI assistant acting as human annotator, per the user's
   instruction) judges each pair: which turn better answers the question. Labels recorded
   before training, with human-style error included (the point — feedback ≠ gold).
   Gold-flag agreement is computed post hoc as a descriptive label-quality read.
3. **Reward model:** R's architecture initialized from R, pairwise logistic fine-tune on
   the 40 judgments (3 epochs, lr 1e-5).
4. **Policy optimization:** REINFORCE (KL-anchored): for training queries, sample candidate
   c ~ policy top-5 softmax; advantage = RM(c) − mean(RM); loss = −Σ logπ(c)·adv + β·KL(π‖π_R),
   β=0.1; 200 steps over training items. (REINFORCE rather than PPO; frozen choice.)

## Arm C — RLCD (contrastive pair mining, zero feedback)
1. **Contrast pairs:** per training query, auto-generate decoy query (named entities
   replaced by other conversation entities; past↔present tense cues swapped).
   chosen = argmax_R(real query), rejected = argmax_R(decoy query) — if identical, skip.
   This is the RLCD move: pairs from style contrast, no labels, no judgments.
2. **Optimization:** DPO margin loss on scores treated as logits:
   −log σ(β[(s_H−s_ref)(chosen) − (s_H−s_ref)(rejected)]), β=0.1, ref = R,
   200 steps. (DPO rather than PPO-from-generated-prefs; frozen choice.)

## Bars (binding, per arm)
- **PASS:** net vs R on sample2 ≥ +5, McNemar p < .05, E 17/17.
- **SIGNAL:** net > 0, E 17/17.  **DEAD:** otherwise.
- Arm-vs-arm delta reported; no reinterpretation of 005/006 verdicts.

## Contamination & honesty clauses
- The 40 judgments never see gold; gold agreement is computed after labels are locked.
- sample2/E gaps untouched by all training.
- 40 preference pairs is small by design (surrogate-annotator budget); an RM trained on it
  is expected noisy — that is part of the RLHF-vs-RLCD comparison, not a bug to hide.
- No bar movement, final checkpoints only, seed 20260920, serial GPU, no LLM readers in the
  scoring path (the annotator role is feedback, not inference).
