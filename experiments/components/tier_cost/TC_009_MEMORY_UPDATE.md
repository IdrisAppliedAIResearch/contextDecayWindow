# TC-009 Research Memory Update

TC-009 is complete at `REGISTERED-OFFLINE`. It held TC-008's dense semantic
route, exact 50/50 allocator, 16k/32k character budgets, renderer, deduplication
and slack return fixed. The only change made every source session compete by
its best remaining cosine candidate, then subtracted `.03` for each candidate
already selected from that session before immediately letting it compete again.

Disposition is `DENSE_WORKS`; dynamic spread is rejected. At 16k, dynamic
combined/breadth/targeted complete evidence is 713/12/624 versus dense
749/16/643. At 32k it is 794/21/674 versus 810/27/680. Breadth identity delivery
has 1 gain/9 losses at 16k and 4 gains/9 losses at 32k. There is no complete
breadth gain at either budget, and dense guardrails fire at both.

The mechanism is not a disguised hard session floor. All 871 real traces allow
a session to win twice before every session is represented; 606 contain
consecutive same-session wins in the full order. Nevertheless most evidence
damage is unique to the cumulative penalty: 34 required identities at 16k and
22 at 32k, versus 7 and 0 losses common to all fixed-50/50 arms. Penalized
sessions often still own the best remaining evidence.

Targeted carriers lost from otherwise dense-complete contexts have dense ranks
24–57 (median 38.5) at 16k and 60–112 (median 71) at 32k. Breadth gains never
produce a complete-evidence gain. The largest visible 32k breadth addition puts
three required identities into “What job might Maria pursue in the future?”
but still leaves the question incomplete.

The lesson is narrower than “do not spread.” Count-based session exposure is
not a sufficient value signal, whether enforced once through novelty or
repeatedly through a soft penalty. A successor needs a query-conditioned signal
for missing information, not another transformation of how often a session has
already been touched. The offline fallback remains full-budget dense.

G0 passed 2,226 tests, 5,226 predecessor anchors, 1,742 dynamic payload checks,
296,166 full-order states and 69,961 admitted states. Two complete workers are
byte-identical with zero embedding calls, LLM calls or cache misses. Reader
answers were deliberately not started. The final repository suite is 2,228
passed.

## Post-close dependency-graph probe

The model-free dependency/graph route is `NO_POSITIVE_SIGNAL`. At 32k,
dense/IDF lexical/dependency PageRank/subject overlap/subject-personalized
PageRank complete delivery is 810/727/677/316/344; breadth is 27/15/10/3/3.
Every treatment loses in all four conversations. Dependency centrality loses
50 complete questions to its lexical control. Direct subject signals leave a
median 295 candidates tied at zero; personalized subject mass leaves 261.

Preflight corrected one blind exploration count by standalone amendment:
870/871, not 871/871, questions have any exact subject-overlap candidate. It
then reproduced all 871 dense payloads and converged 1,365 standard plus
204,409 personalized graphs. No embedding vectors were read, and embedding and
LLM calls were zero. Grammatical subject is not a usable surrogate for section
topic on this corpus; no TC-010 or reader work follows.
The final repository suite after this probe is 2,238 passed.
