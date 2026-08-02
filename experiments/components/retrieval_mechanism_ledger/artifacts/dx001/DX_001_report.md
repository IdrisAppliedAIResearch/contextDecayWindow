# DX-001 Part 1 - Turn-90 Selection Miss

**Registration commit:** `a30d3bcca53248fe75b7901c2ff74a8aa28f5e1a`
**Frozen configuration:** `A3_l0.1_r0.0_k16`, pool 119, budget 32,000
**Verdict:** **M2+M3+M4**

Offline. No inference, no new study run. Every derived number is
recomputed from committed E005 inputs behind a replay gate that
reproduced 146 of 146 committed payload hashes
byte-for-byte before any of it was reported.

**The gate earned its place.** The first attempt embedded the Q11 query on its own instead of in E005's nine-query batch. The returned vector is not the same one: cosine agreement 0.999837, largest component difference 0.217, and it flips 6 of 146 committed payloads. The cause is not established here and no claim is made about it; what is established is that reproducing E005 requires reproducing the embedding call shape, not only the query text. Everything below uses the committed batched call.

## 0. The target

- Turn 90, id `1dec9c9e-b948-4ef8-9eaa-aa889c083470`
- Cosine rank **112/119**, cosine 0.0560
- Serialized cost **2,862 chars**, carrying **4 Q11 items**: monetary:Taylor Rule, monetary:Federal Reserve, monetary:Dr. Priya Mehta, monetary:2.3%
- Oracle episode: True

## D.2.1 Selection census - run first

Configurations examined: **146**. Configurations that selected turn 90: **0**.

**No configuration in the registered parameter space selected it.**
The objective is structurally blind to this episode across the
entire space explored, not unlucky in one cell.

## D.2.2 Cluster assignment

| k | Target cluster | Size | Alone? | First occupant turn | Step | Its Q11 facts |
|---:|---:|---:|---|---:|---:|---:|
| 2 | 1 | 78 | False | 78 | 4 | 0 |
| 4 | 2 | 58 | False | 98 | 8 | 0 |
| 8 | 2 | 57 | False | 43 | 2 | 0 |
| 16 | 12 | 20 | False | None | None | None |

Collision at every k: **True**. Collision at the primary k=16: **True**.

## D.2.3 Cost

- Target: **2,862 chars**, 715.5 chars per Q11 fact
- Selected episodes: min 358, median 897, max 5,473
- Fact-bearing selections, median chars per fact: 497.0
- Target cheaper than the median selected episode: **False**

## D.2.4 Greedy trace

- Steps: 15
- Target affordable at steps: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
- Best rank among affordable candidates: **27**
- Smallest gap to the step winner: **0.169042**
- Relevance term max(cos, 0) = **0.05599**; lambda term = **0.1**
- Steps where the target's cluster was still novel: [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15]
- Counterfactual with the diversity term paid in full ever wins: **False**

The gap, not the rank, is the deciding quantity; both are recorded in
`greedy_trace.csv`.

## D.2.5 Sensitivity across lambda, r and k

- A3 configurations walked: 132
- Selected the target anywhere: 0
- Best rank achieved anywhere: **4** at `A3_l1.0_r1.0_k16`
- Best rank by r: {"0.0": 16, "0.5": 8, "1.0": 4}
- Best rank by k: {"16": 4, "2": 7, "4": 10, "8": 10}
- Best rank by lambda: {"0.0": 10, "0.1": 10, "0.2": 10, "0.3": 9, "0.4": 9, "0.5": 8, "0.6": 6, "0.7": 7, "0.8": 7, "0.9": 5, "1.0": 4}

## D.2.6 Termination cause (M4 check)

- Spent 31,569 of 32,000; **431 chars remained**
- Unselected candidates: 104, of which affordable at termination: 0
- Cheapest unselected episode: 1,439 chars
- Terminated on: **budget**

## D.3 Mechanism attribution

| Mechanism | Fires | Evidence |
|---|---|---|
| M1 cluster collision | **False** | target shares its k=16 cluster with 19 other episodes, but the diversity term went unpaid at 0 of 15 steps |
| M2 cost discount | **True** | best rank by r: {"0.0": 16, "0.5": 8, "1.0": 4} |
| M3 relevance floor | **True** | relevance term 0.05599 against lambda term 0.1; counterfactual with novelty paid in full wins at no step |
| M4 budget exhaustion | **True** | terminated on budget with 431 chars left and 0 affordable unselected candidates |

**Attribution: M2+M3+M4.**

### D.3.1 Reading

- The diversity term was payable in full at every step: **True**. The target's cluster was never occupied by a selection, so M1 is refuted twice over: the collision exists in the partition and costs nothing in the objective.
- To win at its best step the target needed relevance **0.225032**; it has **0.05599**, a shortfall of **0.169042**. **20** of the 119 episodes clear that bar, so the target would have to be a different episode by cosine, not a better-weighted one.
- Best rank reached anywhere in 132 A3 walks: **4**. Never 1, in any cell.

**Registered F.8 predictions, checked:**

- *M1 cluster collision is the most likely mechanism* - **WRONG**. M1 does not fire.
- *No configuration selected turn 90* - **held**.

**F.6 determination: fires = True; Part 2 outcome = NO_CHANGE_ESCALATE.**

## D.4 Surrogate audit as executed

- Rank alone is not reported as evidence; the marginal-gain gap at the
  deciding step accompanies every rank claim.
- Any configuration selecting the target carries its full result
  vector in the census table above.
- M1 and M3 were tested jointly: the counterfactual pays the diversity
  term in full and asks whether the target would then win.
- A cause is not a remedy. Part 2 remains conditional.

## Boundary

One episode, one probe, one store. Availability only. No
answer-correctness claim and no live run is authorized by this
diagnostic.
