# Study 008 Amendment 001 — Span Rendered-Cost Accounting

**Registered:** July 26, 2026
**Trigger:** Gate 3 blocker, before any ablation or live run
**Scope:** Factor R budget accounting only
**Status:** BINDING

---

## 1. Blocker encountered

The registered Gate 3 sweep found no jointly admissible `c_fill`. Arm A passed
the targeted fixture and reproduced Study 007's Q11/Q14 blocks byte-for-byte.
Arm C reached fact-aware four-domain coverage at both breadth probes, but every
span arm failed targeted majority at every swept cap.

The failure is not a retrieval-ranking result. Under content-only charging, the
32,000-character budget is larger than the preserved distilled span store, so a
span arm can deliver nearly every record regardless of query.

Measured with the exact Study 008 renderer:

| Cell | Records | Charged content | Actual `<retrieved_ltm>` block | Uncharged overhead |
|---|---:|---:|---:|---:|
| Arm A, Q11 | 7 | 31,518 | 33,406 | 1,888 |
| Arm C, Q11 | 185 | 27,433 | 78,012 | 50,579 |
| Arm C, civil targeted query | 200 | 28,498 | 83,106 | 54,608 |

Study 007 excluded XML scaffolding because it was a small, approximately fixed
per-episode overhead. Factor R changes the number of rendered elements by more
than an order of magnitude and adds provenance attributes to every span. The
overhead is therefore neither small nor constant across the factorial.

Content-only charging certifies "within 32,000 characters" while delivering an
83,106-character LTM block. This is the standing surrogate/interface failure
class identified by the preregistration.

## 2. Amendment

For **span-rendering arms C and D**, one candidate's budget cost is the exact
serialized `<span ...>text</span>` element emitted by the production renderer,
including its provenance attributes and escaping.

For **episode-rendering arms A and B**, Study 007's accepted content-character
cost remains unchanged. Changing it would break Arm A's byte reproduction and
confound Factor F by making A and B use different accounting.

The outer `<retrieved_ltm>` open/close tags are constant per block and remain
outside candidate admission cost in all arms.

The same renderer function is the single authority for span serialization and
span cost. No estimated per-record constant is introduced.

## 3. Why this is not criterion softening

Gate 3's majority, top-item, and bounded-cost criteria are unchanged. The
fact-aware Gate 2 proceed condition is unchanged. `B_ltm = 32,000`, `k_min = 1`,
formation, STM, runtime, seed, and all rubric bars are unchanged.

The amendment corrects the quantity constrained by the existing budget to the
quantity Factor R actually delivers. It was forced by a pre-run blocker, uses
only data available before ablation, and makes the gate harder to game rather
than easier to pass.

## 4. Consequences and verification

- Re-run all unit tests, leakage audit, Gate 2, and Gate 3 from scratch.
- Arm A must still reproduce Study 007's probe blocks byte-for-byte.
- Add a test asserting span budget cost equals the exact serialized span
  element length, including XML escaping.
- Recompute context projections from the amended predicted blocks.
- If no `c_fill` passes after corrected accounting, the STOP verdict remains
  binding; no further accounting amendment is permitted from the same evidence.

## 5. Authorization

Authorized under the study author's standing July 26, 2026 instruction:
amendments are permitted only when needed to continue past a blocker and made
in good faith when the blocker is encountered. This amendment is registered
before the affected implementation and rerun.
