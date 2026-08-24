# TC-009 Report — cumulative source-session penalty

**Standing:** `REGISTERED-OFFLINE`  
**Status:** `COMPLETE`  
**Pre-registration:** `TC_009_PRE_REGISTRATION.md`  
**Pre-registration commit:** `1edf6ad7601d06a53a2819874b13e48120d13f04`  
**Pre-registration SHA-256:** `6ec7cd70874c9b0f87817d9a17ad1fb8684027922d4d51f31e932b08ac693563`  
**Final G0 commit:** `2a6b75727c6d3c8178df2a14956e51b78b8efd25`  
**Question-level artifact commit:** `f5bb3c05`  
**Registered disposition commit:** `af862ae3`  
**Descriptive attribution commit:** `b3d94d0c`  
**Date:** 2026-08-23

## Verdict

Letting every session compete again after each selection, with a small
cumulative penalty, does not preserve semantic delivery or improve breadth.
It is worse than full-budget dense at both budgets and worse than TC-008's
one-time session novelty at 32k.

> **Disposition: `DENSE_WORKS`; dynamic session spread is rejected.**

In plain terms: the penalty does what it was designed to do, but it penalizes
sessions that still contain the best evidence. Re-ranking after every pick is
not enough; the re-ranking signal must identify information the question needs.

## Registered result

The primary endpoint is paired required-identity delivery on 44 breadth
questions. The joint guardrails are breadth, combined and targeted complete
evidence. Works alpha is `.01/6`; signal alpha is `.10/6`.

| Budget | Endpoint | Dense | Dynamic | Gains | Losses | Net | Dense p | Reading |
|---:|---|---:|---:|---:|---:|---:|---:|---|
| 16k | Breadth identities | 129 | 121 | 1 question / 1 id | 8 questions / 9 ids | -7 / -8 | .0195 | Adverse; no breadth signal |
| 16k | Breadth complete | 16 | 12 | 0 | 4 | -4 | .0625 | Fails noninferiority |
| 16k | Combined complete | 749 | 713 | 7 | 43 | -36 | 1.05e-7 | Dense guardrail fires |
| 16k | Targeted complete | 643 | 624 | 7 | 26 | -19 | .000659 | Dense guardrail fires |
| 32k | Breadth identities | 157 | 152 | 2 questions / 4 ids | 9 questions / 9 ids | -7 / -5 | .0327 | Adverse; no breadth signal |
| 32k | Breadth complete | 27 | 21 | 0 | 6 | -6 | .0156 | Fails noninferiority |
| 32k | Combined complete | 810 | 794 | 4 | 20 | -16 | .000772 | Dense guardrail fires |
| 32k | Targeted complete | 680 | 674 | 2 | 8 | -6 | .0547 | Adverse |

The registered dense direction clears at both budgets: dynamic produces no
breadth-completeness gain, loses required breadth identities, fails the joint
complete-evidence conditions, and fires dense guardrails. The frozen reader
fallback is therefore the dense control. No reader answers were generated.

## What the cumulative penalty changed

At `lambda=.03`, every real trace permits a repeat session to win before all
sessions are represented. The rule is not a hard floor. Preflight observed
consecutive same-session wins on 606 of 871 questions, up to five in a row.
At 16k the selected payload represents a median 29 sessions and takes at most
four candidates from one session; at 32k those figures are 30 and six.

That behavioral flexibility did not protect evidence. Post-run attribution
finds that most required-identity losses are unique to the cumulative penalty:

| Budget | Dynamic-only losses | Common fixed-50/50 losses | Shared with one predecessor | Dynamic-only gains |
|---:|---:|---:|---:|---:|
| 16k | 34 | 7 | 13 | 6 |
| 32k | 22 | 0 | 1 | 7 |

The 26 targeted evidence carriers displaced on dense-complete questions at
16k have dense ranks 24–57, median 38.5. At 32k the eight displaced carriers
rank 60–112, median 71. These are candidates the available relevance budget
can reach; the dynamic spread order moves them behind other sessions.

## Breadth questions

Dynamic spread produces one breadth-share gain at 16k and two at 32k, but no
complete-evidence gain. It causes four complete breadth losses at 16k and six
at 32k. The 32k gains include three candidates for “What job might Maria pursue
in the future?”, moving zero of three required identities to all three, but
that question still has additional required evidence and remains incomplete.

The losses are not confined to one source session. Ten distinct required
source sessions lose a breadth identity at 16k; eight do at 32k. At 32k,
examples made incomplete include “Where has Maria made friends?”, “What causes
does John feel passionate about supporting?”, and “What movies have both
Joanna and Nate seen?” The penalty spreads misses rather than curing them.

Seven questions per budget show the registered identity/completeness
disagreement: their evidence count changes without changing whether all
evidence is present, or vice versa. This is why required-identity share and
complete delivery were both retained.

## Integrity and scope

G0 passed 2,226 tests, reproduced 5,226 TC-008 payload anchors and 1,742 dynamic
payloads, checked all 296,166 full-order states and 69,961 admitted states, and
matched a two-process prefix. The registered run's two complete workers match
on frozen selection digest `629bdfa1…`, per-question digest `680835bf…`, and
diagnostics digest `cc15bf59…`. Run calls, embedding calls and cache misses are
zero. The final repository suite is 2,228 passed. The two 116 MB immutable gzip artifacts use Git LFS only for transport;
their accepted raw SHA-256 bytes remain the registered digests.

This is availability on used LoCoMo development data. It does not test reader
use, tune lambda, optimize the 50/50 share, choose an enterprise budget, or
rule out query-conditioned coverage signals. It closes cumulative count-based
source-session penalty as the proposed repair. Dense keeps the full budget.
