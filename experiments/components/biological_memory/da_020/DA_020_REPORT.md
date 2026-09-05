# DA-020 Protected Boundary Substitution Continuation Report

**Status:** `NO_PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `47e7d0e3`
**Blind reproduction commit:** `1bcd1e7e`
**Standing:** spent-corpus exact-availability exploration

## Result

The one-swap dominance guard does not safely improve either strongest control.

| Corpus | Control | Treatment | Gains | Losses | Exact p |
|---|---:|---:|---:|---:|---:|
| NF-004 | **970** | 966 | 0 | 4 | .125 |
| LongMemEval | **188** | 188 | 2 | 2 | 1.0 |

NF-004 losses occur one each in conv-26, conv-30, conv-43 and conv-49; no
conversation gains. LongMem gains one single-session-user and one temporal item,
but loses one multi-session and one single-session-user item. The zero-loss and
cross-corpus criteria fail.

## Mechanism

The guard executed 571 NF and 188 LongMem substitutions while preserving direct
evidence and every earlier linked action. Replacements were generally smaller
and more question-similar than incumbents:

- NF median cost 140 -> 116 chars; cosine .430 -> .464.
- LongMem median cost 276 -> 241.5 chars; cosine .167 -> .226.

Those improvements did not preserve answer evidence. NF substitutions removed
five target identities and added two, yielding four complete-item losses and no
gain. LongMem removed four target identities and added three, producing a 2/2
completion trade.

The failure is sharper than DA-018's global-order result. Even at the final
linked boundary, preserving every incumbent-unique question token and requiring
higher question similarity cannot certify that the displaced payload is
dispensable. Query overlap is not an evidence-preservation invariant.

The strongest order should therefore remain immutable under these available
evidence-blind local signals. Further substitution work needs a genuinely
stronger protection invariant, not a softer score or a wider swap neighborhood.

## Integrity and Boundary

DA-020 reproduced DA-019's blind selection byte-identically at SHA-256
`b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f`.
Real streams had zero duplicate opportunities and the synthetic duplicate test
passed. Outcome replay is byte-identical at SHA-256
`1da9345512bcda2df5c9ea152ff97a6f2a0f792a561ea389ae703ab3b060a8d9`.

There were zero model, embedding and cache calls. Both corpora are spent and the
endpoint is evidence availability, not reader use. No tuning, second swap,
deployment or adoption claim follows.

