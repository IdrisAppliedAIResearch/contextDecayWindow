# RD-001 Rarity-Variant Provenance Audit

**Date:** 2026-08-03
**Status:** CORRECTION - NO NEW RARITY MEASUREMENT

## Question

Which historical rarity variant supports the published statement that inverse
document frequency (IDF) ranked the six hard plants worse than density?

## Source Record

- `experiments/study_009/analysis/rarity_signal_feasibility.csv`
  - SHA-256:
    `344d1a342dd51b2008dd30107cb393bf0c9bac842df8b97f560059baa642b24e`
- `experiments/study_009/analysis/breadth_regression_audit.md`
  - SHA-256:
    `5e7876d79cf5218219de24437e7abb8857f4478052042bb27d045aa7044f2b00`
- Both first appear in commit
  `1177f53c3c63d031b72dcdf987fcfacf37c11ce2`.

The audit defines and reports three variants: mean content-word IDF
(`rarity_mean`), maximum content-word IDF (`rarity_max`), and summed IDF divided
by logged word count (`rarity_sum_per_word`). It does not designate a primary
variant and does not state the categorical conclusion "IDF worse."

The categorical claim first appears in commit
`b42f4f81b371225b082204cfbbb03aa031d5f24c`, which created the retrieval
mechanism ledger on 2026-07-30. That commit cites the breadth regression audit
but does not name a variant.

## Variant Comparison

Five plant spans have both an IDF rank and a density rank. The photophores span
is unranked under every variant because the retained eligibility rule excludes
it.

| Variant | Worse than density | Better than density | Result |
|---|---:|---:|---|
| `rarity_mean` | 5/5 | 0/5 | The only variant consistent with the categorical claim |
| `rarity_max` | 3/5 | 2/5 | Improves Taylor Rule and dual mandate |
| `rarity_sum_per_word` | 4/5 | 1/5 | Improves marine snow |

The historical numbers are unchanged. This table only compares fields already
present in the committed CSV.

## Verdict

No historical primary variant produced the published finding. The statement can
be reconstructed only by selecting `rarity_mean` after inspecting all three
variants. Because the audit never registered that selection, the categorical
claim that IDF ranked the hard plants worse than density is unsupported and is
withdrawn.

The narrower descriptive statement is supportable: mean content-word IDF ranked
all five eligible hard-plant spans worse than density, while the other two
variants disagreed on one or two spans. The sixth span remained unranked because
of the retained eligibility filter, not because of its rarity score.

## Boundary

No missing rarity score is computed here. Extending the statistic to the other
70 fact-bearing episodes would be a new measurement. It requires a prospective
RD-002 design that chooses one rarity formula and one phrase-to-episode
aggregation before computation and records that the cosine ranks were already
known when the rarity design was registered.
