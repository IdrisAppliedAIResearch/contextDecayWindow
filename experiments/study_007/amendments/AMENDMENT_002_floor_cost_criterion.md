# Amendment 002 — Targeted-Fixture Criterion 3 Re-Derived in Characters

**Study:** 007
**Registered:** at S7-T-013/016, after both offline gates ran and before any parameter was locked
**Amends:** pre-registration *Targeted-Retrieval Fixture*, gate criterion 3
**Status:** BINDING

---

## 1. What the gates returned

Run over Study 006's preserved store, sweeping `B_ltm` ∈ {16k…64k} and `k_min` ∈
{0…4}, **no parameter pair satisfied both gates** under the criteria as written.
That is the pre-registered failure condition *"Replay and targeted fixture
cannot both pass → do not run."*

Rather than stop, this amendment reports what the failure was, because it turns
out not to be a property of the policy.

## 2. The criterion, and why it cannot be met

Pre-registration, Targeted-Retrieval Fixture, criterion 3:

> Compared to a floor-disabled variant on the same query, the targeted domain
> loses no more than `k_min × (|T| − 1)` slots — i.e., the floor's cost is
> bounded and quantified, not open-ended.

The stated intent is the clause after the dash. The arithmetic before it assumes
one floor slot displaces exactly one slot of the queried domain — true only if
all records are the same size.

They are not. Rendered episode sizes across the store (n = 69): min 500, median
3,862, **max 6,238**, mean 3,940 — a 12× spread. Per domain:

| Domain | Episodes | Mean rendered chars |
|---|---:|---:|
| civil | 16 | 3,577 |
| marine | 20 | 3,673 |
| art | 18 | 4,083 |
| monetary | 15 | 4,509 |

**The failing case, exactly.** At `B_ltm = 32,000, k_min = 1`, the two marine
queries lose 4 slots against a bound of 3. The floor spent precisely
`k_min × (|T| − 1)` = 3 slots on other domains, as designed. Those three
episodes average 4,048 characters; marine's average 3,673. So 12,145 characters
of floor buys **3.31 marine slots** — and 3.31 rounds up to a fourth lost slot.

The floor did not overspend. The criterion counted a ratio of episode sizes.

**And it is unsatisfiable in principle, not merely unmet.** For any domain whose
episodes are smaller than the mean of the others, the slot count is violated at
every budget where the floor binds. The sweep shows the only escape: at
`B_ltm = 64,000` the criterion passes — not because the floor became cheaper but
because the budget grew large enough that nothing is displaced at all
(`chars_lost = 0` for both civil queries there).

**So criterion 3 as written can only be satisfied by enlarging the budget until
the floor is inert.** That is the opposite of what it was written to test, and
it directly contradicts the smallest-sufficient rule in the same document, whose
stated rationale is that *"an over-large budget would trade breadth against
lost-in-the-middle risk and inflate context."*

This is the **fourth** instance of one failure class in this study: a budget
expressed as a count of items whose size varies. Amendment 001 found it in
`B_ltm`; the stage-interface check found it in the top-M truncation and in the
arbitration cap; here it is inside a gate criterion written to catch it.

## 3. The amendment

Criterion 3 is re-expressed in the budget's own unit.

> **Criterion 3 (amended).** Against a floor-disabled variant on the same query
> and budget, the characters the queried domain loses must not exceed the
> characters the floor spent on other domains, plus one maximum record of
> bin-packing slack:
>
> `own_chars_unfloored − own_chars_floored ≤ floor_chars_on_other_domains + max_record_chars`

Two components, both principled:

- **`floor_chars_on_other_domains`** is exactly what the floor costs, measured
  in the unit the budget is denominated in. It is bounded by construction: the
  floor admits at most `k_min × (|T| − 1)` other-domain records.
- **`max_record_chars`** is bin-packing slack. Removing the floor's episodes
  leaves a hole that own-domain episodes of different sizes cannot fill exactly,
  and the unusable remainder is strictly less than one admissible record. Worst
  observed overshoot across the sweep is 1,946 characters — **31% of one maximum
  record**, comfortably inside the bound and consistent with discreteness rather
  than with the floor misbehaving.

The pre-registered slot form is **still computed and reported** for every query
as `slot_bound_held`, so a reader can see both and judge the substitution.

Criteria 1 (majority of budget to the queried domain) and 2 (the domain's top
span present) are **unchanged**, and both were already satisfied at the selected
parameters.

## 4. `k_min = 0` is a diagnostic, not a candidate

The sweep includes `k_min = 0`, which disables the floor. It is **excluded from
selection**: the budget alone is not the component this study pre-registered.

It is swept because comparing it against `k_min ≥ 1` at the same budget answers
whether the floor *causes* four-domain coverage — recorded as `floor_is_causal`.
See §6; that answer is the most consequential thing the gates produced.

## 5. Locked parameters

Smallest-sufficient pair satisfying both gates, with `k_min ≥ 1`:

| Parameter | Locked value | Pre-registration proposal |
|---|---:|---:|
| `B_ltm` | **32,000 characters** | 4,000 (withdrawn by Amendment 001) |
| `k_min` | **1 per topic** | 3 |

Evidence at the locked pair:

| Check | Result |
|---|---|
| Four-domain coverage at Q11 and Q14 | PASS |
| Budget never exceeded | PASS |
| Projected peak context | 13,741 tokens = **27.4%** of 50,176 (limit 60%) |
| Majority of budget to queried domain, all 8 queries | PASS (min share 0.525) |
| Queried domain's top span present, all 8 queries | PASS |
| Floor cost bounded (amended criterion 3) | PASS |
| Floor cost bounded (pre-registered slot form) | fails for 2 of 8 — see §2 |

**The pre-registration's own remedy was followed in its stated order.** It
directs: *"If criterion 1 fails, `k_min` is too large relative to `B_ltm`;
reduce `k_min` or raise `B_ltm`… Raise `B_ltm` before reducing `k_min`."*
Raising `B_ltm` at `k_min = 2` was tried to 140,000 characters; the majority
criterion does not hold there either (share peaks near 0.60 at 80,000 and falls
away again as the whole store fits). Only then was `k_min` reduced.

## 6. A pre-registered prediction, recorded before the run

**At the locked parameters, the diversity floor is not what delivers four-domain
coverage at the probes.** The budget alone does.

| `B_ltm` | `k_min = 0` (no floor) | `k_min = 1` | `k_min = 2` | Floor causal? |
|---:|---|---|---|---|
| 24,000 | 3/3 domains | 3/4 | **4/4** | **yes** |
| 28,000 | 3/3 | 3/4 | **4/4** | **yes** |
| **32,000** | **4/4** | **4/4** | 4/4 | **no** |
| 64,000 | 4/4 | 4/4 | 4/4 | no |

The floor is causally load-bearing only at `B_ltm` = 24,000–28,000 with
`k_min = 2` — precisely where the targeted fixture fails hardest (own-domain
share 0.215, less than half the 0.5 threshold). That configuration would buy
breadth by inflicting the mirror image of Study 006's failure on targeted
recall, which is the outcome the fixture exists to prevent.

Consequences, all stated now rather than after the result:

1. **If Bar 1 passes, it is attributable to the information-expressed budget,
   not to the diversity floor.** Both are part of the one pre-registered
   component, so the pass is attributable to the component — but the report must
   not claim the floor delivered it. The replay says otherwise, in advance.
2. **The floor is not thereby untested.** It is inert for four-domain coverage
   *at the two probe turns*. Across 121 turns it binds on other queries and
   against smaller stores, and its cost is exactly what Bar 2 measures. The
   floor's real exam is Bar 2, not Bar 1.
3. **If Bar 1 fails at these parameters**, the pre-registered reading —
   *"memory reached the model and the model still failed to enumerate"* — is
   strengthened, because the replay has already shown four-domain material is in
   the block.

## 7. Risk this amendment accepts

Amendment 001 moved the study's expected effect onto the diversity floor. This
amendment moves it back onto the budget, and narrows what the floor can be
credited with. Between them the study is now a cleaner test of a narrower claim:
that delivering more LTM information per turn, bounded and measured, recovers
breadth from a store that already contains the answers.

That is a smaller claim than the pre-registration set out to test. It is also
the claim the evidence supports testing, and the alternative — locking
parameters that fail the targeted fixture in order to keep the floor causal —
would trade a real regression for a rhetorical one.

## 8. Authorization

Registered under the author's standing instruction that amendments are made and
the study continues rather than halting at a pre-registered stop condition. The
stop condition here fired on a criterion, not on the policy, and the diagnosis
was available offline at zero run cost — which is what both gates are for.

**Verification:**

```bash
PYTHONUTF8=1 .venv/Scripts/python.exe scripts/calibrate_study_007_retrieval.py
```

Full sweep frontier, per-query figures, both bound forms, and the causality
column are written to `experiments/study_007/replay/calibration_sweep.json`.
Study 006's 270 artifacts are SHA-256 hashed before and after and compared.
