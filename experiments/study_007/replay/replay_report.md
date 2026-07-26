# Study 007 — Retrieval Replay Gate and Parameter Calibration (S7_005)

**Status:** PASS at `B_ltm = 32,000`, `k_min = 1`
**Tasks:** S7-T-014 (harness), S7-T-015 (fidelity), S7-T-016 (calibrate), S7-T-017 (lock)
**Binding amendment:** `amendments/AMENDMENT_002_floor_cost_criterion.md`
**Raw data:** `calibration_sweep.json`
**Reproduce:** `PYTHONUTF8=1 .venv/Scripts/python.exe scripts/calibrate_study_007_retrieval.py`

---

## 1. Read-only guarantee

Study 006's run directory holds **270 files**, SHA-256 hashed before and after
the sweep and compared: **byte-identical**. The database is opened
`file:...?mode=ro`.

## 2. Harness fidelity (S7-T-015)

Configured with Study 006's parameters — `M = 5`, no floor, count-based — the
harness must reproduce what Study 006 actually did, or no replay evidence is
trustworthy.

| Probe | Records | Source turns | Topics | Domains in block |
|---|---:|---|---:|---|
| Q11 (turn 120) | 4 | 3, 4, 8, 98 | 2 | civil |
| Q14 (turn 121) | 4 | 4, 8, 31, 105 | 3 | civil, art, marine |

The live Study 006 run rendered **exactly these source episodes at both probes**
— turns 3, 4, 8, 98 at Q11 and 4, 8, 31, 105 at Q14 — with the same 4-element,
2-topic, single-domain result at Q11 the LTM analysis recorded.

**PASS.**

### One documented divergence, metadata only

For an episode contributing two spans to the top 5, the harness cites a
different `distilled_id` than the live run did. Study 006's arbitration merges
duplicates within the LTM tier as `{**existing, **candidate}`, so the **last**
(lower-similarity) span overwrites the first; the harness keeps the
**highest-similarity** representative.

At Q11 this affects one element (turn 4: live `ef885fef` at similarity 0.505539,
harness `11751190` at 0.510482). **Not a single delivered character differs** —
the rendered text is the source episode's either way, and only the cited span id
and similarity attribute change. Study 007 keeps highest-similarity, because a
collapse should preserve the best reason for admitting the episode.

## 3. The gate at the locked parameters

Criterion 1 requires at least one planted term from each of the four domains in
the block at both probes, matched against the rendered block (see the plant
key's two-contexts table).

| | Q11 (turn 120) | Q14 (turn 121) |
|---|---|---|
| Domains covered | **civil, art, monetary, marine** | **civil, art, monetary, marine** |
| Records in block | 8 | 8 |
| Characters used | 31,269 / 32,000 | 31,947 / 32,000 |
| Budget utilization | 97.7% | 99.8% |
| Floor selections | 1 per topic × 4 | 1 per topic × 4 |
| Fill selections | 4 | 4 |
| Containment drops | 2 | 3 |
| Budget exceeded | never | never |

Projected peak context **13,741 tokens = 27.4%** of the 50,176 capacity, against
a 60% limit. Study 006's treatment peaked at 12,169.

**Criteria 1, 2 and 3 all PASS.**

Against Study 006 at the same probes: 4 records → 8, 13,130 delivered characters
→ 31,269, and **2 domains → 4**.

## 4. Calibration frontier

Full sweep in `calibration_sweep.json`. `causal` compares against `k_min = 0` at
the same budget; `bound` is Amendment 002's character form; `slot` is the
pre-registered slot form, retained for the record.

| `B_ltm` | `k_min` | 4-dom | causal | peak tok | majority | top span | bound | slot | min share | verdict |
|---:|---:|---|---|---:|---|---|---|---|---:|---|
| 24,000 | 2 | ✓ | **✓** | 11,604 | ✗ | ✓ | ✓ | ✓ | 0.215 | |
| 28,000 | 2 | ✓ | **✓** | 12,673 | ✗ | ✓ | ✓ | ✓ | 0.182 | |
| **32,000** | **1** | **✓** | ✗ | **13,741** | **✓** | **✓** | **✓** | ✗ | **0.525** | **LOCKED** |
| 32,000 | 2 | ✓ | ✗ | 13,673 | ✗ | ✓ | ✓ | ✗ | 0.158 | |
| 40,000 | 1 | ✓ | ✗ | 15,877 | ✓ | ✓ | ✓ | ✗ | 0.597 | pass, larger |
| 64,000 | 1 | ✓ | ✗ | 22,219 | ✓ | ✓ | ✓ | ✓ | 0.747 | pass, 2× larger |

Under the smallest-sufficient rule with `k_min ≥ 1`, **`B_ltm = 32,000`,
`k_min = 1`**.

`k_min = 0` is swept as a diagnostic control and excluded from selection — it
disables the floor, which is not the pre-registered component.

## 5. What the gates cost the pre-registration

Two criteria did not survive contact with the store, both for the same reason,
and both are recorded as amendments rather than quietly adjusted:

- **`B_ltm` = 4,000** (Amendment 001) — derived from a delivered-information
  figure that measurement refuted. It would have *cut* delivery 3.3× and could
  not hold four domains at a 3,940-character mean.
- **Criterion 3's slot bound** (Amendment 002) — assumes uniform record size.
  Rendered episodes span 500–6,238 characters, so the criterion measures the
  ratio of episode sizes between domains, and is satisfiable only by inflating
  the budget until the floor is inert.

Both are instances of one failure class — a budget expressed as a count of
items whose size varies — which is also what Study 006's breadth regression was,
and what the stage-interface check caught twice more in the code. Four
instances, one root cause, all found before the run.

## 6. The pre-registered prediction

**At the locked parameters the diversity floor does not cause four-domain
coverage at the probes. The budget alone does.**

| `B_ltm` | no floor (`k_min=0`) | `k_min=1` | `k_min=2` |
|---:|---|---|---|
| 24,000 | 3/3 | 3/4 | **4/4** |
| 28,000 | 3/3 | 3/4 | **4/4** |
| **32,000** | **4/4** | **4/4** | 4/4 |

The floor is load-bearing only at 24,000–28,000 with `k_min = 2`, where the
targeted fixture fails hardest (own-domain share 0.215). Buying breadth there
would inflict the mirror of Study 006's failure on targeted recall.

So: a Bar 1 pass is attributable to the component, and specifically to the
information-expressed budget — **not to the diversity floor**. The floor's real
exam is Bar 2, where its cost is what is measured. Recorded here, before the
run, so the attribution is not chosen after seeing the result.

## 7. Interpretive limit (carried)

`B_ltm` and `k_min` were calibrated on this replay data, so the replay cannot
independently validate them. Its role is to prevent spending a run on a policy
that provably cannot work — which it did, twice, at zero cost. The targeted
fixture and the live run remain the out-of-sample evidence.

## 8. Locked (S7-T-017)

| Parameter | Value |
|---|---:|
| `B_ltm` | **32,000 characters** |
| `k_min` | **1 per topic** |

Recorded in the pre-registration and the decision record before the ablation.
No post-run changes permitted.
