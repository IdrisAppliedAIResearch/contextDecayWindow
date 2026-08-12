# DMR-004 Amendment 001 — one `LIST_MEMBER` obligation carrying N, not N obligations

**Document type:** Standalone amendment (`AGENTS.md` §5)
**Amends:** `../DMR_004_PRE_REGISTRATION.md`, SHA-256
`fd99a9175a5d8048038d5e4d5b70e6a9091c90f71731026dbfdd68dd9eefcfda`, committed
at `6ea982fa`
**Status:** `APPLIED BEFORE IMPLEMENTATION`
**Date:** August 12, 2026

The locked pre-registration is not edited. This file is the change.

## 1. Trigger and evidence

The pre-registration's §4 step 2 says an `ENUMERATE_N` plan emits "N
`LIST_MEMBER` obligations". Its §6 gate G5 requires that every obligation span
be "non-overlapping with its siblings", at a bar of 100%.

These cannot both hold. The queries that trigger `ENUMERATE_N` do not contain N
distinct textual spans to point at:

> *What is the order of the three trips I took in the past three months, from
> earliest to latest?*

The three trips are not in the query. There is one list request and one span.
Emitting three obligations gives three identical spans, which are overlapping
siblings, so **G5 fails by construction on every `ENUMERATE_N` plan**. A gate
that no admissible result can pass is the exact defect that stopped DMR-001 —
its G3 largest-event-share bar was unreachable for any session shorter than
four times the size cap, and it was locked without anyone checking.

Some queries do carry N spans — *"Which three events happened in the order from
first to last: A, B, and C?"* — but most do not, and a rule that emits N
obligations only when N spans happen to be present is new design, not a repair.

## 2. Change

An `ENUMERATE_N` plan emits **one** `LIST_MEMBER` obligation, whose
`requested_count` is N and whose span is the list request. `support_mode`
remains `N_DISTINCT`.

Nothing else changes. `N_DISTINCT` already carries the cardinality to a
downstream controller through `requested_count`, which is the field §2 defines
for it, so no information is lost.

## 3. Rationale

This repairs a contradiction between two clauses of the same locked document.
It does not make any criterion easier:

- G5's bar stays at 100% and now has an admissible passing result.
- G_J, G3 and G4 are untouched; `ENUMERATE_N` is not a gated class.
- The `FINITE` completeness mode of `ENUMERATE_N` is unchanged, so the
  finite/open statistic is unchanged.

`AGENTS.md` §5 permits an amendment that repairs a protocol contradiction and
forbids one that eases a criterion after results are known. **No result is
known.** The compiler does not exist at the time of this commit, and the
holdout has not been annotated.

## 4. Exclusions

- No gate bar is changed.
- No class is added, removed, or moved in the precedence order.
- The development gold is untouched.
- This amendment does not authorize any second change to the registration. A
  further contradiction gets its own amendment.

## 5. Authorization

Made by the implementing agent under `AGENTS.md` §5 during implementation, and
reported to the author in the same session rather than folded silently into the
code. If the author prefers the alternative repair — emitting N obligations
only where N distinct spans exist in the query text — that is a new design
decision and needs its own amendment; it is not what this one does.
