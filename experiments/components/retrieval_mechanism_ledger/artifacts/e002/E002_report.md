# E002 Segmented Query Retrieval

**Design commit:** `b42f4f81b371225b082204cfbbb03aa031d5f24c`  
**Execution commit:** `51e55e47725ccd92b762771302e21eaa527c389a`  
**Outcome:** **KILL**

## Result

The same-budget unchanged-selector baseline delivered **6/17** items at 31,946 of 32,000 characters. The historical 13/17 hurdle came from the 60,595-character corrected run and is retained as the stricter comparison.

The best segmented configuration delivered **10/17** items across **3/4** domains. It used `S=4`, `o=1`, `b=2`, selected 10 episodes, and serialized 21,761 characters.

Targeted no-regression preserved **14/16** committed-available items.

## Integrity

Mechanism seal: **PASS**. Leakage audit: **PASS**. Source integrity: **PASS**. Byte-identical raw rerun: **PASS**.

This is an offline availability result. It makes no answer-correctness claim and authorizes no inference run.
