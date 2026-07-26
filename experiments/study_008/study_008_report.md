# Study 008 — Retrieval Factorial

## contextDecayWindow · Idris Applied AI Research

**Status:** COMPLETE — **STOPPED AT PRE-RUN GATES**
**Live runs:** none
**Registration:** `0a20ef0`
**Gate STOP:** `4a29540`
**Amendments:** 001 (span rendered-cost accounting)

---

## Summary

Study 008 registered a 2x2 factorial over floor/fill policy and LTM rendering:

| Arm | Floor/fill | Rendering |
|---|---|---|
| A | similarity floor, uncapped fill | source episode |
| B | density floor, capped fill | source episode |
| C | similarity floor, uncapped fill | selected span |
| D | density floor, capped fill | selected span |

The study stopped before ablation because no `c_fill` from 1 through 50 passed
the fact-aware breadth replay and targeted-retrieval fixture jointly.

This is the gates doing their job. No inference run, score, or bar verdict was
manufactured from a design that had already failed its spend conditions.

## Gate results

### Gate 1 — corrected Study 007 re-derivation

**P1 CONFIRMED.** At the locked `B_ltm = 32,000`, no `k_min` from 0 through 4
gave episode rendering a complete rubric-critical fact from all four domains at
both probes.

The first swept episode-rendering pass was `B_ltm = 40,000`, `k_min = 2`.
Study 007 Amendment 002 §6's claim that the floor was inert at 32,000 is void
under the corrected criterion: `k_min = 0` does not reach fact-aware 4/4.

### Gate 2 — four-arm replay

Arm A reproduced Study 007's actual LTM blocks exactly:

| Probe | Predicted block SHA-256 | Actual block SHA-256 | Verdict |
|---:|---|---|---|
| 120 | `f78f91fea54b535494437ce43f10278ced4720001dd78346be238c9c6b75180a` | same | PASS |
| 121 | `4b338017ab877cb6a2bc90ff2a62222b69a8129eec8359a8be007dbf4a87c61d` | same | PASS |

The 271 preserved Study 007 artifacts were hash-identical before and after the
replays.

After Amendment 001, the decisive calibration points were:

| `c_fill` | Arm A 4/4 | Arm B 4/4 | Arm C 4/4 | Arm D 4/4 | Gate 3 |
|---:|---|---|---|---|---|
| 1 | FAIL | **PASS** | FAIL | FAIL | FAIL |
| 5 | FAIL | FAIL | FAIL | FAIL | FAIL |
| 50 | FAIL | FAIL | FAIL | FAIL | **PASS** |

At `c_fill = 1`, density/cap episode retrieval delivers breadth but allocates as
little as 11.5% of a targeted block to the queried domain. At `c_fill = 5`, Arm
B's minimum targeted share rises to 54.7% but its Q11 block loses monetary
facts. At 50, all arms pass targeted allocation, while every arm fails
four-domain delivery at one or both probes.

### Gate 3 — targeted retrieval

Post-amendment minimum targeted-domain shares:

| Arm | Earliest passing `c_fill` | Minimum own-domain share there |
|---|---:|---:|
| A | not capped | 50.7% |
| B | 5 | 54.7% |
| C | not capped | 52.5% |
| D | 50 | 52.6% |

Top own-domain items and character-cost bounds passed at those points. The
breadth gate did not.

## Amendment 001

The first Gate 3 run exposed an interface error. Content-only accounting charged
Arm C 27,433 characters at Q11 while the renderer delivered a 78,012-character
LTM block. A targeted Arm C query charged 28,498 and delivered 83,106.

The cause was per-span provenance markup: negligible at seven episode elements,
dominant at roughly 200 span elements. Amendment 001 made span candidates cost
their exact serialized `<span>` element, using the production renderer as the
single authority. Episode arms retained Study 007 accounting so Arm A remained
an exact reproduction.

No gate criterion changed. The corrected gates still failed jointly, so the
STOP remained binding.

## Prediction ledger

| Prediction | Verdict | Evidence/consequence |
|---|---|---|
| P1 — no episode-rendered `k_min` solves 4/4 at 32k | **CONFIRMED** | Gate 1; rendering economics matter more than Study 007's surrogate implied. |
| P2 — span arms score higher fact coverage | **NOT EVALUATED** | No live probes or scores; replay did not yield a locked admissible comparison. |
| P3 — Q5 loses full credit under span rendering | **NOT EVALUATED** | No answer was generated. Span replay confirms no accidental episode carriage, but that is not the registered score prediction. |
| P4 — D highest breadth, A lowest | **NOT EVALUATED** | No live scores and no locked `c_fill`. |
| P5 — density floor picks fact-bearing units over overviews | **NOT ADJUDICATED** | Density changed replay delivery, but the policy had no jointly admissible calibration point. |

## Bar status

| Bar | Status | Reason |
|---|---|---|
| Bar 0 — Arm A reproduction | **PRECONDITION PARTIAL** | Replay blocks match byte-for-byte; no Arm A live run or score reproduction occurred. |
| Bar 1 — breadth recovery | **NOT EVALUATED** | No live run. |
| Bar 2 — targeted recall | **NOT EVALUATED** | No generated answers or blinded scores. |
| Bar 3 — formation non-regression | **NOT EVALUATED** | No per-arm store was formed. Carried formation tests pass, but tests are not a study result. |

The registered outcome vocabulary (VALIDATED/PARTIAL) applies to completed live
factorials. This study is instead reported as **STOPPED AT PRE-RUN GATES**.

## What was learned

1. Fact-aware coverage reverses Study 007's floor-inertness conclusion.
2. Bare span rendering changes element count enough that provenance overhead
   must be part of budget accounting.
3. Under the fixed 32,000-character budget, the registered cap has a real
   breadth/targeted trade: the breadth point and targeted-preservation point do
   not overlap.
4. The preserved store can support breadth under one narrow episode-policy
   setting (`c_fill = 1`), but that setting is not safe for targeted queries.
5. A third policy level would be required to continue. Adding it here would no
   longer be the registered 2x2 study.

## Next study

Do not proceed directly to the 1,000-turn endurance study. First register a new
retrieval design that can pass both gates. The strongest candidates are:

1. span rendering with minimal surrounding context, so complete facts split at
   sentence boundaries can travel without whole-episode cost;
2. query-adaptive fill allocation with a pre-registered targeted lower bound;
3. formation-side per-domain fact guarantees if retrieval still cannot expose
   the locked facts within budget.

Any next design should retain the fact-aware criterion, exact rendered-unit
accounting, Arm A byte-fidelity check, and leakage audit.

## Verification

- 644 tests passed after Amendment 001.
- Leakage audit passed over 22 retrieval-path files and a 14-module import
  closure; both detectors reject the planted transitive violation.
- Gate 1 and joint Gate 2/Gate 3 replayed the accepted Study 007 store read-only.
- No ablation, full run, scoring, or mechanism interpretation occurred after
  the binding STOP.
