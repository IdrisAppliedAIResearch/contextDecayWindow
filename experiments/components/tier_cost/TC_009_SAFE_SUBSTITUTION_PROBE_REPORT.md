# TC-009 safe-substitution signal probe — report

**Status:** `NO_POSITIVE_SIGNAL`; descriptive feasibility diagnostic  
**Design commit:** `fe52d000`  
**Implementation commit:** `c3243b65`  
**Preflight commit:** `7adea87c`  
**Date:** 2026-08-23

## Result

No frozen evidence-blind feature identifies TC-009's safe 32k substitutions.
Among 868 eligible questions, required-identity delivery has 7 gains, 23 losses
and 838 ties; complete evidence has 4 gains and 20 losses. None of the 15
predeclared query-score, redundancy, novelty, rank, session, cost or penalty
features passes the descriptive signal rule.

| Strongest clue | AP | AP / prevalence | Gain-vs-loss AUC | Top-20 gains | Conversation AUC | Result |
|---|---:|---:|---:|---:|---|---|
| Worst incoming-vs-outgoing query margin | .0541 | 6.71x | .708 | 1 | conv-41 .30; conv-42 1.00; conv-48 .78 | Fails consistency and top-20 |
| Mean outgoing dense rank | .0838 | 10.39x | .509 | 1 | .30; .70; .39 | Near chance on discordances |
| Worst outgoing dense rank | .0391 | 4.85x | .537 | 1 | .45; .90; .39 | Near chance on discordances |

The high AP lifts are caused by seven gains in a prevalence of only `.0081`;
they do not produce useful precision. The strongest top 20 contains one gain.
Candidate-to-retained novelty and redundancy range from `.47` to `.54` AUC,
session-count delta is `.39`, and accumulated-penalty summaries are `.46–.49`.
Missingness controls are exactly `.50` AUC and pass nothing.

## Interpretation

The current observables do not support a conservative replacement gate. The
one pooled score-margin clue changes direction across conversations, which is
the failure a same-corpus aggregate would hide. Registering a selector from it
would be post-result tuning on an exhausted development corpus.

This does not prove safe substitution impossible. It says the available dense
score, embedding-redundancy, rank, session, cost and penalty signals do not tell
us which TC-009 replacements are safe. A successor needs a genuinely new
query-conditioned information signal or new corpus evidence, not another
combination of these features.

## Integrity and boundary

Preflight sealed 871 feature rows at SHA-256
`03faa2f020dae21ae57e79731548f0b5056f80825c67340168089474572a244e`
before label import, replayed all 1,742 accepted control/dynamic payload
identities, and rejected planted early label access. Zero cache misses,
embedding calls and LLM/generative calls occurred. Availability only; no
selector, threshold, reader evaluation or TC-010 is authorized. The final
repository suite is 2,231 passed.
