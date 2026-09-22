# AF-READ-001 — Results (plan `f75f590d`, pre-registered before any call)

**Verdict: DEAD on both bars. The ±2-turn anchor window loses decisively to the
deployed full-memory read, even when the anchor is correct.** The guardrail
alternative reading (triggered at B−A < −8) is the right summary: this is a
*window* failure, not an anchor failure — and it closes the anchor-as-replacement
program on top of the retrieval-level arc (AF-FT-001/002/003).

## Headline (primary H120, 3-pass blind judge, committed before gold opened)

| arm | correct /120 | vs A net (p) | median prompt | mean tokens_in |
|---|---|---|---|---|
| A_DEPLOYED (frozen timeline) | **85** | — | 28,739 ch | 10,715 |
| B_ANCHOR (V2 argmax ±2 turns) | 51 | −34 (~0) | 825 ch | 332 |
| C_GATE (τ=0.2, 80/120 swapped to B) | 68 | **−17, p=8e-5** | — | 3,597 |

- Bars: WORKS ≥ +8 & p<.05 → no. SIGNAL ≥ +4 → no. Result is significantly *negative*.
- Descriptive D120 (contaminated sample2): A 76, B 43, C 51 — same direction.
- τ-sweep monotone against anchoring: net vs A = −6 (τ=.05), −11 (.1), −17 (.2), −30 (.4), −32 (.6). Even the most conservative gate loses.
- PF9 clean: 0 discordances on fallback items — every loss is carried by an anchor swap; the gate machinery itself worked.
- Calibration: arithmetic + all 15 judge fixtures passed twice; template-suffix asserts held on 720 calls; 0 failed reader/judge calls.

## Guardrail diagnostic (why it dies — the interesting part)

| slice | n | A | B | C |
|---|---|---|---|---|
| anchor lands IN gold evidence | 60 | 49 | 41 | 44 |
| anchor lands OFF gold evidence | 60 | 36 | 10 | 24 |
| gated-to-anchor subset | 80 | 59 | 42 | 42 |
| multi-evidence (≥2 gold turns) | 39 | 21 | **4** | 13 |

1. **Even when the anchor is right, the window is not enough** (41 vs 49 on
   in-evidence items). The ±2-turn window destroys answer-bearing context the
   reader silently depends on — coreference, dates, speaker state from earlier
   turns. Retrieval top-1 ≠ reading sufficiency.
2. **Multi-evidence questions are the kill site**: A 21/39 vs B 4/39. A single
   window can't span cross-session evidence; the deployed timeline can (it has
   everything). This is exactly what the timeline representation buys.
3. The V2 anchor's 66% any-correct retrieval ceiling compounds into reader loss:
   off-evidence swaps collapse to 10/60.
4. Cost math: C saves 66% input tokens but pays 17 items of accuracy. At this
   reader, accuracy/token frontier is dominated by A. A context-compression
   program (keep the timeline, shrink it losslessly-ish) is the only survivor
   of this idea-space, and it's a different experiment.

## What this closes

- The full arc, all pre-registered, all negative at the endpoint: a BERT-class
  cross-encoder with native abstention *can* be trained to competitive
  cross-lexical retrieval (V2: sample2 exact 59.4 vs champion 56; AUROC 0.936
  abstention; E17 17/17) — and it still **does not transfer to the reader**,
  because reading needs the neighborhood, not the turn.
- Honest scope: negative for "anchor window replaces timeline memory" on LoCoMo
  with a 27B reader at 32-40k ctx. The deployed timeline at 10.7k mean tokens
  wins; a hybrid (anchor as *reranker/order* of the timeline, keeping content)
  was never registered and would be a new pre-registration.

## Artifacts (all committed; phase boundaries = commit boundaries)

`pilot.json` → `reader/*` (720 raw calls) → `reader_complete.json` (before gold)
→ `blind_surface.json` (gold opens) → `judges/*` → `judge_complete.json` →
`results.json` (this + guardrail diagnostics). Commits: `ad168acd`, `e95d9887`,
`6a5e1e75`, `c6562cb1`, `319009a3`, re-score with diagnostics follows.
