# DA-009 Scratchpad

## Inherited Evidence

- DA-008 exact speaker dictionaries: median 504 characters saved, 935 direct
  preserved, benefit links 961 (+26/0), one-hop oracle 986 (+51).
- Ranking advantage over controls is not differentiated. Freeze it; this branch
  tests renderer capacity only.

## Blind Feasibility

- Default role tuple is `(0,1)` on 730 contexts and `(1,0)` on 374.
- Data-informed pre-registration distribution: incremental savings min/p10/p50/
  p90/max = 79/111/147/191/235 characters; median 39 matching direct pairs.
- Branch rule: if complete delivery does not exceed 961 without any conversation
  regression, role-pattern compression closes and the next lead returns to the
  link payload representation, not ranking threshold tuning.

## Result

- Blind gate passes: median incremental savings 147 chars, minimum 79; 43,939
  matching and 27,614 exception pairs exercise both render paths.
- Frozen DA-004 order rises 961->966: +31/0 versus direct, all conversation
  totals nondecreasing. Links admitted rise 2,561->3,181.
- Incremental item discordance is 7 gains/2 reroutes, p=.180: descriptive signal,
  not a standalone statistically differentiated step.
- One-hop oracle remains 986; 31/51 reachable gains recovered, 20 remain.
- Lead retained: compact full linked payloads or remove more repeated structural
  metadata. Keep ranking frozen; do not tune NF-004 thresholds.
