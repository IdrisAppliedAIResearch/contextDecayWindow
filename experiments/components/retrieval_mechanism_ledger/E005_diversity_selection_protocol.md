# E005 Diversity-Aware Selection Protocol

**Status:** PROSPECTIVE - no selection output generated
**Type:** Offline component test, not a study or pre-registration
**Parent:** `RETRIEVAL_MECHANISM_LEDGER.md`, E005
**Addresses:** F1 (breadth / enumeration)
**Inference calls:** 0
**Literature scan:** `LITERATURE_SCAN.md` diversity-aware selection item, COMPLETE

## Purpose

Test whether replacing per-item cosine ranking with a set-level selection
objective recovers a material fraction of the Q11 coverage gap AR-001 measured,
without degrading targeted retrieval.

AR-001 established that the gap is selection and not capacity: exact 14/17 costs
5,058 characters and 17/17 costs 7,592 against a 32,000 character budget, while
the deployed selector delivers 6/17 while spending 31,946. This protocol tests
deployable approximations of the coverage maximization AR-001 ran with answer-key
access.

Passing authorizes a promotion decision in the living ledger. It does not
authorize a live run, a new study, or any answer-correctness claim.

## Locked Inputs

- Corrected Tier 6 run:
  `experiments/surveys/retrieval_bakeoff/tier6/runs/tier6_live_121_corrected_001/context_matched_stm`
- Primary breadth probe: turn 120, Q11.
- Targeted no-regression probes: turns 112, 113, 115, 116, 117, 118, and 119.
- Store eligibility: raw episodes with `source_turn < probe_turn`.
- Candidate text and vectors: the stored raw episode embeddings already present
  in the corrected run database.
- Query embeddings: the carried Qwen3-Embedding-0.6B Q8_0 artifact, SHA-256
  `06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439`.
- Similarity: carried cosine implementation. No new embedder.
- Rendering: post-DR-001 `render_episode_element` through
  `render_stm_payload([], selected)`.
- Retrieval payload budget: exactly 32,000 Python characters after complete
  serialization. No arm may exceed it.

The input database and all source logs are read-only and hashed before and after
execution. The run's mechanism seal must pass before analysis.

## Candidate Pool - Registered Decision

**Primary pool: the complete eligible store, every episode with
`source_turn < probe_turn`, with no similarity pre-filter. For Q11 this is 119
episodes.**

The parent ledger entry described the pool as "the existing N-cap retrieval
output, cosine pre-filtered", and the scanned RAG practice uses a top-100 cosine
pre-filter. Measured against this store before this file was committed, those
readings are not interchangeable and one of them makes the experiment
unmeasurable. The Q11 cosine ranks of AR-001's five greedy-optimum episodes are:

| Oracle episode | Source turn | Q11 cosine rank of 119 | Cosine |
|---|---:|---:|---:|
| `dd904725-094b-4f94-a8fc-ca18668ad246` | 113 | 14 | 0.2640 |
| `77a1d148-12da-4a70-874d-42e816497c9a` | 118 | 21 | 0.2231 |
| `5c4446e4-fc4b-40f8-8b27-04cb33c7be57` | 112 | 22 | 0.2227 |
| `4c611a05-6ad0-434a-a188-1cdb941acf58` | 116 | 86 | 0.1088 |
| `1dec9c9e-b948-4ef8-9eaa-aa889c083470` | 90 | 112 | 0.0550 |

The deployed turn-120 N-cap union K pool holds 34 episodes and contains **two**
of the five. A cosine top-100 pre-filter contains four of the five, dropping the
turn-90 monetary episode that carries four Q11 items.

Restricting the pool would therefore set the achievable ceiling by pool
construction rather than by the selector, and E005 would measure the wrong thing.
The unrestricted pool is also close to the scanned top-100 practice at this store
size, so the departure is small in candidate count and decisive in ceiling.

**Registered secondaries, reported and never used for the kill decision:** the
same arms and configurations re-run against the cosine top-100 pool and against
the deployed 34-episode N-cap union K pool. The difference between primary and
secondary results is the measured cost of pre-filtering and is a reportable
finding in its own right.

## Arms

Every arm receives the identical candidate pool, budget, renderer, and
similarity function. Arms differ only in the selection rule.

| Arm | Selector | Role |
|---|---|---|
| **A0** | Corrected-run candidate order, N-first packing | Committed baseline, unchanged |
| **A1** | MMR, lambda sweep | Classical reranker |
| **A2** | Facility location, cost-scaled greedy | Corpus coverage |
| **A3** | Relevance plus cluster diversity, Shang form, cost-scaled greedy | Explicit diversity regularizer |
| **A4** | Greedy set cover over ground-truth facts | ORACLE, carried, never deployable |

### A0 - baseline, carried

The unchanged corrected-run N and K candidate ordering repacked with the compact
production renderer at 32,000 characters. This is E002's committed same-budget
baseline and is re-derived here through the same code path as a verification
gate, not recomputed with new logic. Committed value: **6/17 items across 3/4
domains, 8 episodes, 31,946 characters.**

### Common greedy frame for A1 to A3

Let `V` be the candidate pool, `q` the query vector, `v_i` episode `i`'s stored
vector, `rel(i) = cosine(q, v_i)`, and `sim(i, j) = cosine(v_i, v_j)`.

Additive serialized weight is `c_i = len(render_episode_element(i)) + 1`, the
AR-001 convention: the `+1` is the inter-line separator each episode contributes
inside a non-empty `<retrieved_stm>` block, and the fixed two-block wrapper is
charged once. The additive total must equal
`len(render_stm_payload([], selected))`; mismatch is fatal.

Selection is greedy and budget-filling. At each step, consider every unselected
candidate whose addition keeps the complete serialized payload at or below
32,000 characters, choose the one maximizing the arm's criterion, and repeat
until no candidate fits. Candidates that do not fit are skipped, never
truncated, and never terminate the loop - the carried packer's
graceful-degradation behavior.

Ties are broken by lowest additive weight, then lowest source turn, then lowest
episode ID. The ordered selection sequence is recorded so that facts delivered
against characters spent is reportable along the whole prefix.

### A1 - MMR

Carbonell and Goldstein (1998). Criterion for candidate `i` given selected set
`S`:

```
score(i) = lambda * rel(i) - (1 - lambda) * max_{j in S} sim(i, j)
```

with the penalty term zero when `S` is empty, so the first pick is the most
relevant candidate. `lambda` sweeps `[0, 1]` in steps of `0.1`. `lambda = 0.5`
is the common published default and is reported explicitly. `lambda = 1.0` is
pure cosine ranking under budget fill and serves as an internal control that is
distinct from A0's recency-first packing.

MMR is a per-step reranking criterion, not a set function, so no cost scaling
and no submodular bound apply to it.

### A2 - Facility location

```
f(S) = sum_{i in V} max_{j in S} sim_plus(i, j),   f(empty) = 0
```

where `sim_plus(i, j) = max(0, cosine(v_i, v_j))`. The clamp is registered
before implementation: it makes `f` monotone non-decreasing and submodular,
which the approximation guarantees require, and raw cosine over this store takes
negative values.

Greedy criterion is the modified cost-scaled ratio of Lin and Bilmes (2010):

```
gain(i) = (f(S union {i}) - f(S)) / c_i^r
```

`r` sweeps `{0, 0.5, 1.0}`. The sweep is deliberately small: the budget is slack
at roughly four times headroom, so `r` is expected to be inert. **If `r` matters
materially that contradicts the slack-budget analysis and is escalated as a
finding rather than absorbed.**

### A3 - Relevance plus cluster diversity

Shang et al. (2018) form, with the informativeness term instantiated as query
relevance:

```
f(S) = sum_{s in S} rel_plus(s) + lambda * |{ j : exists s in S with s in cluster_j }|
```

where `rel_plus(s) = max(0, cosine(q, v_s))`. The first term is modular and
non-negative; the second is a monotone submodular coverage count over clusters.
The same cost-scaled greedy ratio and `r` sweep as A2 apply. `lambda` sweeps
`[0, 1]` in steps of `0.1`.

Clusters are computed over the candidate pool vectors only. The cluster count
`k` is a free parameter that the parent entry does not fix, so it is swept
rather than chosen: `k` in `{2, 4, 8, 16}`. **The mechanism never reads domain
labels, the fact key, or any rubric artifact; that `4` appears in the sweep is
arithmetic regularity and confers no domain knowledge.**

Clustering is deterministic and uses no random number generator: farthest-first
initialization seeded at the lowest episode ID, followed by Lloyd iterations to
convergence or 100 iterations, with assignment ties broken by lowest cluster
index and empty clusters retained. Determinism is gated by byte-identical rerun.

### A4 - oracle, carried not re-derived

AR-001's committed greedy set-cover result, carried in as the reference point:
**15/17 items, 5 episodes, 5,455 serialized characters**, episodes at source
turns 90, 112, 113, 116, and 118. A4 is the only arm permitted to depend on the
ground-truth fact key, it is not re-run here, and it is never deployable.

## Registered Correction to the Parent Entry's Ceiling Language

The parent entry's surrogate table treats a fact count above 15/17 as
necessarily a fact-detection bug, on the grounds that the oracle's 15/17 cannot
be beaten. **That reasoning is incorrect and is corrected here before results
are opened.** AR-001's 15/17 is a *greedy* upper bound, not the maximum. Its
committed exact frontier reaches 17/17 at 7,592 characters, comfortably inside
the 32,000 budget, so a deployable selector exceeding 15/17 is admissible rather
than anomalous.

The bug signal is therefore registered as **a Q11 fact count above 17/17, or any
count whose items cannot be reproduced from the arm's own serialized payload**,
not as a count above 15/17. This correction makes the check stricter-correct and
changes no threshold: the kill bar, the no-regression gate, and the surrogate
gate are all unaffected.

## Parameters

| Parameter | Arms | Values | Count |
|---|---|---|---:|
| `lambda` | A1, A3 | `0.0` to `1.0` step `0.1` | 11 |
| `r` | A2, A3 | `0`, `0.5`, `1.0` | 3 |
| `k` clusters | A3 | `2`, `4`, `8`, `16` | 4 |

Total swept configurations: A1 11, A2 3, A3 132, for 146 deployable
configurations per pool.

## Kill Condition

**E005 is KILLED if no arm and configuration exceeds A0's committed 6/17 at the
enforced 32,000 character budget.** Exceeding means at least 7/17.

### Achievability of the bar, stated before implementation

Required by the parent entry, and by the E002 lesson that a bar must be checked
against the regime the arm actually runs in.

A0's 6/17 was measured in exactly the regime E005 arms run in: the same store,
the same compact post-DR-001 renderer, the same enforced 32,000 character
budget, the same eligibility rule. AR-001 proves from the same store and the
same renderer that 14/17 costs 5,058 characters and 17/17 costs 7,592, both
inside the budget, so counts far above the bar are reachable in principle. E002
reached 10/17 in this regime with a weaker mechanism, which is direct evidence
that 7/17 is attainable and not a formality. The bar is therefore achievable and
is not set where achievability is in doubt.

The bar is set at A0 and not at the 14/17 rubric threshold deliberately. E002
was killed against a 13/17 hurdle imported from a 60,285-character payload and a
superseded accounting regime, and its post-hoc interpretation records that it
improved its exact-budget baseline by 66.7 percent while remaining KILL. A0 is
the committed same-regime baseline and is the correct test of whether this
mechanism does anything.

### Registered secondary reference points

Reported, never kill thresholds: E002's best **10/17**; the rubric threshold
**14/17**; the carried oracle **15/17 at 5,455 characters**; AR-001's exact
frontier **17/17 at 7,592 characters**.

## Gates

**Primary gate:** at least one arm and configuration makes at least 7/17 Q11
atomic items available at 32,000 characters.

**No-regression gate:** the same configuration, applied unchanged to every
targeted probe, preserves every targeted item whose committed corrected-T6
availability is `True`. Items previously unavailable may improve and do not
count against the gate. **Per-probe reporting is mandatory; an aggregate is not
sufficient.**

A diversity penalty is actively dangerous on targeted queries, where the correct
answer may be several near-identical episodes about one fact and MMR's penalty
suppresses exactly that. An arm that improves breadth while degrading targeted
recall is not a win and must not be promoted.

**Surrogate gate:** the primary configuration must cover all four Q11 domains
and the report must expose per-domain counts for every arm and configuration.
A selector that raises the total while still dropping a domain has not solved
breadth.

**Outcome:**

- `KILL` if no configuration reaches 7/17.
- `REJECT_NO_REGRESSION` if one reaches 7/17 but none also passes the targeted
  no-regression gate.
- `PROMOTION_ELIGIBLE` if one configuration passes all three gates.

## Mandatory Diagnostics

Reported for every arm and configuration, not only the winner.

1. **Per-domain fact counts.** AR-001 domain minima: civil 826, art 3,182,
   monetary 2,913, marine 824 characters. E002's best reached 3/4 domains.
2. **Characters spent against facts delivered**, along the whole greedy prefix,
   plus facts-per-character at the final selection. The oracle's ratio is 15
   facts in 5,455 characters.
3. **Prior-answer fraction.** The fraction of selected episodes whose source
   turn is a prior probe turn rather than a raw content turn. Four of AR-001's
   five optimum episodes are prior probe answers. Study 004's error-cascade
   dynamic is the hazard: preferring prior answers propagates prior errors, and
   Q11's prior answers were largely wrong.
4. **Data-dependent optimality ratio** for the arms with a submodular objective,
   A2 and A3, reported alongside the worst-case constant. At the final greedy
   set `S`, compute each unselected candidate's marginal gain and additive cost,
   sort by gain per unit cost, fractionally fill the remaining budget, and add
   that to `f(S)` for an upper bound on the optimum; the ratio is `f(S)` over
   that bound. A1 has no set function, so its ratio is reported as not
   computable, which is itself the observation owed by the deliverable below.
5. **Selection overlap with the carried oracle set.** Which of AR-001's five
   episodes each configuration found and which it missed, by episode ID. This
   distinguishes closeness to the oracle from a coincidentally similar score.

## Surrogate Audit

> Can each check pass while the property it certifies is false?

| Check | Certifies | Can it pass falsely | Mitigation |
|---|---|---|---|
| Diversity objective improved | more facts covered | **Yes, the central risk.** Dissimilarity is a surrogate for informational novelty; chit-chat is maximally dissimilar from a technical turn and factually empty. Precedent: density was a surrogate for factual content and ranked the six hard plants 89th to 316th | Score on fact count only, never on the diversity objective. The objective is the mechanism; facts are the measurement |
| Total facts increased | breadth solved | Yes, by concentrating in cheap domains | Per-domain counts mandatory |
| Arm beats A0 | selector is better | Yes, if it spent more characters | Facts-per-character reported; both enforced at the same budget |
| Fact count above the oracle | approximation is excellent | See the registered correction above: above 15/17 is admissible, above 17/17 is a bug signal | Recount every configuration's items from its own serialized payload, never from unioned per-episode masks |
| Targeted unchanged in aggregate | no regression | Yes, aggregates hide per-probe swings | Per-probe reporting, binding |
| Pool is representative | ceiling is set by the selector | Yes, a pre-filtered pool can exclude the optimum before any selector runs | Primary pool is unrestricted; both restricted pools reported as secondaries |

**Accepted residual:** every arm is evaluated on one breadth probe, Q11, against
one store. Q11 is the program's only breadth probe. **No arm may claim general
breadth capability from this result, and that limitation must be stated wherever
the number is cited.**

## Measurement Boundary

Mechanism code may read only the query text, eligible episode identities,
episode content, stored embeddings, budget, and configuration. It must reject
paths and imports containing `q_facts_key`, `rubric`, `atomic_items`, or
`targeted_items`, enforced by grep, an import-graph audit, and a planted
violation.

A separate analysis layer may read the committed measurement artifacts
`analysis_corrected_121/breadth_fact_delivery.csv` and
`analysis_corrected_121/targeted_fact_delivery.csv`. The mechanism must write
selected IDs, source turns, domains, per-step gains, costs, and exact serialized
cost before the analysis layer counts any fact.

A4 is the only arm permitted to depend on the fact key, it is carried as a
committed constant rather than re-derived, and it is not deployable.

## Selection And Tie-Breaks

Fixed before any E005 output. Among configurations passing all gates, choose the
primary by:

1. highest Q11 atomic availability;
2. highest Q11 domain count;
3. highest number of committed targeted items preserved;
4. fewest serialized characters;
5. fewest selected episodes;
6. arm order A1, then A2, then A3;
7. lowest `lambda`;
8. lowest `r`;
9. lowest `k`.

If no configuration passes, the same ordering without the failed gate fields
identifies the descriptive best row.

## Integrity Requirements

- This design anchor is committed before any implementation file; its SHA is the
  integrity anchor and is recorded in the result artifact.
- Kill condition, gates, and diagnostics are committed before any result is
  opened.
- Mechanism seal over the corrected Tier 6 run must pass before analysis.
- Leakage audit with a planted forbidden-path violation.
- Source integrity: all inputs hashed before and after execution.
- Determinism: byte-identical raw rerun of every selection record.
- Additive serialized cost must reproduce the exact rendered payload length for
  every recorded selection.
- Full test suite green.
- One PR, updating `README.md`, the `AGENTS.md` digest, and the ledger together.
- `ERRATA.md` if any committed number changes.

## Required Artifacts

- `artifacts/e005/E005_report.md`
- `artifacts/e005/e005_results.json`
- `artifacts/e005/configuration_sweep.csv` - every arm and configuration
- `artifacts/e005/per_domain_counts.csv`
- `artifacts/e005/selection_prefix.csv` - facts against characters, per step
- `artifacts/e005/oracle_overlap.csv`
- `artifacts/e005/prior_answer_fraction.csv`
- `artifacts/e005/optimality_bounds.csv`
- `artifacts/e005/targeted_no_regression.csv` - per probe, per configuration
- `artifacts/e005/pool_secondaries.csv`
- `artifacts/e005/primary_payload.txt`
- `artifacts/e005/q11_item_matrix.csv`
- `artifacts/e005/a0_baseline.json`
- `artifacts/e005/raw/*.jsonl` and byte-identical rerun counterparts
- `artifacts/e005/determinism.json`, `source_integrity.json`,
  `leakage_audit.json`, `artifact_manifest.json`

## Deliverable Owed To The Scan

The parent scan recorded, unverified, that MMR's objective lacks the
submodularity that buys the greedy guarantees. **That claim was not confirmed
from a primary source and must not be stated as established anywhere on the
strength of this protocol.** It is verified against Lin and Bilmes (2011)
primary text and the finding recorded in the E005 report before the ledger entry
closes.

All artifacts are availability measurements. They make no answer-correctness
claim and authorize no inference run.
