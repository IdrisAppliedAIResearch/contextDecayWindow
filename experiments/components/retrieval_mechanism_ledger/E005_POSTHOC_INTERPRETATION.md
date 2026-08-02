# E005 Post-Hoc Interpretation

**Date:** 2026-08-01
**Design anchor:** `ebbf384e18f38c5af017464e4723a3c77d81e73b`
**Outcome:** `PROMOTION_ELIGIBLE`
**Companions:** `E005_diversity_selection_protocol.md`, `artifacts/e005/E005_report.md`,
`amendments/AMENDMENT_004_targeted_item_identity.md`

Everything below is interpretation written after the outcome was fixed. None of
it changes a gate, threshold, or verdict.

## 1. Headline

A set-level selection objective roughly doubles matched-budget breadth
availability and does so without costing anything on targeted recall.

| Arm | Selector | Best Q11 | Domains | Targeted |
|---|---|---:|---:|---:|
| A0 | committed cosine / N-first packing | 6/17 | 3/4 | 16/16 |
| A1 | MMR | 12/17 | 4/4 | 16/16 |
| A2 | facility location | 13/17 | **3/4** | 16/16 |
| A3 | relevance plus cluster diversity | 12/17 | 4/4 | 16/16 |
| A4 | AR-001 oracle, carried | 15/17 | 4/4 | n/a |

Primary configuration `A3_l0.1_r0.0_k16`: **12/17 items across 4/4 domains, 16/16
targeted items preserved, 4 of the oracle's 5 episodes recovered, 15 episodes,
31,569 characters.**

All 146 configurations cleared the 7/17 kill bar. 137 preserved targeted recall
completely, 40 reached all four domains, and 35 passed all three gates.

For scale: E002, the previous best matched-budget mechanism, reached 10/17 at
3/4 domains and was killed. E005's worst configuration on the primary pool beats
A0, and its best four-domain configuration beats E002 while covering the domain
E002 never reached.

## 2. Facility location wins the count and fails the purpose

A2 produced the single highest raw availability, 13/17, and never passed a gate.
At every value of `r` it delivered **monetary 0/4** while taking civil 5/5, art
3-4/4, and marine 4/4.

This is the surrogate the protocol was written to catch, firing exactly as
predicted: *"a selector that improves the total while still dropping a domain
has not solved breadth."* Had E005 scored on total facts alone, A2 would have
been the winner and the report would have claimed a breadth result while
delivering a three-domain payload.

It also inverts the scan's expectation. B.4.3 argued facility location would be
*pushed toward spanning* the store while MMR could assemble mutually dissimilar
items from one corner. On this store the opposite happened: facility location
maximizes representation of the corpus as it actually is, and this corpus is not
uniform across the four probe domains. Representing the store faithfully is not
the same as covering the query's domains, and the monetary region is small
enough that a faithful representative set can skip it entirely.

**The per-domain diagnostic, not the headline count, is what made this visible.**

## 3. Registered escalation: `r` is not inert

The protocol registered a prediction and an escalation:

> The sweep is deliberately small: the budget is slack at roughly four times
> headroom, so `r` is expected to be inert. If `r` matters materially that
> contradicts the slack-budget analysis and is escalated as a finding.

**`r` matters materially and the escalation is hereby raised.** It changes the
Q11 fact count in **44 of 44** A3 `(lambda, k)` cells, typically from 7 facts at
`r = 0` to 11 at `r = 0.5`. In A2 it moves 13 to 12.

The slack-budget analysis was not wrong, it was answering a different question.
The budget is slack *for the optimum*: AR-001's 15/17 costs 5,455 of 32,000
characters. The budget is not slack *for the selector*, because the registered
greedy frame fills the budget. Every arm spends 31,000-plus characters, so the
knapsack constraint is active at every step and cost scaling changes both which
episodes are chosen and how many fit.

Cost-normalized greedy was imported as machinery for a constraint this problem
was believed not to have. It turns out to have it, created by the decision to
fill the budget rather than by the structure of the store. **The knapsack half of
the literature transfers after all, for a reason the scan did not anticipate.**

## 4. The candidate-pool decision was load-bearing

Registered before implementation, on the ground that a restricted pool would set
the ceiling by pool construction rather than by the selector. The secondary
pools confirm it:

| Pool | Episodes | Best Q11 | Configurations reaching 4/4 domains |
|---|---:|---:|---:|
| full eligible store | 119 | 13/17 | **40** |
| cosine top-100 | 100 | 13/17 | 29 |
| deployed N-cap union K | 34 | 13/17 | **0** |

Every pool reaches the same best raw count, so a report scoring on totals alone
would have concluded the pool does not matter. It matters completely: **on the
deployed pool, no configuration covers all four domains, so nothing could have
passed the surrogate gate.** Had the ledger's literal "existing N-cap retrieval
output" reading been implemented, E005 would have returned a rejection produced
by pool construction and attributed to the selectors.

The pre-filter cost is a real deployment finding in its own right: the deployed
candidate pool cannot express a four-domain answer regardless of how well
anything downstream selects.

## 5. Greedy is near its bound; the objective is the ceiling

Data-dependent optimality ratios for the submodular arms land between **0.9548
and 0.9996** across 135 configurations. Greedy is recovering essentially all of
what its own objective can offer.

That relocates the remaining gap. A3 at 12/17 against the oracle's 15/17 is
**not** a greedy-approximation gap of three facts. Greedy is close to optimal
*for the objective it was given*; the shortfall is that relevance-plus-cluster
coverage is a surrogate for fact coverage, and the surrogate tops out below the
answer-key objective. Tuning the search harder will not close it. A different
objective might.

This is the same lesson the program has recorded five times in other clothing:
the mechanism optimizes what it measures, and dissimilarity is not information.

## 6. Prior-answer fraction: the hazard is live

Across the 35 gate-passing configurations the prior-answer fraction runs
**0.100 to 0.333, mean 0.237**. The primary configuration sits at the top of that
range: **5 of its 15 selected episodes are prior probe answers rather than raw
content turns.**

Four of AR-001's five optimum episodes are also prior probe answers, so this is
a property of where the facts are in this store, not a pathology the selectors
invented. It is still a hazard, and it is the one Study 004 documented: an
architecture that prefers prior answers propagates prior errors, and Q11's prior
answers were largely wrong.

**Availability is not correctness.** E005 measures whether the text is in the
window. A payload built substantially from earlier answers can make a fact
available and simultaneously re-supply the error that accompanied it. Nothing in
this component test detects that, and no live run has been authorized to check.

## 7. Verification owed to the scan: the MMR claim is refuted

The scan recorded, explicitly unverified, that:

> MMR's objective is widely described as **lacking the submodularity** that buys
> the greedy guarantees, which would make it a heuristic where Lin and Bilmes'
> formulations are approximation algorithms. This was not confirmed from a
> primary source.

Checked against the primary text, Lin and Bilmes (2011), *A Class of Submodular
Functions for Document Summarization*, ACL-HLT, pages 510-520. Section 3 states
the opposite and proves it:

> "Interestingly, the gain function defined in the original MMR paper (Carbonell
> and Goldstein, 1998) satisfies diminishing returns, a fact apparently
> unnoticed until now."

> "**Theorem 2.** Given an expression for `F_MMR` such that
> `F_MMR(S ∪ {k}) − F_MMR(S)` is equal to Eq. 1, `F_MMR` is non-monotone
> submodular."

> "diminishing-returns hold ... and therefore `F_MMR` is submodular. On the other
> hand, `F_MMR` would not be monotone, so the greedy algorithm's constant-factor
> approximation guarantee does not apply in this case."

**The claim as scanned is refuted.** MMR's objective *is* submodular. What it
lacks is **monotonicity**, and monotonicity is what the guarantee requires.

The scan's conclusion happened to be right - MMR carries no constant-factor
guarantee where the Lin and Bilmes formulations do - but its stated reason was
wrong, and the corrected reason is more specific and more useful. Lin and Bilmes
treat MMR's submodularity as a contribution of their own paper, which is why the
folk description the scan repeated is so common.

Two consequences for this repository:

1. **The E005 implementation is correct but its comment was imprecise.** MMR is
   reported as having no computable data-dependent optimality bound. That is the
   right behavior, because the bound derivation requires monotonicity, not
   because MMR lacks a set function. It has one; it is non-monotone.
2. **Nothing in this repository may state that MMR is non-submodular.** The
   accurate statement is *non-monotone submodular*.

## 8. What E005 does not establish

- **One probe, one store.** Q11 is the program's only breadth probe. No general
  breadth capability may be claimed, anywhere the number is cited.
- **Availability, not correctness.** No answer was generated, scored, or read. A
  12/17 payload is not a 12/17 answer, and Section 6 is the specific reason to
  doubt the step from one to the other.
- **No live run is authorized.** Promotion eligibility means the mechanism
  cleared its offline gates, not that it has been validated in inference.
- **The oracle was carried, not beaten.** A4 remains at 15/17 and A3 reaches
  12/17. AR-001's exact frontier reaches 17/17 at 7,592 characters, so headroom
  above the oracle exists and no deployable arm approached it.
- **A2's 13/17 is not a breadth result** and must not be cited as one without
  its 0/4 monetary column attached.
