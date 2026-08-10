# E006 Part 2 — Retrieved-Context Chained Retrieval (Rev 4, superseding)

**Type:** Mechanism specification. Repair of a failed PF11 gate.
**Repository:** `contextDecayWindow` · `experiments/components/retrieval_mechanism_ledger/`
**Branch:** `e006-p2-chained-retrieval`
**Supersedes:** Rev 3, design anchor `42f710a3`, SHA-256 `1A41013C…D24B325` — withdrawn for the §2 defect
**Status:** DRAFT — **UNAUTHORIZED.** Requires new authorization; Rev 3's does not carry
**PF11 of record:** FAIL, auditor commit `960c9810`, artifact `57448B3E…1E8CA3B`
**Companions:** `RETRIEVAL_MECHANISM_LEDGER.md` · `PREFLIGHT.md` · `LITERATURE_LANDSCAPE.md`

---

## 0. What changed, and what did not

**Rev 3 failed at its first gate.** PF11 compared the registered §2 derivation against an independent vector route: **0/12 cells agreed on score, 0/12 on full ranking, and 3/12 selected a different next hit set**, with score differences of 0.040 to 0.212.

**Only §2 changes in Rev 4.** Every other section is carried from Rev 3 unaltered: the D1 and D2 repairs, Q11 scoping, the CHARACTERIZED ceiling, the 48-cell grid, PF7's absorbing-state proof, and PF11 itself.

**PF11 is unchanged and remains the first gate.** It just demonstrated that it works, at the moment it was least convenient. It does not get relaxed because it fired.

### 0.1 What PF11 established beyond the failure

Two findings that survive and are load-bearing for Rev 4:

1. **The query vector is recoverable from committed cosines.** The auditor reconstructed a unit query in an augmented 1,025-dimensional space matching every committed Q11 cosine to a maximum absolute error of **9.96e-15**, with the projection onto the episode span carrying squared norm 0.6151 and the orthogonal residual 0.3849. **D3's blocker is genuinely dissolved** — zero-call chained retrieval on Q11 is computable. Rev 3's equations were the only thing wrong.
2. **The corrected recurrence agrees with the vector route to 9.49e-15 across all 12 cells, with identical full rankings.** It was recorded as a **non-gating diagnostic** and explicitly not used to pass PF11.

**That restraint is the reason Rev 4 exists as a registered document rather than a patch.** Continuing on the corrected recurrence after observing the gate result would have been repairing a locked derivation post hoc — the failure class this program has named and instantiated before.

---

## 1. The defect

**Rev 3 §2 dropped the recursion.**

Rev 3 §5.1 defines the context update as a running blend:

```
c ← normalize(RHO * c + BETA * mean(ê for ê in hits))
```

Rev 3 §2 then computed `c` as **the mean of the current hit set alone**, discarding the prior `c`. The resulting score equation carried `W_Q` and `W_C` and **omitted `RHO` and `BETA` entirely** — the two parameters that distinguish chaining from repeated single-shot retrieval.

**Not a notation difference.** A chain whose context is the latest hit mean is memoryless; the registered mechanism's context accumulates. PF11's numbers are what that gap looks like.

**Author's error, recorded as such**, alongside D1 in Rev 3 §1.1. Both were controls or derivations asserting properties the mechanism's own locked rule forbids.

---

## 2. Corrected derivation — recursive Gram formulation

> **Derived from §5.1's rule by direct substitution, shown rather than asserted.** Rev 3's §2 was stated as a result; this section shows the steps, because an unshown derivation is what failed.

### 2.1 Available quantities

- **Committed:** `cos(q0, e_i)` for all 119 eligible episodes — Q11's full trace.
- **Computable, zero calls:** `G_ij = cos(e_i, e_j)`, the 119×119 Gram matrix over normalized committed episode vectors.

### 2.2 What must be tracked

The chain's state is `c`. Rather than materializing `c` as a vector, track two **projections** of it, both of which are all that any score requires:

- `S_i ≡ ĉ · ê_i` for every episode `i` — the context's score against each episode.
- `P ≡ q̂0 · ĉ` — the context's alignment with the original query.

### 2.3 Initialization

At step 0, `c = q0`, therefore:

```
S_i ← cos(q0, e_i)          # committed trace
P   ← 1
```

### 2.4 Step recurrence

Given hit set `H` from the current step, let `μ` be the mean of the unit hit vectors. Its projections come straight from committed data:

```
μ · ê_i = mean_{h∈H} G_{h,i}                 # Gram matrix
q̂0 · μ  = mean_{h∈H} cos(q0, e_h)            # committed trace
```

Substituting the unnormalized update `c' = RHO * c + BETA * μ` and using linearity of the inner product:

```
S'_i(unnorm) = RHO * S_i + BETA * (μ · ê_i)
P'(unnorm)   = RHO * P   + BETA * (q̂0 · μ)
```

Normalizing `c'` divides both by `|c'|`, which is identical across all `i` and therefore computable as a single scalar:

```
|c'| = sqrt( RHO² + BETA² + 2*RHO*BETA*(ĉ · μ) )
     where  ĉ · μ = mean_{h∈H} S_h              # already tracked
```

Then:

```
S_i ← S'_i(unnorm) / |c'|
P   ← P'(unnorm)   / |c'|
```

**`RHO` and `BETA` appear in the recurrence, which is what Rev 3 lost.**

### 2.5 Scoring

```
score(e_i) = ( W_Q * cos(q0, e_i) + W_C * S_i )
             / sqrt( W_Q² + W_C² + 2*W_Q*W_C*P )
```

The denominator is constant across `i`, so it does not affect ranking — but it is computed anyway, because the absolute score is reported and any thresholded variant would need it.

### 2.6 Status of this derivation

**PF11's diagnostic already matched this formulation to the vector route at 9.49e-15 across all 12 cells with identical rankings.** That is encouraging and **is not a pass.** It was computed by the auditor as a diagnostic, not against a registered equation, and Rev 4 registers the equation now so PF11 can test it properly.

**PF11 runs again, unchanged, as Rev 4's first gate.** A derivation that has already matched once is exactly the kind this program has been wrong about before.

---

## 3. Carried unchanged from Rev 3

Restated in brief; Rev 3's text governs.

- **D1 repair.** X1 is `D = 0`, not `BETA = 0`. The inclusive loop at `D = 0` runs one step and retrieves exactly `m` — single-shot `top_m`, the chain's true degeneracy.
- **D2 repair.** X0 is a **reference**, not an identity target. Deployed X0 is thresholded K plus N-first packing over a least-recently-delivered rotation; the chain is `top_m` over an exclusion set. No parameterization bridges them. The study asks whether chaining improves single-shot `top_m`, with X0 as comparison. **This must be stated in any report.**
- **Scope: Q11 only.** The eight targeted probes have no committed cosine traces, so **no no-regression arm is possible.** Ceiling on any outcome is **CHARACTERIZED** — no promotion, no adoption.
- **Grid:** `D` ∈ {0,1,2,3}, `m` ∈ {3,5}, `W_Q` ∈ {0.3,0.5,0.7} with `W_C = 1−W_Q`, `RHO` ∈ {0.5,0.7} with `BETA = 1−RHO`. **48 cells, none added after results.**
- **PF7 absorbing-state proof**, now executable via §2: no repeated retrieved set, no fixed point, per-step novelty > 0, on a real trace, all cells.
- **Kill:** no chained arm exceeds X0's committed Q11 availability at any registered cell.
- **Reference points, not thresholds:** E002 10/17 against a 6/17 baseline, killed on its own bar; E005 12/17; AR-001 oracle 15/17 at 5,455 characters.
- **Rejected:** authorizing embedding calls to reconstruct `q0`. The H1 call-shape hazard means a reconstructed vector would not be the one the live run used. **PF11 §2 confirms this rejection was unnecessary as well as unsound** — the vector is recoverable from committed cosines.

---

## 4. Preflight — order unchanged

**PF11 first. All other items follow only if it passes.**

| # | Requirement |
|---|---|
| **PF11** | Two independent routes agree with §2. **Registered tolerance: maximum absolute score difference < 1e-10, identical full rankings, identical next `top_m`, in all 12 next-step cells.** Fail → stop |
| PF1 | Q11 cosine trace and 119-episode Gram matrix, counted and hashed. Targeted probes' absence recorded as a known limit |
| PF2 | Component identity re-asserted at the execution commit |
| PF3 | Gate ordering asserted in git |
| PF4 | Maximum reachability at each depth, stated before the kill condition locks |
| PF5 | Content SHA-256 only |
| PF6 | X0 reproduces its own committed result — payload SHA-256 `64b19b96…8afe478`, 8 episodes, 31,946 characters. Reused from S2 |
| PF7 | Absorbing-state proof, real trace, all cells |
| PF8 | Depth-local behavior exercised on one probe; cross-turn and live variance are not |
| PF9 | Surrogate audit (§5) |
| PF10 | Offline delivery is not an answer verdict |

**§4's PF11 tolerance is registered here because Rev 3 left it unstated.** PF11's diagnostic agreed at 9.49e-15; 1e-10 is loose against that and tight against the 0.040–0.212 differences that failed. **If agreement lands between those, escalate rather than adjusting the tolerance.**

---

## 5. Surrogate audit — one row added

Carried from Rev 3, plus:

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| **§2 matches the vector route** | **the derivation implements §5.1's rule** | **Yes — both routes could implement the same wrong rule.** PF11 compares §2 against a vector implementation; if that implementation were also written from §2 rather than from §5.1, agreement would be circular | **The vector route must be implemented from §5.1's pseudocode directly, by a path that does not read §2.** Assert this in the PF11 artifact |

**That row is the one Rev 4 most needs.** Rev 3's failure was caught because the vector route was independent. **Keep it independent.**

Rev 3's other rows stand: no-cycle can pass on near-identical sets; Q11 availability rising cannot catch a targeted regression that no arm measures; a chain that wins by returning more material has not shown better ranking — X0 returned zero K candidates on 74 of 121 turns while `top_m` always returns `m`.

**Accepted residual:** one probe, one corpus, no variance, **no targeted no-regression check.** The last is why no outcome promotes.

---

## 6. Registered predictions

Prior: fourteen predictions, most wrong on mechanism, including Rev 3 §2 at 80% confidence.

1. **PF11 passes.** ~85%. Higher than Rev 3's 80% because the formulation has already matched the vector route once — **and that is precisely the reasoning that should be distrusted**, so the increase is small.
2. **Preflight passes without cycles** at `RHO ≥ 0.5`, `W_Q ≥ 0.3`. ~70%.
3. **Depth 1 helps, depth 3 hurts.** ~60%.
4. **Best chained arm reaches 8–11/17**, below E005's 12/17.
5. **Final cue drifts** — cosine below 0.7 to `q0` by depth 2.
6. **Chaining beats X0 on raw count while delivering more candidates**, making §5's last row the one that matters. ~50%.

**The uncomfortable one, unchanged:** 4 and 6 together say this loses to a ledger mechanism and may only appear to beat the deployed path by volume. If so, the value is PF7's discipline, §2's computability result, and the drift measurement.

---

## 7. Deliverables

- [ ] **Rev 4 committed as design anchor before implementation** — SHA recorded
- [ ] **New authorization recorded.** Rev 3's does not carry
- [ ] PF11 re-run against §2, with the vector route implemented **independently from §5.1** and that independence asserted in the artifact — **stop if it fails**
- [ ] Remaining Preflight PF1–PF10, artifacts committed
- [ ] Maximum reachability by depth, before kill condition locks
- [ ] X1 = single-shot `top_m` by payload digest at all `D = 0` cells
- [ ] PF7 real-trace cycle and novelty sweep, 48 cells, region reported
- [ ] S4: facts, characters, episodes, **candidate counts** per arm and depth
- [ ] Final-cue drift per depth
- [ ] Ledger verdict, ceiling CHARACTERIZED; graveyard entry if killed
- [ ] **Explicit statement that no targeted no-regression arm was possible, and why**

---

*Rev 4, August 10, 2026. Supersedes Rev 3 (`42f710a3`, `1A41013C…D24B325`), withdrawn after PF11 FAIL at `960c9810`. Sole change: §2 replaced with the recursive Gram formulation derived from §5.1, tracking `S_i = ĉ·ê_i` and `P = q̂0·ĉ` through the blend so `RHO` and `BETA` enter the recurrence. PF11 unchanged and re-run; its tolerance now registered.*
