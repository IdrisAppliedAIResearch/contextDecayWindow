# TA-001 Final Design Lock

**Date:** August 11, 2026
**Status:** LOCKED - PART 2 AUTHORIZED
**Pre-registration commit:** `23cff2d8da6e864363b05d2438398f9b60c8893b`
**Authorization commit:** `43d4e764ef95cd1b89a6037d925824a686221991`
**Amendment 001 commit:** `6ffe9b7c382b486e0d77dcd170e966b8aa507670`
**Implementation commit:** `1c786b758ad8dfce76d675d8a125958ffb6e02a2`
**Part 1 commit:** `0ea39da6fa66b23773593fdff36bdc28a433bad5`

## 1. Bound artifacts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| Process-1 exploration | 592,075 | `A18C91D4251A5A6ACA8E2FB6B37ED96E86E64798EA30E3DB76FF2894399FDDF` |
| Process-1 query traces | 440,346 | `94BD23AA1ADAC7F5B40FBBEBA81915B21E76347DFECB6BB68FD99DB5114D43FD` |
| Two-process comparison | 423 | `2E6EFB355A16C96BF924F6B7155066052FAB72332B087C92E901B9B99CF66C3C` |
| Component source | 7,370 | `2DF0617542728E57A0FD53E421199ACDCB71F18E1AA20DF283A44C9631C471F1` |
| Exploration source | 20,161 | `17868F76EE456C88902567A05D9644F994F42C09D6E906265222588F13677D6E` |

The deterministic Part 1 digest is
`54983E565475AFD17862C9AEE46D12018DC344206ED9CCB3A60C2E3774DA50A5`.
Fresh-process comparison status is `PASS`.

## 2. Locked mechanism

Part 2 retains the pre-registered policy without revision:

```text
CANDIDATE_QUOTA = 15
TEMPORAL_RADIUS = 1
BUDGET_CHARS = 32000
TIE_BREAK = ascending episode content SHA-256
NEIGHBOR_TIE_BREAK = ascending episode content SHA-256
```

C0 is the first 15 episodes in fixed-query cosine order. T1 iterates that same
complete rank stream; for each unseen seed it admits the seed and then the
eligible `t-1` and `t+1` episodes in content-hash order, deduplicates, does not
recursively expand neighbors, and stops at 15. Both arms use the same whole
episode representation and authoritative skip-overflow 32,000-character
packer.

## 3. Part 1 disposition

All seven Part 1 eligibility conditions passed on Q11 and 24 sealed holdout
queries:

- exact 15 unique candidates in both arms;
- every neighbor at temporal distance one from its recorded parent;
- direct-query seed order preserved;
- every payload within 32,000 characters;
- exact committed Q11 C0 candidate, packed-identity, payload, and character
  reproduction;
- identical deterministic digest in two fresh processes;
- forbidden import and planted path sentinels passing.

The mechanism is stateless. The 25-query trace produced distinct candidate
sequences rather than a constant output. Boundary, duplicate, and quota-stop
events are retained in the bound artifact.

No answer key, required fact, domain outcome, recall value, or art outcome was
opened to make this decision.

## 4. Part 2 authorization

The original authorization covers PF1-PF10 and sealed offline measurement after
this lock. Part 2 must apply G1-G5 exactly as written in the pre-registration
and stop at the first failure. It may not tune or replace the locked mechanism.

The conditional 35-turn ablation remains authorized only if every offline gate
passes and a separate calibrated run lock is committed before inference. A
121-turn live run remains unauthorized.
