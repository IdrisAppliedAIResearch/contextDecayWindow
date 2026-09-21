# AMENDMENT 001 to AF-PRE_007_PLAN.md — Arm C corrected to the published RLCD procedure

**Trigger/evidence:** web access became available after plan registration
(4c865d3e). The registered Arm C ("decoy-query argmax pairs + DPO") was written from
memory and is **not** the published method. RLCD (Yang et al., arXiv 2307.12950,
ICLR 2024) is: (1) for each prompt build surface-matched positive/negative prompts
p₊/p₋ differing only in attribute words; (2) get the base model's outputs under p₊ and
p₋; auto-label the p₊-output preferred — no post-hoc scoring, no human labels;
(3) train a preference model on those pairs; (4) run RL (PPO with KL regularization)
from that preference model. The paper explicitly lists DPO as untested future work,
so the registered DPO step is out of family. No numbers existed when this amendment
was written; bars unchanged.

**Change — Arm C is re-specified (everything else in the plan stands):**
1. **Contrast prompts** (surface-matched per the paper's criterion 2, differing only
   in one adjective):
   - p₊ = question + "\nWhich turn best answers the question above?"
   - p₋ = question + "\nWhich turn least answers the question above?"
2. **Pair generation** by the reference model R (our analogue of the base model's
   output): chosen = argmax over candidate turns of score_R(p₊), rejected = argmax of
   score_R(p₋); skip the item if identical. No gold, no judgments used.
3. **Preference model:** initialized from R, pairwise logistic fine-tune on the
   contrast pairs — same recipe as Arm H's reward model (3 epochs, lr 1e-5).
4. **Policy optimization:** identical to Arm H's frozen REINFORCE step (top-5
   sampling, advantage from the arm's own preference model, β=0.1 KL to R, 200
   steps). The two arms now differ **only** in preference-data source — which is the
   RLCD-vs-RLHF comparison as published.

**Exclusions:** bars (PASS +5 net p<.05, E 17/17), Arm H, eval surfaces, seeds, and
all honesty clauses are unchanged. Arm H itself matches standard RLHF (human
preferences → RM → KL-anchored policy RL; REINFORCE-not-PPO deviation was already
registered).
