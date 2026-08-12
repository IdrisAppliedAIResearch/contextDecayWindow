# DMR-001C Memory Update

DMR-001C is the first confirmatory test in this line. The rule was frozen at
DMR-001B's anchor and committed before LongMemEval was re-fetched, the corpus
slice overlaps no earlier study, and the registration commit contains no
implementation file.

G4 confirms the transfer claim. Across 50 unread haystacks, 11,453 episodes and
2,128 real session seams, per-stream fire rate held between 3.41% and 7.35%, a
p95/p05 ratio of 1.67x. DMR-001's fixed threshold swung tenfold between two
synthetic scripts and died on one. A relative bar carries its operating point
onto real multi-session conversation with no parameter touched.

G5 fails. Macro F1 .387 against C_PERIODIC_4's .606. The reason is recall, not
accuracy: precision is .837 against a .186 base rate and never fell below .556
on any stream, but the rule fires on ~5% of episodes where seams occur on
18.6%. `min_event_size` 5 cannot resolve seams inside six-exchange sessions.
The registration recorded that ceiling before the run.

Two things carried forward. `min_event_size` was inherited from DMR-001 and
never tested against short sessions; it, not the threshold, is now the binding
constraint. And macro F1 was a poor statistic for a corpus with an 18.6% base
rate, because it rewards frequent firing - C_PAIR's precision equals the base
rate exactly. That defect is recorded and not re-scored; a successor must
register a base-rate-insensitive statistic before seeing a result.
