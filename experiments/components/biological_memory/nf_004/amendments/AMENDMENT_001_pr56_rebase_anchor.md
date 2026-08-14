# NF-004 Amendment 001 - PR #56 Rebase Anchor

**Status:** `AUTHORIZED BEFORE IMPLEMENTATION OR HOLDOUT ACCESS`
**Trigger:** user-requested merge cleanup for PR #56
**Original registration commit:** `c9d55b71`
**Rebased registration commit:** `95f0d25c`
**Date:** August 13, 2026

## Trigger and evidence

The user explicitly requested merging PR #56 so the branch tree would remain
simple. PR #56 was already merged remotely at `4b6ddb59` when checked. The
clean NF branch was rebased from PR #56's head `5bfbadc6` onto that merge commit.

The rebase occurred after NF-004 registration but before any NF-004
implementation, vector capture, preflight gate, holdout retrieval, or outcome.
It changed commit IDs while preserving file blobs byte-for-byte:

| Role | Original | Rebased | Git blob | Identical |
|---|---|---|---|---|
| Ranking-budget control plan | `cddb1a86` | `8c940d8b` | `083ce689f093c414e75fc578b6f21b70a14070e8` | yes |
| Holdout metadata inventory | `30a391ac` | `44a9a796` | `4cf80a961cd43aa73b3391907df1d6a29badcdf7` | yes |
| NF-004 pre-registration | `c9d55b71` | `95f0d25c` | `bddc41b0904fedb7dd3a8ee66bea154e7da0fc48` | yes |
| Three-arm evidence artifact | `8a41bce4` | `0b6993c3` | `cf6cc98963dc556c697fe8b55e0e9d83585880a5` | yes |

The full commit order is preserved. The pre-registration remains after all
development outcomes and before every NF-004 implementation file.

## Change

For future NF-004 gates and reports, `95f0d25c` is the executable registration
commit and `8c940d8b` is the executable control-plan commit. Historical artifacts
that record the original SHAs remain unchanged; this amendment supplies the
one-to-one mapping. G0 must verify both the rebased commit and the locked file's
LF SHA-256. The locked pre-registration itself is not edited.

## Rationale

Commit identity cannot survive a rebase even when content and order do. An
explicit mapping preserves the integrity trail without pretending the old SHA
is reachable from the cleaned branch or silently rewriting the registration.

## Exclusions

This amendment changes no corpus, split, population, candidate, score, vector,
budget, endpoint, statistic, threshold, tier, gate, stop, live boundary, or
authorized run. It does not make any criterion easier and was recorded before
any NF-004 outcome existed.

## Authorization

The user's August 13, 2026 instruction to merge PR #56 so the branch tree stays
simple authorizes the topology change. It does not authorize any scientific
change; none is made.
