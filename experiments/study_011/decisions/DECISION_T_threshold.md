# Decision — T is locked at 6 of 13

**Study:** 011 — STM and LTM Tier Isolation and Joint Operation
**Registration:** `experiments/study_011/pre_registration.md`, §4.1
**Pre-registration SHA-256:** `350d9763691c93b2e057cc0c10bdd7f19d8a78c7e169f9e40ef0571d69e5e7f4`
**Status:** AUTHORIZED — program author, August 6, 2026
**Applies to:** G2, G3, G4
**Committed before:** the G6 ablation and every live run, as §4.1 requires

---

## 1. The decision

> **T = 6 of 13.**

G2, G3 and G4 each read "≥T of 13 probes". T is 6.

A second reading is settled here because the same measurement showed the
registration's text admits two, and one of them is unusable:

> **"Delivers a K episode" means the K path delivered an episode that the
> recency path would not have carried anyway.**

---

## 2. Why "K episode" needed settling

G1 requires Arm A to deliver **0 K episodes** at all 13 probes. Arm A has
no K tier. Under the other available reading — an episode that *is* a K
candidate, wherever it came from — **Arm A delivers K episodes at 4 of 9
windows**, because the recency window carries episodes that would also
have cleared the threshold. G1 would fail by construction on the arm it
was written to certify.

The same reading inflates G2 and G3 in the opposite direction: an episode
already in the recency candidate set renders in `recent_context`, so
crediting it to the similarity tier credits that tier with material
recency delivered anyway. Turn 115 is the clean case — one K candidate,
already a recency candidate, contributing nothing.

Both failures are the program's recurring class: a count that can move
while the property it certifies does not. The K-only reading is the one
under which G1 is satisfiable and G2/G3 mean what they say.

This is an ambiguity resolved from the criterion text before any affected
result was read, not a criterion changed after observing one.

---

## 3. The measurement T was set from

`experiments/study_011/gates/achievability/`, run at commit `ab76f863`
on a clean tracked worktree, zero model calls, zero embedding calls,
packer imported unchanged from IC-001.

| Artifact | SHA-256 |
|---|---|
| `achievability.json` | `2fa1afbe032fc07497574dafbfd359c9c5abda8e68c89ce7a74a80771535c470` |
| `k_availability.csv` | `9e460c057ec9a12b74ef7639bf90d902c968355e84f17bd4d0a1bcc9325920a4` |
| `no_model_call_audit.json` | `e560ec0260cc506c24973db1ea98f8d9385ae1f895af3060921bca05d823fc49` |
| `run_header.json` | `cd844c238d51af2b306ee2d299c7e2114537750968684f4db0e95839d7c942d8` |

**Ceilings, K-only:**

| Arm | Windows | Questions |
|---|---:|---:|
| A — STM only | 0 / 9 | 0 / 13 |
| B — LTM only | 6 / 9 | 8 / 13 |
| C — both, K-first | 6 / 9 | 8 / 13 |
| D — both, recency-first (deployed) | 1 / 9 | 2 / 13 |

**T = 6 sits two below the ceiling of 8 and three above the deployed
order's 2.**

### 3.1 Thirteen questions, nine windows

Q3 and Q12 share turn 114, Q6 and Q9 share 117, Q7 and Q10 share 118.
Questions sharing a turn share one retrieval window exactly, so they
move together and cannot be counted as independent evidence. Q13 scores
rule compliance across turns 112–120 and has no window at all.

The count is kept in the registered units — out of 13 — so that no
amendment to locked wording is needed. It is a re-expression of the
window count, not a second measurement, and every report of a T-governed
gate states both.

### 3.2 What the slack is for

Because questions move in blocks, losing one window costs 1 or 2. T = 6
tolerates the loss of one two-question window (114 or 117) **or** two
single-question windows. That is the margin for the live stores
diverging from the proxy the ceiling was measured on.

### 3.3 Four questions can never count

**Q7, Q8, Q10, Q13.** Turns 118 and 119 hold no K candidate at K = 0.48,
so no packing order delivers K there; Q13 has no window. The attainable
maximum is therefore 9 of 13 in principle and 8 on the measured store. A
threshold near 13 would have failed by construction, which is what §4.1
exists to prevent.

---

## 4. The limitation this does not remove

The ceiling was measured on the corrected Tier 6 run's committed
candidates — a store built under recency-first packing at a
60,595-character budget. Study 011's arms are live runs whose stores do
not exist yet, and **Arm B has no recency window, so its store diverges
from turn 1 by construction.** Candidate identity does not depend on the
packing budget, so the measurement bounds the ceiling on *this* store; it
does not predict Arm B's.

§9's registered risk stands: if the achievable value turns out lower than
T on the arms' own stores, report the value and stop. **Do not lower T to
pass.**
