# Study 010 Targeted Retrieval And Curve Validity Audit

This audit corrects the post-score analysis before merge. Scores and the Bar 1
arithmetic are unchanged.

## Terminal Targeted Questions

Arm S did not answer the 12 terminal targeted questions from the ten-episode
recency block alone. For Q1-Q12:

- all five required facts appeared in `<retrieved_stm>` for every question;
- Q1 also had three facts in recency, while Q2-Q12 had none of their required
  facts in recency;
- Arm S had 203 logged K retrieval events across those 12 turns; and
- all 60 required targeted facts were present in prompt and recalled.

The earlier statement that neither arm had a terminal targeted K hit was
false. The analysis parser treated the rubric's domain column as its type
column, leaving the targeted-turn set empty. The parser and generated
`k_probe_precision.csv` are corrected in this commit.

The targeted terminal result is therefore genuine long-range STM retrieval:
K supplied complete fact sets to S. It is not evidence that the terminal
questions were answerable from recency or an unlogged source.

## Breadth Discrimination

The targeted queries successfully focused K on one domain at a time. They do
not test simultaneous cross-domain allocation. Q13-Q14 do: L's LTM block
contained all 12 required pairs at each breadth turn, while S's prompt
contained two pairs at Q13 and one at Q14.

Thus the 2.0-point terminal gap genuinely rests on the two breadth questions.
That is not hidden by the targeted result, but it narrows the headline:
Study 010 supports LTM for cross-domain breadth at 1,000 turns; it does not
show an LTM advantage for single-domain targeted recall.

## Interim Curve Defect

The interim fractions are not comparable degradation measurements. Each
three-question checkpoint contains one recent-domain targeted probe whose
rubric requires two facts that had not yet been introduced:

| Probe | Turn | Available facts | Missing facts planted later |
|---|---:|---:|---|
| I2 battery | 251 | 3/5 from turn 246 | specification and threshold at turn 288 |
| I5 ecology | 501 | 3/5 from turn 493 | specification and threshold at turn 535 |
| I8 linguistics | 751 | 3/5 from turn 740 | specification and threshold at turn 782 |

Under the locked rubric, each item had a maximum reachable score of 0.5 at
its probe turn. Both arms reached that maximum. The nominal interim totals
therefore embed an unavoidable 1.5-point loss, while all terminal targeted
questions occur after their complete five-fact plants.

The apparent rise from interim to terminal performance is consequently a
probe-construction artifact, compounded by a composition change from three
questions per interim checkpoint to fourteen terminal questions. The files
remain a complete set of scored checkpoints, so Bar 3's literal completeness
criterion is met, but they do not support a degradation trajectory claim.

## Corrected Interpretation

- Confirmatory Study 010 remains stopped at G2.
- Exploratory Bar 1 arithmetic remains L 14.0 versus S 12.0 terminal and still
  triggers the registered `RETAIN LTM` consequence.
- The evidence is specific to breadth: targeted recall tied; breadth favored L.
- Exploratory Bar 3 is nominally complete but construct-invalid as a
  degradation measurement.
- No conclusion should compare interim and terminal score fractions as a
  temporal improvement or decline.
