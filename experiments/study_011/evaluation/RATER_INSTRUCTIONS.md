# Study 011 — Blind Rater Instructions

You are one of three independent raters. You have no history with this
project and you are not told which system produced any answer. Score only
what is in front of you.

**Do not look for, open, or reason about:** which arm produced an item,
any retrieval or delivery log, any packing order, any fact-plant key, or
any other rater's scores. If you find yourself inferring which system an
answer came from, that inference is not evidence and must not affect a
score.

---

## 1. Calibration gate — do this first, and stop if it fails

Score every item in `experiments/audits/scoring_integrity/calibration_set.json`
and compare against its `expected` value. **You must reproduce every one,
including `cal_no_answer` at 0.0.** If any disagrees, stop and report the
disagreement; do not proceed to real answers. The gate is never waived.

---

## 2. Two rules that override everything else

1. **Only content outside reasoning blocks is scoreable.** Reasoning has
   already been stripped from the packets. What you see is the whole of
   what counts.
2. **An item with no final answer is `NO_ANSWER` and scores 0.0.** Items
   carry `"no_answer": true` when stripping left nothing. Score those 0.0
   with the rationale "NO_ANSWER". Never score an answerless item above
   zero.

Mid-sentence truncation is a protocol deviation and earns no credit.

---

## 3. The locked criteria

Scores are 1.0, 0.5, or 0.0 unless the criterion says otherwise. Where a
criterion is binary, **there is no 0.5 category** — do not invent one.

| Q | What is asked | Scoring |
|---|---|---|
| **Q1** | Main span length of Halcyon Crossing and its steel grade. Expected: 847 metres, S460ML | 1.0 both · 0.5 one · 0.0 neither |
| **Q2** | Lead engineer and maximum load rating. Expected: Dr. Anara Bekova, 92.4 metric tons per axle | 1.0 both · 0.5 one · 0.0 neither |
| **Q3** | Both formatting rules stated precisely. Expected: numbered lists for technical specifications; risk classification on engineering recommendations | 1.0 both · 0.5 one · 0.0 neither |
| **Q4** | Painting, artist, patron, completion year. Expected: The Annunciation of Forlì, Melozzo da Forlì, Cardinal Giuliano della Rovere, 1483 | 1.0 all four · 0.5 two or three · 0.0 one or none |
| **Q5** | Pigment technique — ground and glaze. Expected: lead white ground, ultramarine glaze | 1.0 both · 0.5 one · 0.0 neither |
| **Q6** | Cardinal Giuliano della Rovere's role and its significance. Expected: patron of The Annunciation of Forlì, later Pope Julius II | **Binary.** 1.0 clean Renaissance retrieval · 0.0 cross-topic contamination or fact absent |
| **Q7** | Organism, researcher, depth range, feeding behaviour. Expected: Vampyroteuthis infernalis, Dr. Kenji Watanabe, 600–900 metres, marine snow particle aggregation | 1.0 all four · 0.5 two or three · 0.0 one or none |
| **Q8** | Bioluminescent organ and its location. Expected: photophores along the mantle margin | 1.0 both · 0.5 one · 0.0 wrong or absent |
| **Q9** | Same answer as Q6's turn, scored for topic bleed. Bleed indicators: Taylor Rule, Dr. Priya Mehta, inflation threshold, Vampyroteuthis, Dr. Kenji Watanabe | **Binary.** 1.0 clean Renaissance retrieval · 0.0 contamination from the monetary or marine topics |
| **Q10** | Researcher disambiguation. Three researchers exist: Dr. Anara Bekova (engineering), Dr. Priya Mehta (economics), Dr. Kenji Watanabe (marine biology). Expected: Watanabe correctly tied to Vampyroteuthis | **Binary.** 1.0 correct attribution · 0.0 researchers conflated |
| **Q11** | Every numerical value, named entity and technical specification across all four topics. Values: 847m, S460ML, 92.4 MT/axle, 1483, 600–900m, 2.3%, 2%. Entities: Halcyon Crossing, Dr. Anara Bekova, The Annunciation of Forlì, Melozzo da Forlì, Cardinal Giuliano della Rovere, Federal Reserve, Taylor Rule, Dr. Priya Mehta, Vampyroteuthis infernalis, Dr. Kenji Watanabe | **Binary, no 0.5.** 1.0 if ≥80% of values and entities are present with correct attribution · 0.0 otherwise |
| **Q12** | Both rules stated precisely. Expected: numbered list rule and risk classification rule | **Binary.** 1.0 both correct · 0.0 one or both missing or wrong |
| **Q13** | Rule compliance across the late turns supplied in the item. Rule 1: numbered lists when specifications are listed. Rule 2: `(Risk: X)` when engineering recommendations are made — score N/A and apply Rule 1 alone if no engineering advice was requested | **Binary.** 1.0 applicable rules honoured in ≥5 of 9 late turns · 0.0 absent or inconsistent |

Where a criterion is ambiguous, resolve it from the criterion text before
reading the affected answers — not afterwards.

---

## 4. Strict score

Where a primary score credits an offered correct alternative among
unresolved possibilities, also record a **strict** score that rejects
hedging. Where the two agree, record the same value in both.

---

## 5. Output

Write JSON to the path you were given:

```json
{
  "rater": "<your model id, as observed>",
  "calibration": {"passed": true, "disagreements": []},
  "scores": {
    "<item_id>": {
      "primary": 1.0,
      "strict": 1.0,
      "rationale": "grounded in the answer's own words"
    }
  }
}
```

Every score needs a rationale grounded in the answer text. A rationale
that restates the criterion without pointing at the answer is not a
rationale. Score every item in the packet; do not skip any.
