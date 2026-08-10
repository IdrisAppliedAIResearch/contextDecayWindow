# E006 Part 2 - Retrieved-Context Chained Retrieval (Rev 5, superseding)

**Type:** Mechanism specification. Repair of a failed PF11 gate.
**Repository:** `contextDecayWindow` - `experiments/components/retrieval_mechanism_ledger/`
**Branch:** `e006-p2-chained-retrieval`
**Supersedes:** Rev 4, design anchor `71acbd35`, SHA-256
`2A516FCDF86744B47B2DF8BAB74794EDC73F8A66348CAA61997B1A572659C474`
**Status:** DRAFT - authorization must be recorded after this design anchor
**PF11 of record:** FAIL, auditor commit `a85f1708`, artifact
`3193DFB4D632C96E606C291E7A851BC2DBA39B9587A105355DEA655F2E2A85B3`
**Companions:** `RETRIEVAL_MECHANISM_LEDGER.md` - `PREFLIGHT.md` -
`E006_PART2_REV4_PF11.md`

---

## 0. Revision boundary

Rev 4 failed its first gate. Its recursive structure was correct, but its
normalization treated the mean of unit hit vectors as though that mean were
itself unit length. On the committed Q11 trace, the squared hit-mean norms were
`0.8426498393248191` at `m=3` and `0.5330802255471974` at `m=5`, not `1`.
Score tolerance and full-ranking identity therefore failed in all 12 PF11
cells, although all 12 immediate next `top_m` sets agreed.

**Sole Rev 5 change:** Section 2.4 registers the missing `||mu||^2` term and its
zero-call Gram computation. No mechanism rule, arm, parameter, criterion,
prediction, scope boundary, or outcome ceiling changes.

All Rev 4 requirements outside Section 2.4 carry unchanged. Rev 3 remains the
full source for the mechanism pseudocode and arm definitions where Rev 4
restated them in brief. If this document conflicts with a carried requirement,
this document governs only the explicit Section 2.4 repair; otherwise the
earlier requirement remains binding.

The program author directed creation of the necessary revision and authorized
continued execution in the August 10, 2026 user message. That authorization
must be recorded in a standalone file after this design anchor and before any
Rev 5 implementation commit.

---

## 1. Unchanged mechanism

The mechanism remains exactly Rev 3 Section 5.1:

```text
retrieve_chained(q0, budget, D, m):
    c = q0
    seen = {}
    for step in 0..D:                       # inclusive: D=0 runs one step
        cue  = normalize(W_Q * q0 + W_C * c)
        hits = top_m(cue, exclude=seen)
        seen |= hits
        c    = normalize(RHO * c + BETA * mean(e_hat for e_hat in hits))
    return pack(rank(seen, cue_final), budget)
```

`W_Q > 0`, `RHO > 0`, and `exclude=seen` remain asserted properties. Rev 5
changes no vector operation.

---

## 2. Corrected recursive Gram formulation

### 2.1 Available quantities

- `Q_i = cos(q0, e_i)` for all 119 eligible episodes from the committed Q11
  trace.
- `G_ij = cos(e_i, e_j)`, the 119 by 119 Gram matrix over normalized committed
  episode vectors, computable with zero calls.

### 2.2 State

Track the normalized context's projections:

```text
S_i = c_hat dot e_hat_i
P   = q_hat0 dot c_hat
```

Initialize at `c = q0`:

```text
S_i <- Q_i
P   <- 1
```

### 2.3 Hit-mean products

For current hit set `H`, let `mu` be the arithmetic mean of its unit episode
vectors. Every required product is available from the trace and Gram matrix:

```text
mu dot e_hat_i = mean_{h in H} G_{h,i}
q_hat0 dot mu  = mean_{h in H} Q_h
c_hat dot mu   = mean_{h in H} S_h
||mu||^2       = mean_{h in H, k in H} G_{h,k}
```

The last line is the sole mathematical addition in Rev 5. A mean of unit
vectors is unit length only when all vectors in the mean are identical.

### 2.4 Step recurrence - corrected norm

Let `BETA = 1 - RHO` and apply the unchanged unnormalized update
`c' = RHO * c_hat + BETA * mu`:

```text
S'_i(unnorm) = RHO * S_i + BETA * (mu dot e_hat_i)
P'(unnorm)   = RHO * P   + BETA * (q_hat0 dot mu)

|c'| = sqrt(
    RHO^2
    + BETA^2 * ||mu||^2
    + 2 * RHO * BETA * (c_hat dot mu)
)

S_i <- S'_i(unnorm) / |c'|
P   <- P'(unnorm)   / |c'|
```

This is the direct inner-product expansion of the unchanged vector update. It
does not normalize `mu` separately and does not assume `||mu|| = 1`.

### 2.5 Scoring

Let `W_C = 1 - W_Q`:

```text
score(e_i) = (W_Q * Q_i + W_C * S_i)
             / sqrt(W_Q^2 + W_C^2 + 2 * W_Q * W_C * P)
```

The denominator is computed even though it is constant across episodes.

### 2.6 Verification status

The Rev 3 auditor's unregistered corrected-recurrence diagnostic included the
`||mu||^2` term and agreed with its independent vector route to
`9.49240686054509e-15` in all 12 cells. That prior diagnostic is not a Rev 5
pass. PF11 runs again against this newly registered equation.

---

## 3. Scope, arms, and parameters - unchanged

**Scope:** Q11 only. The eight targeted probes have no committed cosine traces,
so no targeted no-regression arm is possible. Every outcome is capped at
`CHARACTERIZED`; no promotion, adoption, live run, model call, or embedding call
is authorized.

| Arm | Configuration | Role |
|---|---|---|
| X0 | Deployed thresholded K plus N-first packing | Reference, not an identity target |
| X1 | Chain with `D=0` | Single-shot `top_m` degeneracy control |
| X2-X4 | Chain with `D=1,2,3` | Chained mechanism |

The complete authoritative grid remains:

| Parameter | Registered values |
|---|---|
| `D` | `{0, 1, 2, 3}` |
| `m` | `{3, 5}` |
| `W_Q` | `{0.3, 0.5, 0.7}`; `W_C = 1 - W_Q` |
| `RHO` | `{0.5, 0.7}`; `BETA = 1 - RHO` |

There are exactly 48 cells. None may be added after results.

**Outcome:** Q11 facts available under exact serialized 32,000-character
packing, reported jointly with characters, episodes, candidate counts, and
final-cue drift at each depth.

**Kill:** no chained arm exceeds X0's committed Q11 availability at any
registered cell.

Reference points remain descriptive, not thresholds: X0 `6/17`, E002 `10/17`,
E005 `12/17`, and AR-001 oracle `15/17` at 5,455 characters.

---

## 4. Gate order - unchanged

**PF11 runs first. All other checks follow only after a committed PF11 pass.**

| # | Requirement |
|---|---|
| **PF11** | Independent Section 5.1 vector route and Section 2 recurrence must have maximum absolute score difference `< 1e-10`, identical full rankings, and identical next `top_m` in all 12 next-step cells. Fail means stop |
| PF1 | Q11 trace and 119-episode Gram matrix exist, are readable, hashed, and counted; targeted-trace absence recorded |
| PF2 | Every named component's behavioral identity re-asserted at execution commit |
| PF3 | Git order proves design, authorization, PF11, remaining Preflight, parameter lock, and run order |
| PF4 | Maximum fact reachability at each depth stated before the kill condition is evaluated |
| PF5 | Content SHA-256 values are the only comparison keys |
| PF6 | X0 reproduces payload SHA-256 `64b19b96...8afe478`, 8 episodes, 31,946 characters |
| PF7 | On the real Q11 trace in all 48 cells: no repeated retrieved set, no fixed point, and per-step novelty greater than zero |
| PF8 | One probe exercises depth-local behavior only; it cannot detect cross-turn or live variance |
| PF9 | Surrogate audit from Rev 4 and Rev 3 remains binding |
| PF10 | Offline availability is not an answer verdict |

PF11's vector route must continue to execute Section 5.1 directly from a path
that neither reads nor imports Section 2. Agreement between two implementations
of the same derivation would be circular and must fail the independence audit.

---

## 5. Carried surrogate audit and predictions

All Rev 4 surrogate rows remain binding: score-route agreement can be circular;
no-cycle can pass on near-identical sets; Q11 gains cannot detect targeted
regression; X1 can match by coincidence; positive `W_Q` does not prove low
drift; greater depth can merely return more material; and beating sparse X0 by
always returning `m` candidates does not demonstrate better ranking.

The accepted residual remains one probe, one corpus, no variance, and no
targeted no-regression check.

Rev 4's six registered predictions carry unchanged. No prediction is revised
after either PF11 result.

---

## 6. Deliverables

- [ ] Rev 5 design committed before implementation
- [ ] The author's August 10 authorization recorded after the design anchor
- [ ] PF11 rerun with independent vector route; stop if it fails
- [ ] PF1-PF10 completed and committed only after PF11 passes
- [ ] Maximum reachability by depth recorded before run interpretation
- [ ] X1 payload identity asserted at every `D=0` cell
- [ ] PF7 cycle, fixed-point, and novelty sweep across all 48 cells
- [ ] S4 reports facts, characters, episodes, candidates, and cue drift
- [ ] Ledger disposition capped at `CHARACTERIZED`
- [ ] Report states that targeted no-regression was impossible and why

---

*Rev 5, August 10, 2026. Supersedes Rev 4 (`71acbd35`,
`2A516FCDF86744B47B2DF8BAB74794EDC73F8A66348CAA61997B1A572659C474`),
withdrawn after PF11 FAIL at `a85f1708`. Sole change: Section 2.4 now includes
`BETA^2 * ||mu||^2`, with `||mu||^2` computed from the hit-set Gram submatrix.*
