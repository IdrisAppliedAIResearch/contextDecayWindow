# DA-018 Frozen-Query Carrier Utility Report

**Status:** `NO_CROSS_CORPUS_CARRIER_UTILITY_SIGNAL`
**Date:** August 30, 2026
**Protocol commit:** `85d3046f`
**Blind allocation commit:** `013a0304`
**Standing:** spent-corpus exact-availability exploration

## Result

No frozen-query treatment improves both strongest corpus controls without loss.

| Arm | NF-004 complete | vs 970 control | LongMem complete | vs 188 control |
|---|---:|---:|---:|---:|
| Strongest control | **970** | - | **188** | - |
| Payload cosine | 952 | 6 gains / 24 losses | 179 | 7 / 16 |
| Cosine per character | 944 | 1 / 27 | 189 | 12 / 11 |
| Marginal utility | 960 | 1 / 11 | **191** | 6 / 3 |

NF-004 marginal utility loses ten net items (`p=.00635`); payload cosine loses
18 (`p=.00143`), and cosine per character loses 26 (`p=2.16e-7`). Every
NF-004 conversation is nonpositive under marginal utility.

LongMem marginal utility is descriptively +3 net, with 6 gains and 3 losses
(`p=.508`). It improves single-session-user by three with no losses, but loses
one preference item and trades within multi-session and temporal cells. The
registered zero-loss and cross-corpus criteria fail.

## Mechanism

Recomputing similarity against the original question avoids TC-012's semantic
feedback loop, but it does not solve carrier allocation. Direct payload cosine
is actively worse than both controls. Dividing by exact cost admits many more
small singleton payloads, but small and question-similar is not equivalent to
evidence-bearing.

The richer fixed marginal rule is the least harmful treatment. Its LongMem
movement suggests seed confidence, lexical novelty and exact cost contain some
allocation information when the control is temporal order. But on NF-004 it
overrides DA-004's learned whole-pack perturbation order and loses 11 established
completions to gain one. The corpus controls encode different useful priors:
pack perturbation on NF-004 and shallow temporal locality plus capacity on
LongMem. A common local payload score does not replace either safely.

The remaining scarcity problem is therefore not ordinary nearest-neighbor
rescoring. It requires estimating the *counterfactual completion value of the
whole residual pack*, or a protection rule that can improve an existing order
without globally replacing it.

## Integrity and Boundary

All 1,563 questions were processed. Blind allocation replay is byte-identical
at SHA-256 `3928700040ffe7931b5865414867b149595db67a431f32dc97a72d4e9f7ffcdb`;
opened outcomes replay at
`daceb9e0204524705fab787447ae8a72cced0d68db3158f766e770989548bcfd`.
LongMem used 7,866 sealed-cache hits and zero misses. There were zero model and
zero new embedding calls. Every gain has exact admitted-carrier accounting and
direct evidence remains immutable.

Both corpora are spent and the endpoint is availability, not reader use. No
formula tuning, selector adoption, live run or production claim follows.

