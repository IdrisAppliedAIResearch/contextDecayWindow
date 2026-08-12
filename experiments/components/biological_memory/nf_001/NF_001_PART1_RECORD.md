# NF-001 Part 1 — Novelty-Floor Stopping, Characterization

**Status:** `STOP AT PART 1 — INSTRUMENT CANNOT PRICE STOPPING; CHARACTERIZED`
**Spec:** `NF_001_NOVELTY_FLOOR_STOPPING_DIAGNOSTIC.md`
**Artifact:** `artifacts/part1_record.json`
**Store:** `experiments/surveys/retrieval_bakeoff/tier6/runs/tier6_live_121_corrected_001/context_matched_stm/study.db`
**Streams:** IC-001 `B0_deployed` and `B1_k_first`, 8 probes each, 16 total
**Model calls:** 0
**Date:** August 12, 2026

Part 2 of preflight was not entered. The diagnostic stops here, as PS-002 did.

## 1. Measurement is anchored, not invented

Fact counting is substring match of the committed item strings against episode
text. On IC-001's selected payload for Q11 it returns **7 of 17** — exactly the
`fact_count` IC-001 committed. The measurement reproduces a known result before
producing a new one.

## 2. The stated killer did not fire

The spec named the failure most likely to make this look good for the wrong
reason: a novelty floor stops early wherever a stream repeats itself, and Study
010's corpus is 84% duplicates.

**Measured inside each of the 16 streams: 0 exact duplicates, 0 near-duplicates
at Jaccard ≥ 0.90.** The internal streams do not repeat. Whatever happens below
is not that artifact.

## 3. Two of four stop conditions fire

### 3.1 The rule does not adapt (§8 condition 2)

The oracle stopping depth genuinely varies: it ranges from **2 to 28** across
the 16 streams, with a p95:p05 **swing of 13.5**. There is real per-question
structure to find.

Every novelty-floor setting has a swing of **1.06 to 5.33**, and every setting
with competitive regret sits at **1.27 to 1.75**. The rule picks very nearly the
same depth every time. It is a soft fixed depth, which is exactly what the swing
statistic was carried forward from DMR-001B and DMR-001C to detect.

### 3.2 Regret cannot discriminate on this instrument (§8 condition 1)

`NEVER_STOP` scores mean regret **0.00**. So does `FIXED_30`. The streams are
32–35 candidates deep, so taking everything is free, and any rule that stops
late scores perfectly for doing nothing.

The grid's best rows are exactly that: median depth 27–33 and zero regret. They
are `NEVER_STOP` wearing a costume, and the statistic registered to catch a
degenerate arm caught it.

## 4. What the signal actually is

Restricting to settings that genuinely stop (median depth ≤ 20) and comparing
each against the fixed arm of the same or lower cost:

| unit | floor | window | depth | mean regret | matched fixed | its regret | delta |
|---|---|---|---|---|---|---|---|
| char5_gain | 0.50 | 2 | 11 | −0.81 | FIXED_10 | −1.38 | **+0.56** |
| char5_gain | 0.40 | 1 | 12 | −0.81 | FIXED_10 | −1.38 | **+0.56** |
| token_gain | 0.50 | 3 | 14 | −0.81 | FIXED_10 | −1.38 | **+0.56** |
| token_gain | 0.50 | 1 | 6 | −2.25 | FIXED_5 | −2.81 | **+0.56** |
| char5_gain | 0.40 | 2 | 15 | −0.62 | FIXED_15 | −0.69 | +0.06 |
| char5_gain | 0.50 | 1 | 8 | −2.00 | FIXED_8 | −1.62 | −0.38 |

**11 of 14 stopping settings beat the fixed arm at matched cost.** The best
margin is **+0.56 facts**, against a total headroom of 2.81 facts between
`FIXED_5` and taking everything — roughly a fifth of what is available.

On 16 streams, a consistent-sign margin under one fact is suggestive and no
more. It is reported as suggestive.

## 5. Does novelty track fact gain at all?

| unit | sign agreement | mean fact gain when novel | when stale |
|---|---|---|---|
| token_gain | 0.542 | 0.187 | 0.038 |
| char5_gain | 0.534 | 0.175 | 0.050 |
| token_jaccard | 0.492 | 0.108 | 0.118 |

Sign agreement is barely above the 0.500 chance line, and `token_jaccard` is
**below** it — a unit that inverts should not be carried forward. The
mean-gain contrast is better: a novel candidate carries about **5×** the fact
gain of a stale one under `token_gain`.

So the signal exists and is weak. It is enough to rank candidates and not
enough to locate a stopping depth.

## 6. Why this stops, precisely

Not because novelty carries no information — §5 says it carries some — and not
because of duplicates, which §2 rules out. It stops because **the instrument
cannot price stopping.** Every stream fits inside the budget, so refusing to
stop costs nothing, and a diagnostic where the degenerate arm is optimal cannot
rank anything against it.

That is a defect in NF-001's design, not a property of the mechanism, and it was
not visible before the streams were assembled. Naming it is the useful output.

## 7. What instrument would answer the question

1. **Streams long enough that stopping costs something.** IC-001's are 32–35
   deep. LongMemEval supplies 11,453 episodes across 50 haystacks, already
   fetched, already covered by the CC-006 cache at zero model calls.
2. **Regret priced against budget, not depth.** The question is not "how many
   candidates" but "what is displaced" — this program's whole finding is that
   packing order gates delivery, so a candidate taken is a candidate that
   displaces another.
3. **A statistic that a late-stopping arm cannot win.** Regret-vs-oracle is not
   it. Regret per unit of budget consumed would be.

## 8. What this earns

Nothing is promoted, adopted, or authorized. `NF-001` does not unblock DMR-005
and never claimed it would.

What it establishes: on non-repeating internal streams, marginal novelty carries
a weak fact-gain signal (≈5× contrast), a novelty floor beats matched fixed
depth 11 times in 14 by under one fact, and no setting adapts its depth anywhere
near as much as the oracle depth varies. A retrieval-side sufficiency signal is
not refuted here. It is untested, on an instrument that could not test it.
