# AF-PRE-007 RESULTS — RLHF (surrogate-human) vs RLCD on the anchor reranker

Plan `4c865d3e` + Amendment `900ff9ef` (Arm C corrected to published RLCD,
arXiv 2307.12950, before any numbers). Labels locked `1db799f9` before training.

## Verdicts (bars: net ≥ +5 p<.05 vs R on sample2, E 17/17)

| arm | sample2 ungated | net vs R | p | E gaps | verdict |
|---|---|---|---|---|---|
| R (AF-PRE-005 ckpt2) | 56/120 | — | — | 17/17 | reference |
| H — RLHF (40 human-style prefs → PM → REINFORCE) | 58/120 | +2 (5/3) | .727 | 17/17 | **SIGNAL** |
| C — RLCD (contrast pairs → PM → REINFORCE) | 58/120 | +2 (6/4) | .754 | 17/17 | **SIGNAL** |

Neither arm reaches PASS. No detectable ordering between RLHF and RLCD at this
resolution — the two are indistinguishable (+2 each, identical Wilson band).

## Why the preference signal did not move anything (descriptive)

- **Arm H feedback quality:** the surrogate annotator (the assistant, judging
  unseen-gold pairs picked for maximum model uncertainty) agreed with gold on
  only **21/40 (52.5%)** of pairs. The reward model was trained on near-coin-flip
  labels on exactly the pairs where the model was already most likely wrong.
- **Arm C contrast yield:** p₊/p₋ (surface-matched best/least framing) selected
  **different turns on only 32/772 items (4.1%)**, and when they did differ the
  auto-labeled chosen turn was gold only **9/32 (28%)**. In this task the
  contrast-prompt trick barely produces signal, and what it produces is
  majority-wrong — RLCD's premise (differentiated outputs ⇒ clean labels) does
  not hold for a 6-layer cross-encoder ranking conversation turns.
- Both PMs fit their tiny/label-noisy pairs to near-zero loss, and 200 KL-anchored
  REINFORCE steps against such rewards move the policy only trivially — the +2/+2
  observed, with E anchors fully preserved (KL anchor working as designed).

## Reading

This is a **clean negative for RL-style post-training at this scale with
this feedback budget**, not a tie between methods: the comparison was run
with identical machinery and it showed that *both preference sources are too
weak here to lift anything*. AF-PRE-005's supervised pipeline-matched training
(56, net +26 over BM25) remains the program's best reranker; its training
signal is 772 gold labels — two orders of magnitude more usable than what
either preference channel supplied (40 noisy / 32 noisy).

If preference methods are revisited: the bar to clear first is feedback data —
not algorithm. A successor only makes sense with either (a) gold-quality
preference pairs at ~10³+ (i.e., supervision, defeating the purpose), or
(b) a contrast source that separates on this task — the AH-salience signal
from AF-PRE-006 (59% context-only anchor ID) is the only known candidate.

## Artifacts
`review.md` (40 pairs, gold hidden), `rl_labels.json` (locked pre-training),
`pairs_locked.json`, `rlcd_pairs.json`, `human_pairs.json` (gold agreement
computed after lock), `ckptH`, `ckptC`, `results.json`. Seed 20260920.
