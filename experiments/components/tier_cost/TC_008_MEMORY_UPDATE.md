# TC-008 Research Memory Update

TC-008 is complete at `REGISTERED-OFFLINE`. It held TC-007's dense ranking,
fixed 50/50 allocator, 16k/32k exact-character budgets, renderer, deduplication
and slack return fixed. The only change replaced A3's 16 embedding clusters
with real LoCoMo source sessions under the same relevance-plus-0.1-novelty
objective.

Disposition is `DENSE_CARRIES_SIGNAL`; no session split is selected. At 16k,
combined complete evidence is 728 versus dense 749, breadth is 13 versus 16,
and targeted is 629 versus 643. Breadth identity delivery has one gain and five
losses across one/four questions. Dense fires both combined and targeted
guardrails. At 32k all three complete endpoints tie, while session spread loses
one breadth identity.

Session novelty behaves as named but the name is not the answer property. At
16k it raises median represented sessions from 24 under dense to 30. Yet among
27 evidence-changing questions there are only three unique gains, nine losses
shared with any fixed 50/50 protection, and fifteen extra losses relative to A3
caused by source-session grouping. More covered sessions certify nothing about
required evidence.

The 16 targeted carriers lost at 16k have dense ranks 27–52, median 41. A3
rescues eight; session grouping does not. The one breadth gain adds a rank-87
candidate to “How old is Jolene?” but leaves the question incomplete. Three
previously complete breadth questions become incomplete even while represented
session counts rise by 7–9.

TC-008 closes fixed 50/50 source-session novelty, not all protected spread. A
successor would need a query-conditioned signal for missing evidence; global
session touch is ruled out as its certifying surrogate. The offline fallback is
full-budget dense.

G0 passed 2,214 tests, 3,484 TC-007 payload anchors, 1,742 treatment payloads,
70,736 mechanism steps and two fresh prefixes. The accepted two-worker run is
byte-identical with zero cache misses, zero embedding calls and zero LLM calls.
The selection manifest has 871 questions and no answer/evidence keys.

Reader answers were deliberately not started. The next work must separately
preflight and register its reader, frozen context contrast, prompt, replicate
schedule, fact-use scorer and bars.
