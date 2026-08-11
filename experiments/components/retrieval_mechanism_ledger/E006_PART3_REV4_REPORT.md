# E006 Part 3 Rev 4 Autoassociative Construct Repair Report

**Date:** August 10, 2026
**Outcome:** **PATTERNS_NOT_STORED - CHARACTERIZED**
**Stage:** Preflight Part 1 stop at G3
**Original P3 outcome:** unchanged (`NO_DIFFERENTIATED_CUE - CHARACTERIZED`)
**Design commit:** `a4f952f6`
**Authorization commit:** `27313b66`
**Input amendment commit:** `8c2c0a16`
**Implementation commit:** `942cde4e`
**Exploration implementation commit:** `84646efa`
**Exploration result commit:** `47bcc882`
**Result:** `artifacts/e006_p3_rev4_exploration/exploration.json`
**Result SHA-256:** `1942950078E0A7EB30619F66356E0373208372415B401B61A49DAE6FE8CDAA78`
**Calls:** zero embedding requests; zero model-generation calls

## 1. Repair boundary

The completed E006-P3 mechanism was a local walk over a dense-cosine episode
graph. It did not learn recurrent weights, store attractors, converge a neural
state, or test recovery from a degraded cue. Its negative retrieval result
therefore did not test neural pattern completion.

Rev 4 prospectively replaced that construct with a deterministic canonical
autoassociative memory. It median-centered the 119 carried 1,024-dimensional
episode vectors into unique bipolar patterns, learned a symmetric zero-diagonal
Hebbian matrix, and ran fixed-order asynchronous updates to convergence while
recording Hopfield energy.

This is a minimum computational construct, not a claim of full hippocampal
replication. Classical content-addressable memory recovers a stored state from
a degraded state through collective dynamics; CA3 work tests recovery from
partial cues, and human event-completion work tests reinstatement of associated
elements within one coherent event ([Hopfield 1982](https://pubmed.ncbi.nlm.nih.gov/6953413/),
[Nakazawa et al. 2002](https://pubmed.ncbi.nlm.nih.gov/12040087/),
[Horner et al. 2015](https://www.nature.com/articles/ncomms8462)).

## 2. Input amendment

The post-authorization audit found that internal Q11 has 119 retained scalar
episode cosines but no retained query vector. The 48-vector Rev1 cache contains
only named bakeoff holdout queries. Amendment 005 removed the descriptive Q11
translation probe rather than bipolarizing a non-identifiable least-squares
surrogate. The binding attractor gates, patterns, weights, recurrence, and exact
bars were unchanged.

## 3. Ordered result

G1 passes: the input is 119 unique content identities, 119 unique bipolar
patterns, and a finite `119 x 1024` matrix. G2 passes: the learned matrix is
finite, symmetric, exactly zero-diagonal, and the implementation agrees with an
independent slow oracle. The synthetic two-pattern fixture stores both patterns
and recovers all `16/16` one-bit corruptions exactly, proving G3 and G4 are
reachable.

G3 fails on the real store:

| Observation | Result |
|---|---:|
| Stored episode patterns that are fixed points | `0/119` |
| Trajectories that converge | `119/119` |
| Trajectories with non-increasing energy | `119/119` |
| Terminal states equal to any stored pattern | `0/119` |
| Unique terminal fixed points | `6` |
| Terminal basin sizes | `5, 13, 15, 20, 29, 37` |
| First-sweep changed bits, min / median / max | `18 / 214 / 294` |
| Sweeps to convergence, min / median / max | `4 / 9 / 20` |
| Terminal Hamming distance from source, min / median / max | `194 / 467 / 531` |

The binding disposition is therefore `PATTERNS_NOT_STORED`. G4 one-bit
completion, G5 degenerate cues, PF1-PF10, parameter locking, Q11 measurement,
and live evaluation are not reached. The registered stop is the end-to-end
result, not missing work.

Two independent executions are byte-identical at result SHA-256
`1942950078E0A7EB30619F66356E0373208372415B401B61A49DAE6FE8CDAA78`.

## 4. Mechanical post-mortem

The repair moved the test to the right property and exposed the next failed
translation. Every coordinate is positive in exactly `60/119` patterns, so the
median transform achieves balanced feature marginals. That balance does not
certify pattern separation or independent memory codes. Pairwise normalized
overlap ranges from `-0.186` to `0.699`; the closest pair differs in only
`154/1024` bits.

Under Hebbian superposition, each memory receives its own stabilizing term plus
cross-talk from the other 118 patterns. The observed dependencies make at least
one local field disagree with every stored pattern, so none is a fixed point.
The recurrent dynamics themselves behave correctly: energy falls and every
trace converges. They converge to six spurious mixtures because the encoded
episode vectors did not define the intended attractor landscape.

The failed surrogate is now explicit:

> Balanced coordinate activity passed while stored episodic attractors were
> false.

This does not show that established neuroscience lacks mechanical consequences.
It shows that a dense semantic embedding, even after deterministic binarization
and marginal balancing, is not automatically a hippocampal engram code. Sparse
pattern separation, event-element binding, natural partial cues, and a mapping
from model representations into that code remain absent. Leutgeb et al. show
that hippocampal subregions transform similar inputs differently; Rev 4 did not
implement that circuit function ([Leutgeb et al. 2007](https://pubmed.ncbi.nlm.nih.gov/17303747/)).

The Q11 mismatch also remains. Q11 asks one cue to enumerate facts from four
unrelated memories, while autoassociation completes one basin. A future
multi-memory controller would be an additional executive retrieval component,
not evidence that a single attractor failed.

## 5. Preflight and scope

Preflight Part 1 completed and stopped at the binding construct gate. Part 2
PF1-PF10 was not entered, so this report makes no PF PASS claim. The exploration
artifact records the full pattern and pairwise distributions, all 119 G3 energy
and state-hash traces, the synthetic reachability fixture, the construct table,
input hashes, and the ordered not-reached stages.

The result authorizes no alternate encoding, pseudoinverse learning rule,
capacity reduction, episode filtering, natural-language cue claim, Q11 score,
live run, promotion, adoption, or full hippocampal-replication claim. A sparse
pattern-separation encoder would be a new component and requires a new
prospective study rather than a post-result Rev 4 repair.

Verification passes the focused original-P3 and Rev4 tests and the full
repository suite, `1439/1439`.
