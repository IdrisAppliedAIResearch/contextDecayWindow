# CC-003 — Budget Enforcement and Truncation Semantics

**Pre-registration:** `CC_003_004_005_deployment_closeout.md` at `43588944`
**Branch:** `cc/003-enforcement`
**Amendment:** `amendments/AMENDMENT_001_drop_order_default.md`
**Blocking gate:** `DECISION_001_dx002_growth_branch.md` (DX-002, Branch B)
**Artifacts:** `artifacts/cc003/`
**Status:** PASS — E1–E6 green, suite 963

Closes `CC_001` O1 and O2.

## 0. The block, and its release

DX-002 returned Branch B and §0.4 made that a block on this part: *name the
unbudgeted component and bring it inside the budget or remove it before
anything ships*. Shipping a ceiling while an unbudgeted block grows beside
it would produce exactly the wrong reassurance — `truncated=False` on a
context that is not bounded.

**G-E0** is the gate that releases it. It replays all 1,000 committed
Study 010 arm L episodes, with their committed embeddings, turn by turn
through `episodic.build_context` at a 32,000-character budget, so the store
grows exactly as it did during the run. No embedder is required:
`build_context` is a pure function of episodes, a query vector, a budget,
and a config.

| Measure | Study 010 runner | `episodic` |
|---|---:|---:|
| Delivered block, p95 growth over the last five 100-turn buckets | **+23,238 chars** (arm L STM) | **+18 chars** |
| Window over window, turns 401–700 → 701–1000 | +33.0% | **−0.02%** |
| Turns over budget | 668 of 1,000 | **0 of 1,000** |
| Saturated by the DX-002 criterion | no | **yes** |

The library's block sits at a mean of ~31,840 characters from turn 101
onward and does not move for the next 900 turns. **The leak is a property
of the Study 010 runner**, which carried the recency window and the
retrieval tier on separate budgets; `build_context` routes the recency
window, the K-threshold hits, and the coverage selection through a single
`budget` in `pack_stm_payload`, which charges the exact serialized cost of
the whole two-block payload on every admission.

DX-002's Branch B stands as a finding about the runner. It is discharged
for the deployable component, and CC-003 proceeds.

## 1. What was already true

Most of §1.2's ceiling was carried, not built. `pack_stm_payload` already
charged exact serialized cost and skipped candidates that did not fit;
`select()` already filtered each greedy step to affordable candidates. The
honest description of this part is that it **closed three gaps and named
one policy**, rather than that it built enforcement from nothing.

## 2. What changed

### 2.1 The ceiling no longer has an exception at the bottom

`pack_stm_payload` raised `ValueError` when the budget could not fit the
two empty block tags, and `select()` raised `AssertionError` at any budget
too small to afford a single candidate — an additive-cost identity that
only describes a non-empty selection was asserted unconditionally. A hard
ceiling with an exception at the bottom is not a hard ceiling. Both now
degrade: an empty block, `truncated=True`, no exception, at every budget
down to and below zero.

The `select()` fault was latent and pre-existing. It could not surface
through `build_context` at any realistic budget, because at least one
candidate always fit. E4 found it.

### 2.2 The truncation signal carries what was dropped

`ContextReport` gains `dropped_ids` — the identities of episodes the
retrieval paths proposed and packing did not deliver, in proposal order —
alongside `drop_policy`, `budget_chars`, and the derived `chars_available`
and `shortfall_chars`. §1.2.3's objection was that "a boolean alone lets a
caller know something happened and not what"; the report now answers what.

### 2.3 The drop order is named

`episodic._packing.DROP_POLICY` is `marginal_gain_order_skip_on_overflow`,
documented at its definition with a worked example. This deviates from the
default suggested in §1.2.2 and the deviation is recorded in
`AMENDMENT_001`: the two policies agree at the 32,000 operating point, and
where they differ, the carried one delivers strictly more — two episodes
against one at a 1,000-character budget.

## 3. Tests

| # | Test | Certifies | Result |
|---|---|---|---|
| E1 | budgets 1k–64k, plus adversarial values, `chars_delivered ≤ budget` | ceiling holds | PASS |
| E2 | every budget with a shortfall sets `truncated=True` and reports identities | signal fires and is actionable | PASS |
| E3 | no budget where selection fits sets `truncated=True` | no false positives | PASS |
| E4 | budget below one episode → empty block, `truncated=True`, no exception | pathological case | PASS |
| E5 | drop order identical across two processes | reproducibility | PASS |
| E6 | at 32,000 the E005 primary reproduces 12/17 · 4/4 · 16/16 @ 31,569 chars | **enforcement changed nothing at the operating point** | PASS |

114 enforcement tests; full suite 963, up from 849.

**E6 ran against the live carried embedder**, not a proxy: CC-002's T3 was
re-executed under enforcement and reports 132 of 132 committed A3 payload
SHA-256 values matching byte-for-byte, seven targeted selections replayed,
and the primary result vector unchanged. Enforcement is inert where it
should be.

## 4. Surrogate audit, answered

§1.4 named three checks that could pass while the property is false.

| Check | Can pass falsely by | What answers it here |
|---|---|---|
| `chars_delivered ≤ budget` | **delivering nothing** | `test_the_ceiling_is_not_met_by_delivering_nothing` asserts a non-empty, episode-bearing block above 30,000 chars at the operating point; G-E0 reports a 31,840-char mean across 1,000 turns |
| `truncated` set | being a flag with no content | E2 asserts `dropped_ids` is non-empty, deduplicated, correctly sized, and disjoint from delivered turns |
| boundary tests pass | tested budgets being a sample | E1 sweeps 64 budgets from 1k to 64k plus ten adversarial values including 0, 1, and negative |

The third mitigation is real but partial: 64 budgets is a denser sample,
not a proof. The ceiling is asserted in `build_context` on every call, so a
breach at an unswept budget raises rather than ships silently — that
assertion, not the sweep, is what makes the claim general.

## 5. Boundary

- G-E0 is one store, one conversation shape, one query-vector convention
  (each turn's own embedding). It establishes that the library does not
  reproduce the runner's leak at this horizon. It is not a general
  boundedness proof, and it inherits DX-002's horizon limit in full: 1,000
  turns says nothing about 10,000.
- `chars_wanted` is the cost of what the three paths jointly proposed
  before packing, not of an unconstrained selection over the whole store.
  The coverage selector is a budgeted greedy with no unconstrained mode.
  The quantity reported is the one a caller can act on by raising the
  budget; it is not an upper bound on what a larger budget would retrieve.
- The ceiling governs the block `context()` returns. What a caller wraps
  around that block — a system preamble, a tool schema, its own scratchpad
  — is outside the library's accounting, and DX-002 is the evidence that
  this distinction is where the growth actually happened.
