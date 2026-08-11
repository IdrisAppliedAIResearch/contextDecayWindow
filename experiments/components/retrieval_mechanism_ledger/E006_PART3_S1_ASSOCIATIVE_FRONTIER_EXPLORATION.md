# E006 Part 3 - Query-Anchored Associative-Frontier Exploration Protocol

**Type:** Pre-registered exploration protocol and candidate mechanism specification
**Identifier:** E006 Part 3 (`E006-P3`)
**Branch:** `study/e006-p3-query-anchored-associative-frontier-retrieval`
**Status:** PRE-REGISTERED - PART 1 AUTHORIZATION MUST FOLLOW THIS DESIGN ANCHOR
**Implementation:** EXPLORATION-ONLY PROTOTYPE AFTER STANDALONE AUTHORIZATION; EVIDENCE PROHIBITED
**Calls:** none authorized
**Outcome ceiling:** `CHARACTERIZED`, regardless of result
**Primary prior:** `E006_PART2_REV5_REPORT.md`
**Historical prior:** `experiments/surveys/retrieval_bakeoff/tier4/tier4a_report.md`

This document fixes the proposed comparison, records the author's parameter
resolutions, and limits the claims that the diagnostic may make. Preflight Part
1 can still expose a structural blocker, but it may not tune these settings
against Q11 facts. Any change after exploration requires a new reviewed revision
and authorization before evidence implementation.

---

## 1. Question

E006 Part 2 raised Q11 packed availability from `3/17` at `D=0` to `9/17` at
`D=2`, but its best cells considered 15-20 candidates and packed 12 episodes.
It therefore did not distinguish a better chained cue from a larger delivered
volume. It also averaged retrieved episodes into one context vector, which can
blur distinct local bridges.

This diagnostic asks:

> At an equal candidate quota and under the same exact packer, does local
> episode-to-episode frontier propagation recover more Q11 facts than both a
> fixed-query deeper scan and E006's mean-context chain?

The single proposed new component is the **query-anchored associative-frontier
propagation operator**. The episode store, Q11 trace, Gram matrix, eligibility,
content-hash identity, and exact packing path are carried unchanged.

This is offline availability measurement, not an answer-correctness test.

---

## 2. Historical boundary: Tier 4A

The retrieval bakeoff's Tier 4A failed its advancement gate: no explicit graph
configuration beat its flat baseline without a greater-than-10% regression on
another query class. That negative result is a binding prior, not background to
omit.

The proposed work must not be described merely as "Gram-derived kNN rather
than observed co-retrieval." Tier 4A included all of the following:

- E2 edges from observed co-retrieval.
- E3 edges from exact episode cosine: undirected top-8 neighbors, negative
  weights clamped to zero, and asymmetric selections unioned.
- E3-only traversal at depths 1, 2, and 3.
- Truncated personalized PageRank with `0.15 * seed + 0.85 * P^T * activation`.

All E3-only rows failed advancement. Depths 2 and 3 improved chained recall but
regressed enumeration, so Tier 4A closed before Tier 4B.

The proposed mechanism is therefore **not a first test of a cosine kNN graph**.
Its potentially distinct operation is narrower: only the newly retrieved hop
forms the next frontier; unseen candidates receive a local frontier score; a
direct query term remains in every hop; exactly `m` unseen episodes are admitted
per hop; and the cumulative candidates pass through E006's exact rank-and-pack
path. It does not diffuse a probability distribution over the full graph.

The eventual ledger entry must say:

> Tier 4A already refuted advancement for global PPR traversal over observed
> co-activation edges and an exact-cosine top-8 graph. This diagnostic does not
> reopen that result. It tests a different propagation operator over the same
> broad cosine-graph family, with a matched-volume fixed-query control and the
> E006 exact packing path. Any result remains `CHARACTERIZED`.

**Blocking identity condition:** if exploration shows the proposed arm reduces
to Tier 4A E3 traversal, or differs only by a relabeling or monotone score
transform, stop. A repeated negative arm is not a new mechanism.

---

## 3. Three-arm comparison

All arms use the same eligible 119 Q11 episodes, original query cosine vector
`Q`, content hashes, depth `D`, per-hop quota `m`, total candidate quota
`m * (D + 1)`, 32,000-character ceiling, deterministic tie-break, and
authoritative compact-XML packer. Seen candidates are excluded from later hops.

| Arm | Operation | Purpose |
|---|---|---|
| A0 | Fixed-query deeper scan: select the next `m` unseen episodes by original `Q` at every hop | Matched-volume control; isolates gain from scanning farther down the original ranking |
| A1 | E006 Rev 5 mean-context chain, unchanged | Carried chained control; measures the existing global-centroid cue at the same volume |
| A2 | Query-anchored associative-frontier chain | Proposed local propagation operator |

X0 (`6/17`, 8 episodes, 31,946 characters) and E005 (`12/17`) remain descriptive
historical references. They are not equal-volume arms and cannot establish the
new mechanism's ranking quality.

### 3.1 Proposed A2 operation

The following is a review-level skeleton, not executable pseudocode:

```text
graph = build_knn_graph(G, K_GRAPH, EDGE_POLICY, SYMMETRY_POLICY)
seen = {}
frontier = top_m(Q, exclude=seen)

for hop in 0..D:
    if hop > 0:
        association_i = FRONTIER_AGGREGATE(
            graph_weight(h, i) for h in frontier
        )
        score_i = QUERY_ANCHOR * Q_i + ASSOCIATION_WEIGHT * association_i
        frontier = top_m(score, exclude=seen)
    seen |= frontier

return pack(rank(seen, final_score), 32_000)
```

Section 3.2 fixes nodes without a frontier edge at association `0`, leaving them
rankable through the query term so A2 still admits exactly `m` unseen candidates
at every hop. Any fallback that changes candidate count would break the
matched-volume comparison and requires a new reviewed revision.

### 3.2 Author resolutions

These choices are fixed for review. Their provenance is carried design rather
than an exploratory search over Q11 outcomes.

| Decision | Resolution | Rationale |
|---|---|---|
| `K_GRAPH` | `8` | Carries Tier 4A E3 exactly; avoids choosing a new graph width after seeing E006 |
| kNN topology | Undirected union of directed top-8 selections | Carries Tier 4A E3; retain an edge selected in either direction |
| Edge weights | `max(cosine, 0)`; union duplicates retain the larger weight | Carries Tier 4A E3 and prevents negative association from being mislabeled as activation |
| `FRONTIER_AGGREGATE` | Maximum retained edge weight from any episode in the immediately previous frontier | Tests a local bridge without mean dilution or degree-weighted sum inflation |
| Query/association weights | `QUERY_ANCHOR = 0.3`, `ASSOCIATION_WEIGHT = 0.7`; direct convex sum, no additional normalization | Carries E006's strongest registered query-anchor setting and keeps both cosine terms on their native scale |
| A1 context update | `RHO = 0.5`, `BETA = 0.5` | Carries the E006 configuration that reached 9/17 at the primary cell |
| No-edge fallback | Association is `0`; all unseen nodes remain rankable through `0.3 * Q_i` | Preserves the exact per-hop quota without injecting a separate retrieval method |
| Tie behavior | Descending arm score, then descending original `Q`, then ascending content SHA-256 | Deterministic and independent of generated IDs, paths, and labels |
| `D` grid | `{0, 1, 2, 3}` | Carries E006 unchanged |
| `m` grid | `{3, 5}` | Carries E006 unchanged |
| Primary cell | `D = 2`, `m = 5` | Directly retests E006's first 9/17 plateau at 15 equal candidates; all other cells are secondary |
| Final cumulative ranking | Native final arm score: A0 uses `Q`; A1 uses its final E006 cue; A2 uses the score that selects the final frontier | Preserves each end-to-end mechanism; exact characters expose ranking-induced packing differences |

For A2 at hop `d > 0`:

```text
association_i = max({edge_weight(h, i) for h in frontier_(d-1)} or {0})
score_i = 0.3 * Q_i + 0.7 * association_i
```

At `D=0`, all three arms rank by `Q`. At `D>0`, A2's final cumulative ranking
uses the score computed from frontier `D-1` to select frontier `D`; it does not
recompute against the just-selected final frontier. Self-edges are absent. PF1
must confirm that eligible content hashes are unique; duplicates fail before
ranking rather than falling through to an unstable tie-break.

The inherited grid contains exactly 24 arm cells: eight A0, eight A1, and eight
A2. The primary interpretation uses only the three `D=2, m=5` cells. Secondary
cells report the depth and quota distributions but cannot rescue a failed
primary comparison.

No parameter may be changed by looking at new Q11 fact counts, domain counts,
or the fact key. Exploration may characterize score and graph distributions
without opening outcome labels.

---

## 4. Measurements

Every cell in every arm must report all of the following before interpretation:

- Candidate count before packing.
- Candidate serialized characters before packing, both in candidate rank order
  and as the sum of individually rendered episode costs.
- Selected episode count after packing.
- Exact delivered characters after packing.
- Skipped episode count and skipped characters.
- Q11 facts available before packing and after packing.
- Facts by all four domains, not only the total.
- Facts per candidate, facts per selected episode, and facts per 10,000 delivered
  characters as descriptive diagnostics, never as substitute outcomes.
- Candidate, selected-sequence, and payload SHA-256 values.
- Per-hop selected content hashes, scores, source turns, and graph predecessors.
- Pairwise arm overlap for candidates and packed episodes.

Candidate count equality is necessary but insufficient. Equal-volume arms can
deliver different characters because candidate lengths and packing order differ.
A packed-fact gain accompanied by greater delivered characters is consistent
with a residual volume effect and must be labeled that way.

The primary contrast is A2 against both A0 and A1 at the same registered cell.
No comparison to X0 may be worded as evidence of better ranking.

### 4.1 Diagnostic rule and thresholds

Integrity and Preflight failures stop before fact measurement. In particular,
every arm must admit exactly 15 unique candidates at the primary `D=2, m=5`
cell. A quota mismatch invalidates the comparison; it is not a null result.

At the primary cell, define two ordered thresholds:

**Candidate-cue threshold (`CUE_DIFFERENTIATED`):** A2 must contain at least one
more candidate-set fact than A0 and at least one more than A1. A2 must also be
no lower than either control in each of the four domain fact counts. Candidate
count is fixed at 15 for all arms.

**Packed-delivery threshold (`DELIVERY_DIFFERENTIATED`):** A2 must contain at
least one more packed fact than A0 and at least one more than A1, be no lower
than either control in every domain, and deliver no more exact characters than
either control. This is deliberately stricter than equal candidate count.

Disposition is mechanical:

| Primary result | Disposition |
|---|---|
| Candidate-cue threshold fails | `NO_DIFFERENTIATED_CUE` |
| Candidate-cue passes; packed gain is absent | `REACH_ONLY_NOT_DELIVERED` |
| Packed facts improve but A2 delivers more characters than either control | `VOLUME_CONSISTENT_PACKED_GAIN` |
| Both thresholds pass | `DIFFERENTIATED_OFFLINE_DELIVERY` |

The full inherited grid is always reported if the run is valid, but no
secondary cell changes the primary disposition. After that disposition is
recorded, stop: no targeted inference, live run, adoption, or promotion follows
from any row.

### 4.2 Registered predictions

These predictions are fixed before exploration outcomes are opened:

1. PF6 reproduces Tier 4A E3 and E006 A1 by identity and digest. At the primary
   A1 cell it reproduces 15 candidates, 12 selected episodes, 28,562 exact
   characters, and `9/17` packed facts.
2. A0, A1, and A2 each admit exactly 15 unique candidates at the primary cell,
   while their selected episode counts or delivered characters differ.
3. A2 passes `CUE_DIFFERENTIATED` at the primary cell because a strongest-edge
   frontier preserves a local bridge that A0's static ranking and A1's global
   hit centroid suppress.
4. A2 does not pass `DELIVERY_DIFFERENTIATED`; packing removes the candidate
   gain or the packed gain requires more delivered characters.
5. A2 retrieves zero art facts after packing at every cell. The static cosine
   graph does not overcome the corpus geometry documented by DR-002 and E006.
6. No A2 cell exceeds E005's historical `12/17` packed availability.
7. A2's best packed fact count plateaus by `D=2`; `D=3` adds candidates but no
   more than one packed fact relative to the matched `D=2` cell.
8. The equal-candidate comparison still produces unequal exact characters in
   at least four of the six `D>0` matched arm triplets.

Predictions 3 and 4 are the mechanism claims. Predictions 5-8 characterize the
expected residual boundary. A wrong prediction changes the report, never the
threshold or grid.

---

## 5. Mandatory Preflight

No implementation or evidence run begins before this protocol is committed and
its Part 1 authorization is recorded in a standalone file. Preflight has two
ordered parts, and its findings may require a new reviewed revision before the
final evidence design is locked.

### Part 1 - Exploration

Exploration must use committed inputs without reading Q11 labels or facts and
must produce committed machine-readable artifacts for:

1. One falsifiable behavioral-identity sentence for A0, A1, A2, the graph,
   frontier, candidate quota, final ranking, and packer.
2. Full graph distributions: degree, retained edge weight, connected component,
   reciprocal-edge, and isolated-node distributions for every proposed graph
   policy.
3. Full per-hop score, frontier-neighbor, candidate source-turn, overlap, and
   serialized-character distributions for all three arms.
4. Mechanical degenerate-state traces: empty frontier adjacency, all-zero or
   all-negative association, repeated frontier, graph cycle, query-only
   fallback, constant ranking, and exhausted unseen candidates.
5. Tier 4A non-identity: construction inputs, edge semantics, propagation
   recurrence, rankings, and output digests compared directly with Tier 4A E3.
6. A1 reproduction of E006 Rev 5 by candidate sequence and payload digest before
   any A2 output is opened.

Exploration may cause the author to change the draft. It may not tune against
facts, domain labels, or packed availability.

### Part 2 - PF1-PF10

| Check | Required artifact-level answer |
|---|---|
| PF1 | Hash and count every Q11 cosine, vector/Gram, episode, packer, Tier 4A, and E006 reproduction input; record the absent targeted traces |
| PF2 | Execute every named component on committed data and prove A2 is not Tier 4A E3 or A1 under another name |
| PF3 | Assert git order: authorized exploration protocol, exploration-only prototype and artifacts, final reviewed design, standalone authorization, evidence implementation, checklist completion, parameter lock, then results |
| PF4 | Establish attainable candidate quotas and attainable comparative rules before labels are opened; unreachable rules block lock |
| PF5 | Use canonical content SHA-256 values for all equality, exclusion, overlap, and tie checks |
| PF6 | Reproduce Tier 4A E3's relevant committed output and E006 A1's committed candidate and payload identities before A2 runs |
| PF7 | On the full intended Q11 depth trace, prove whether feedback cycles, repeated frontiers, fallback absorption, or constant rankings occur; do not infer this from code |
| PF8 | State that one offline Q11 probe can detect only depth-local behavior, not cross-turn persistence, targeted regressions, or live answer variance |
| PF9 | Commit the surrogate audit below with one row per gate and metric |
| PF10 | State the unavailable targeted and live checks; availability is not an answer verdict |

Any failed identity, reproduction, quota, leakage, or ordering check stops before
fact measurement.

---

## 6. Surrogate audit

| Observation or check | False property it could appear to certify | Required interpretation |
|---|---|---|
| A2 packs more facts | Better associative cue | Not demonstrated if A2 delivers more characters or episodes |
| All arms admit the same candidate count | Equal delivered volume | False unless selected episodes and exact characters are also comparable |
| A2 reaches more candidate facts | Better final payload | Packing may discard the gained episodes |
| A2 beats A0 | Graph structure is the cause | Could reflect final-score ordering or fallback; report both separately |
| A2 beats A1 | Local association is generally superior | One known Q11 trace cannot establish generality |
| A2 reaches four domains | Targeted safety | Domain breadth is not targeted no-regression |
| No repeated frontier | No absorbing behavior | A constant ranking or query-only fallback can still absorb |
| Gram-kNN differs from E2 | New graph mechanism | Tier 4A already tested E3 cosine kNN; novelty, if any, is propagation |
| More art facts | Corpus geometry solved | One post-result mechanism on the known art miss is diagnostic only |
| Deterministic offline replay | Answer improvement | LV-001 established that availability is not the answer |

Accepted residuals are one probe, one corpus, post-result mechanism design, no
variance estimate, no targeted traces, no answer generation, and no deployment
test.

---

## 7. Leakage and scope

Graph construction, A0-A2 retrieval, ranking, fallback, exclusion, and packing
must not import, read, or depend on `q_facts_key.md`, rubrics, domain labels, or
measurement outputs. Fact measurement begins only after immutable candidate,
selection, and payload digests exist. Grep, import-graph, and planted-violation
tests are binding.

Only one new component is allowed: A2 frontier propagation. The following are
out of scope:

- E005 diversity selection or any hybrid selector.
- Stateful retrieval suppression, read-writes, replay, consolidation, or
  retroactive salience from the hypothetical biological architecture.
- New embeddings, formation, segmentation, storage, packing, or live prompts.
- Targeted no-regression claims without the missing committed cosine traces.
- Promotion, adoption, production changes, or a live run.

The hypothetical biological architecture is motivation only and is not an
execution input or authority. This draft adopts only its separation between
query seeding and propagation over stored episode relations.

---

## 8. Interpretation ceiling

The strongest permitted positive statement is:

> On the committed Q11 offline trace, query-anchored local frontier propagation
> delivered more facts than both equal-candidate controls after exact packing,
> with the accompanying candidate, episode, and character differences reported.

The strongest permitted null statement is:

> Under the registered Q11 diagnostic, local frontier propagation did not
> separate from fixed-query depth or E006 mean-context chaining once candidate
> and delivered volume were exposed.

Neither statement establishes answer quality, targeted no-regression,
cross-query generality, or superiority to E005. E005's `12/17` remains the
leading historical Q11 result unless a later authorized design establishes
otherwise on comparable controls.

**Ceiling: `CHARACTERIZED` regardless of outcome.** The eight targeted probes
have no committed full cosine traces, so the caveat survives all three arms.

---

## 9. Review checklist

- [x] Identifier assigned as E006 Part 3.
- [x] Author approved the Section 3.2 resolutions before exploration.
- [x] Author approved the Section 4.1 rules and Section 4.2 predictions
  before exploration.
- [x] Dedicated E006-P3 branch exists.
- [ ] Preflight Part 1 receives its own protocol anchor and authorization before
  an exploration-only prototype is written or run.
- [ ] Exploration artifacts are committed and reviewed before the final evidence
  design is locked.
- [ ] Any structural change forced by exploration is recorded in a new review
  revision; outcome-driven tuning is prohibited.
- [ ] Final spec receives explicit standalone authorization.
- [ ] Only then may evidence implementation begin.

---

*Pre-registered August 10, 2026 from the author's revised design and instruction
to handle Preflight and any structurally required revisions. This document
authorizes no implementation or outcome by itself; standalone authorization
must bind the committed protocol before Part 1 begins.*
