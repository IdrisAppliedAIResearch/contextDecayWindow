# HH-001 predictions, recorded before the result

**Status:** `SEALED BEFORE OUTCOMES` — written while the Mem0 ingest was still
running and before any arm had been scored.
**Author:** the implementing agent, asked for an independent view.
**Standing:** none. These are opinions, not registered bars. They cannot
promote or demote any result, and no disposition in
`HH_001_DEVELOPMENT_PLAN.md` §6 reads them. Their only function is to be
checkable afterwards, so that a post-hoc story cannot be told as a prediction.

## Ranked, falsifiable

1. **A1 `FULL_CONTEXT` scores highest.** LoCoMo's longest conversation is
   90,034 characters, roughly 22k tokens, against a 200k window. The corpus
   fits. If this holds, the honest reading is that LoCoMo poses a cost problem
   and not a capacity one, and no result here demonstrates a memory layer is
   *needed*.
2. **A2 beats A3 on judged accuracy.** Two reasons, and only the first is
   merit: verbatim storage fits a corpus whose questions are mostly single-hop
   lookups over dialogue, and at matched budget A2 delivers roughly four to
   eight times more text.
3. **A2 and A4 land close.** The one I would bet on least confidently and
   watch most closely. If naive 1,000-character chunking matches pair ranking,
   NF-004's apparatus is not earning its keep against a trivial baseline on
   this corpus.
4. **Mem0's store loses some answers outright.** `store-probe` finds gold
   answers absent from the store, not merely unretrieved. Bounded above by the
   containment test, which counts a preserved paraphrase as absent.
5. **A2 wins the long-horizon stratum by more than it wins overall**, because
   verbatim retrieval does not care how old a turn is.

## What would change my mind

- **A3 > A2 on accuracy.** Then 16,000 characters of mostly-irrelevant text is
  worse than 2,000 curated ones, and distraction beats availability. This
  programme has already measured that twice on itself: Study 007 delivered all
  four domains at the breadth probe and scored zero there, and LV-001
  preserved 16/16 targeted items offline and then fired its live kill bar.
- **A4 ≈ A2.** Then the component's claim narrows to being as good as
  chunk-and-embed and cheaper than Mem0.
- **A0 above zero at n=300.** The 0/50 contamination probe was small.

## The asymmetry neither side's paper names

The two architectures amortize in opposite directions. This component spends
nothing at write and four to eight times more prompt tokens at read; Mem0
spends a generative call per stored pair and reads cheaply afterwards. Which
is cheaper is decided by the **read/write ratio**, a parameter neither
`HH_001_DEVELOPMENT_PLAN.md` nor arXiv:2504.19413 states. A report that gives
an ingest-cost figure without naming that ratio has answered half the
question. The run measures both halves, so the report can state the crossover
rather than pick the flattering side of it.
