# E006 Part 2 — Retrieved-Context Chained Retrieval (Rev 3, superseding)

**Type:** Mechanism specification. Repair of a failed Preflight.
**Repository:** `contextDecayWindow` · `experiments/components/retrieval_mechanism_ledger/`
**Branch:** `e006-p2-chained-retrieval`
**Supersedes:** Rev 2, design anchor `7fa09c62`, SHA-256 `84A5EB5B…B35DC1` — withdrawn for the defects in §1
**Status:** DRAFT — **UNAUTHORIZED.** Requires new authorization; Rev 2's does not carry
**Preflight of record:** S2 FAIL, auditor commit `1dabee2a`, artifact `AE78582C…369FA9`
**Companions:** `RETRIEVAL_MECHANISM_LEDGER.md` · `PREFLIGHT.md` · `LITERATURE_LANDSCAPE.md`

---

## 0. What happened, and what this document is

Rev 2 passed S1 and **failed S2 Preflight on four checklist items.** The failures were design defects, not implementation problems, and Preflight caught every one before a parameter was registered or an arm ran.

**Rev 3 repairs three defects and narrows the study to what committed artifacts actually support.** It is a smaller study than Rev 2 proposed. That is the correct outcome of a failed Preflight.

### 0.1 Corrected companion references

Rev 2 named `NEUROSCIENCE_LANDSCAPE.md` and `STANDING_RULE_preflight.md`. **Neither exists in the repository.** Both are drafts never committed under those names. The repository's near-matches are `LITERATURE_LANDSCAPE.md` and root `PREFLIGHT.md`; Rev 3 cites those.

**Any grounding this spec cites must be committed to the repository before it is cited, or dropped.** The auditor recording the discrepancy rather than substituting silently was correct.

---

## 1. The three defects and their repairs

### 1.1 D1 — X1 was structurally incapable of being a control

**Registered:** X1 = chain with `BETA = 0`, asserted to equal X0.

**Why it cannot hold:** `BETA = 0` freezes the context, but the inclusive `0..D` loop still runs `D+1` times with `exclude=seen`. The candidate set is `m × (D+1)`, not `m`. **Disabling reinstatement does not disable chaining** — it makes the chain walk deeper into a fixed ranking. Demonstrated mechanically on Q11 across all six registered cells.

**Repair: X1 is `D = 0`, not `BETA = 0`.** The inclusive loop at `D = 0` executes one step and retrieves exactly `m` episodes — single-shot `top_m`, which is the chain's true degeneracy.

**Author's error, recorded as such.** The control asserted a property the mechanism's own loop structure forbids.

### 1.2 D2 — the chain does not reduce to the deployed path

**Preflight established (PF2):** deployed X0 is **thresholded K** — every episode scoring ≥ 0.48, scanned in store order — followed by **N-first packing over a least-recently-delivered rotation**. The chain is **`top_m` over an exclusion set**. Different retrieval operations. **No parameterization of the chain reduces to X0.**

**Repair: stop requiring it to.** X0 becomes a **reference**, not an identity target.

| Rev 2 | Rev 3 |
|---|---|
| X0 is the anchor the chain must reduce to | X0 is a reference the chain is compared *against* |
| X1 proves "mechanism off = deployed path" | X1 proves "mechanism off = single-shot `top_m`" |
| Asks: does chaining improve the deployed path? | Asks: does chaining improve single-shot `top_m`, and how do both compare to the deployed path? |

**This changes what the study means and must be stated in any report.** Rev 3 evaluates chained `top_m` as an *alternative* retrieval path, not an enhancement of the deployed one.

**PF6 amended:** the reproduction anchor is X0 reproducing its own committed result, which Preflight already demonstrated exactly — payload SHA-256 `64b19b96…8afe478`, 8 episodes, 31,946 characters. Reused, not re-derived.

### 1.3 D3 — `q0` does not exist in committed artifacts

**Preflight established:** the store embeds full `User: …\nAssistant: …` pairs; the live K path embeds the **raw current user message**. **0 of 8 probe-query vectors** across five committed caches. `logs/context_match.jsonl` has candidate identities, no query vectors, no complete cosine arrays. Only **Q11** carries a full committed cosine rank trace.

**Repair: §2 shows the chain is computable from committed artifacts for any probe with a full cosine trace — Q11 only.**

**Rejected alternative: authorize embedding calls to reconstruct `q0`.** Reconstruction reintroduces the H1 call-shape hazard — the carried embedder returns materially different vectors for a query embedded alone versus batched, component difference 0.217 at cosine agreement 0.999837, which flipped 6 of 146 committed payloads in a prior run. **A reconstructed `q0` would not be the `q0` the live run used, and nothing in the record would reveal the difference.** Zero-call scoping is sounder.

---

## 2. The computability result — verify before relying on it

**Claim: the chain's ranking and absolute scores are computable from committed cosines plus the episode Gram matrix, with zero embedding calls.**

Let `q̂0` be the unit query vector, `ê_i` unit episode vectors, `c` the context vector.

- **Committed:** `cos(q0, e_i)` for all `i` — Q11's full cosine trace.
- **Computable from committed vectors:** `cos(e_i, e_j)` for all pairs — the Gram matrix over 121 stored episode vectors.

Each step needs `score(e_i) = cue · ê_i`, where `cue = normalize(α·q̂0 + β·ĉ)`.

Because `c` is the mean of unit episode vectors over the current hit set `H`:

- `ĉ · ê_i = mean_{h∈H} cos(e_h, e_i)` — **Gram matrix**
- `q̂0 · ĉ = mean_{h∈H} cos(q0, e_h)` — **committed cosine trace**
- `|α·q̂0 + β·ĉ| = sqrt(α² + β² + 2αβ·(q̂0 · ĉ))` — **from the above**
- `score(e_i) = (α·cos(q0,e_i) + β·(ĉ · ê_i)) / |α·q̂0 + β·ĉ|`

Every term resolves to a committed artifact. **`q0` itself is never needed.**

**This must be verified, not assumed.** It is an author derivation, and the author's prior on such derivations in this program is poor. **Verification is PF11 (§4). If it fails, Rev 3 has no offline path and the study stops.**

---

## 3. Scope — Q11 only, and what that costs

**The study runs on the enumeration probe alone.**

**Why defensible:** Q11 is F1's probe — the failure this mechanism targets. Preflight confirmed the DR-002 observation on it: the four highest-cosine episodes carry 0/17 target facts. It is the probe where a chained cue has most to prove.

**What it costs, plainly:**

- **No no-regression arm.** Rev 2's binding requirement was that the eight targeted probes must not fall. **Their cosine traces do not exist, so that check cannot run.** A real loss — targeted retrieval is the one capability that works, and every breadth mechanism is a candidate for breaking it.
- **Therefore no promotion, no adoption, no ledger status beyond CHARACTERIZED, on any outcome.** A mechanism that cannot be shown to preserve targeted recall does not advance, however well it does on Q11.
- **n = 1 probe.** The program has one enumeration probe and cannot support a general claim about enumeration.

**E-4 sharpens the framing.** K returned zero candidates on **74 of 121 turns**, including three of the eight probe turns. The deployed similarity path is sparse and frequently empty. **The chain, using `top_m`, always returns `m`.** That is a difference in kind — the strongest argument for evaluating the chain as an alternative path, and also a reason to expect it to deliver lower-relevance material.

---

## 4. S2 Preflight — re-run requirements

Preflight re-runs in full. Passed items are re-asserted, not carried.

| # | Requirement |
|---|---|
| **PF11 (new)** | **Verify §2's computability derivation.** Compute `score(e_i)` for one step by two independent routes and assert agreement. **If it fails, stop — there is no offline path** |
| PF1 | Inputs: Q11 cosine trace and the 121-episode Gram matrix, counted and hashed. **The eight targeted probes' absence recorded as a known limit, not a failure** |
| PF2 | Component identity re-asserted; Preflight's E-2 table is the reference. Confirm it holds at the execution commit |
| PF3 | Gate ordering asserted in git — design anchor ancestor of execution commit |
| PF4 | **Maximum reachability at each depth**, from the Q11 trace, stated **before** the kill condition locks |
| PF5 | Content SHA-256 only |
| PF6 | **Amended (§1.2):** X0 reproduces its own committed result; Preflight's reproduction reused |
| PF7 | **Absorbing-state proof, now executable** via §2. Real trace, all cells, cycle and near-fixed-point detection per §5.3 |
| PF8 | Depth-local behavior fully exercised on one probe; **cross-turn and live variance are not** |
| PF9 | Surrogate audit (§7) |
| PF10 | Offline delivery is not an answer verdict |

---

## 5. Mechanism and controls

### 5.1 The rule — unchanged from Rev 2

```
retrieve_chained(q0, budget, D, m):
    c = q0
    seen = {}
    for step in 0..D:                       # inclusive: D=0 runs one step
        cue  = normalize(W_Q * q0 + W_C * c)
        hits = top_m(cue, exclude=seen)
        seen |= hits
        c    = normalize(RHO * c + BETA * mean(ê for ê in hits))
    return pack(rank(seen, cue_final), budget)
```

**Asserted properties, not tuning choices:** `W_Q > 0` (drift defence), `RHO > 0` (absorbing-state defence), `exclude=seen` (no trivial fixed point).

### 5.2 Arms

| Arm | Configuration | Role |
|---|---|---|
| **X0** | Deployed: thresholded K + N-first packing | **Reference.** Not an identity target (§1.2) |
| **X1** | Chain, `D = 0` | **Degeneracy control.** Must equal single-shot `top_m` by payload digest |
| **X2–X4** | Chain, `D` = 1, 2, 3 | The mechanism |

### 5.3 Parameters — registered before S4

| Parameter | Range | Note |
|---|---|---|
| `D` | {0, 1, 2, 3} | 0 is X1 |
| `m` | {3, 5} | |
| `W_Q` | {0.3, 0.5, 0.7} | `W_C = 1 − W_Q`, not free |
| `RHO` | {0.5, 0.7} | `BETA = 1 − RHO`, not free |

**48 cells** including `D = 0`. **No cell added after results are seen.**

**PF7 assertions per cell:** no repeated retrieved set; no fixed point; per-step novelty > 0. **A chain returning the same set at every depth is degenerate even without exact repetition.** Report the region where cycles or degeneracy appear; cycles inside the registered range means those settings are not authorized.

---

## 6. Outcome and kill condition

**Outcome:** Q11 facts available, at the enforced 32,000-character budget under exact serialized cost, reported jointly with characters, episodes, and candidate counts at each depth.

**A count, not a score** — untouched by the measured 3.0-point instrument band, which Amendment 001 §7 names as applying to scores only.

**Kill: no chained arm exceeds X0's committed Q11 availability at any registered cell.**

**Achievability (PF4):** AR-001 established 14/17 fits in 5,058 of 32,000 characters — the budget does not bind; the question is reachability. **State maximum reachability at each depth before locking.** If the seed set cannot reach fact-bearing episodes at any depth, the mechanism is dead and S4 need not run.

**Reference points, reported and not thresholds:** E002 reached 10/17 against a 6/17 same-budget baseline and was killed on its own bar; E005 reached 12/17; the AR-001 oracle is 15/17 at 5,455 characters.

**Ceiling on any outcome: CHARACTERIZED.** No promotion without the targeted no-regression arm (§3).

---

## 7. Surrogate audit

| Check | Certifies | Can it pass falsely? | Mitigation |
|---|---|---|---|
| §2 computability | the offline path is valid | **Yes — a derivation can be self-consistent and wrong** | PF11: two independent routes must agree |
| No cycle | mechanism stable | **Yes** — near-identical sets without exact repetition | Per-step novelty asserted, not just non-identity |
| Q11 availability rises | mechanism works | **Yes** — and no targeted arm exists to catch a regression | §3: ceiling CHARACTERIZED; no promotion |
| X1 = single-shot `top_m` | harness correct | Yes — could match by coincidence | Payload digest, all `D = 0` cells |
| `W_Q > 0` prevents drift | cue stays on topic | **Yes** — small `W_Q` against large `W_C` drifts anyway | Report final-cue cosine to `q0` per depth |
| Depth helps | chaining helps | Yes — could be more material at any cost | Facts, characters, episodes reported jointly |
| Chain beats X0 | better ranking | **Yes — different operation, different sparsity.** X0 returned zero K candidates on 74 of 121 turns; `top_m` always returns `m` | Report candidate counts alongside facts. **A chain that wins by returning more material has not shown better ranking** |

**Accepted residual:** one probe, one corpus, no variance, no targeted no-regression check. **The last is the most serious and is why no outcome promotes.**

---

## 8. Registered predictions

Committed so they can be wrong. Prior: thirteen predictions, most wrong on mechanism — including D1 above.

1. **PF11 verifies.** ~80%.
2. **Preflight passes without cycles** at `RHO ≥ 0.5`, `W_Q ≥ 0.3`. ~70%.
3. **Depth 1 helps, depth 3 hurts** — drift dominates past two hops. ~60%.
4. **Best chained arm reaches 8–11/17**, below E005's 12/17.
5. **Final cue drifts measurably** — cosine below 0.7 to `q0` by depth 2.
6. **New:** `top_m` chaining beats X0 on raw Q11 count **while delivering more candidates**, making the last surrogate row the one that matters. ~50%.

**The uncomfortable one:** predictions 4 and 6 together say this loses to a ledger mechanism and may only appear to beat the deployed path by delivering more. If so, the value of the work is PF7's absorbing-state discipline, §2's computability result, and the drift measurement.

---

## 9. Deliverables

- [ ] **Rev 3 committed as design anchor before implementation** — SHA recorded
- [ ] **New authorization recorded.** Rev 2's does not carry
- [ ] PF11 computability verification — **stop if it fails**
- [ ] Preflight re-run in full, PF1–PF11, artifacts committed
- [ ] Maximum reachability by depth, stated before kill condition locks
- [ ] X1 = single-shot `top_m` asserted by payload digest at all `D = 0` cells
- [ ] PF7 real-trace cycle and novelty sweep, 48 cells, region reported
- [ ] S4: facts, characters, episodes, candidate counts per arm and depth
- [ ] Final-cue drift per depth
- [ ] Ledger verdict, ceiling CHARACTERIZED; graveyard entry if killed
- [ ] **Explicit statement that no targeted no-regression arm was possible, and why**

---

*Rev 3, August 10, 2026. Supersedes Rev 2 (`7fa09c62`, `84A5EB5B…B35DC1`), withdrawn after S2 FAIL at `1dabee2a`. Repairs: X1 redefined as `D = 0`; X0 demoted from identity target to reference; scope narrowed to Q11 via the §2 computability result, zero embedding calls. Reference failure for PF7: Arm S locked at turn 11 for 111 turns under a monotone no-decay state.*
