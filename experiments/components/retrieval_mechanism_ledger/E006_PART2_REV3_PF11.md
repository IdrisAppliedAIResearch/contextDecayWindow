# E006 Part 2 Rev 3 PF11 Computability Verification

**Date:** August 10, 2026
**Decision:** **FAIL - STOP BEFORE REMAINING PREFLIGHT**
**Design anchor:** `42f710a3`
**Design SHA-256:** `1A41013C3A079DD0BEDD80307D4F6B699139F889CD705457E1D874BB3D24B325`
**Authorization commit:** `38bdd153`
**Auditor execution commit:** `960c9810`
**Machine artifact:** `artifacts/e006_rev3_pf11/pf11.json`
**Machine artifact SHA-256:** `57448B3E607A0E970E8C2BB6ACC46A5147C89EDDE12974604480AE67D1E8CA3B`
**Calls:** zero model calls; zero embedding calls

## 1. Registered Gate

Rev 3 PF11 requires two independent score routes to agree with the Section 2
computability derivation. If they do not, Rev 3 stops because no registered
offline path remains.

PF11 runs before the rest of the PF1-PF11 checklist. It fails. The remaining
Preflight, parameter registration, and offline arms did not begin.

## 2. Inputs and Reconstruction

The committed Q11 trace contains 119 eligible episode identities, source turns,
and query-to-episode cosines. The store contains the corresponding 119 float32
episode vectors. The auditor normalizes those vectors and computes the 119 x 119
episode Gram matrix.

The independent vector route reconstructs a unit query in an augmented
1,025-dimensional space. Its projection onto the episode span has squared norm
`0.615112426581967`; the orthogonal residual has squared norm
`0.384887573418033`. The reconstructed unit query matches every committed Q11
cosine with maximum absolute error `9.96425164601078e-15`.

This proves the committed cosines are sufficient to realize a query vector for
the mechanism without an embedding call. The PF11 failure is not caused by a
missing or inconsistent query representation.

## 3. Two Registered Routes

### Route A - unchanged mechanism

The vector route executes the locked pseudocode after the first `top_m` hit set:

```text
c = normalize(RHO * q0 + BETA * mean(hits))
cue = normalize(W_Q * q0 + W_C * c)
score_i = cue dot episode_i
```

### Route B - registered Section 2 derivation

Section 2 instead states that `c` is the mean of the current hit vectors and
computes `c dot episode_i` and `q0 dot c` directly from that mean. This replaces
the recursive context with the latest hit mean. As a result, its score equation
contains `W_Q` and `W_C` but omits `RHO` and `BETA`, even though those parameters
change Route A.

That is a substantive equation mismatch, not a notation-only difference.

## 4. Result

The comparison exhausts both registered `m` values, all three `W_Q` values, and
both `RHO` values for the next retrieval step: 12 cells.

| m | RHO | W_Q | Maximum score difference | Full ranking equal | Next `top_m` equal |
|---:|---:|---:|---:|---:|---:|
| 3 | 0.5 | 0.3 | 0.117866 | No | Yes |
| 3 | 0.5 | 0.5 | 0.114904 | No | Yes |
| 3 | 0.5 | 0.7 | 0.078608 | No | Yes |
| 3 | 0.7 | 0.3 | 0.212404 | No | Yes |
| 3 | 0.7 | 0.5 | 0.186932 | No | Yes |
| 3 | 0.7 | 0.7 | 0.123717 | No | Yes |
| 5 | 0.5 | 0.3 | 0.081525 | No | Yes |
| 5 | 0.5 | 0.5 | 0.043188 | No | Yes |
| 5 | 0.5 | 0.7 | 0.039952 | No | **No** |
| 5 | 0.7 | 0.3 | 0.085339 | No | Yes |
| 5 | 0.7 | 0.5 | 0.098056 | No | **No** |
| 5 | 0.7 | 0.7 | 0.074150 | No | **No** |

Summary:

- Registered score agreement: **0/12 cells**.
- Full ranking agreement: **0/12 cells**.
- Next `top_m` agreement: **9/12 cells**.
- Registered maximum absolute score difference range: `0.0399517-0.212404`.

No numerical tolerance can reconcile the registered routes: every full ranking
changes, and three cells select a different next hit set.

## 5. Corrected-Recurrence Diagnostic

The auditor also evaluates a non-gating diagnostic that carries the recursive
context through Gram products:

```text
c_scores = normalize(RHO * prior_c_scores + BETA * hit_mean_scores)
q0_dot_c = normalize(RHO * prior_q0_dot_c + BETA * q0_dot_hit_mean)
```

That recurrence agrees with the independent vector route in all 12 cells, with
maximum absolute score difference `9.49240686054509e-15` and identical full
rankings.

This diagnostic localizes the defect: zero-call recursive chaining is
computable from the committed trace and Gram matrix, but **not by the derivation
Rev 3 registered**. The diagnostic is not used to pass PF11 and does not
authorize later stages.

## 6. Integrity

- Design, authorization, database, and Q11 trace are byte-hashed in the machine
  artifact.
- New comparisons use canonical episode-content SHA-256 values; source UUIDs
  only dereference committed rows.
- The PF11 source does not import or reference `q_facts_key.md`, rubric code, or
  targeted item definitions. The rank inventory is immediately projected to
  identity, source turn, and cosine.
- Gate order is design `42f710a3`, authorization `38bdd153`, auditor execution
  `960c9810`.
- The machine artifact records the launch command, auditor SHA-256, and UTF-8.

## 7. Disposition

**STOP BEFORE REMAINING PREFLIGHT.** Rev 3 says PF11 failure leaves no offline
path. Continuing with the corrected recurrence would silently repair a locked
derivation after observing its gate result. A new authorized design or
standalone amendment must register the recursive Gram equations before any
further Preflight, parameter registration, or offline arm can run.
