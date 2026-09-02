# DA-040 Compact Dependency Frontier

**Status:** `COMPLETE; COMPACT_DEPENDENCY_FRONTIER_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-039 result commit `988ce942`
**Standing:** evidence-blind protected structural reachability probe
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can final slack after the immutable DA-038 pack carry a broad frontier of exact
source-member references, separating dependency reachability from expensive
payload materialization?

DA-039 finds 17/18 residual payloads fit initially but are blocked by earlier
append-only payload consumption. A different payload score would trade which
member is displaced. This probe adds no payload and makes no substitution.

## 2. Locked Control

Use all 465 LongMem questions at 16,000 characters. Freeze DA-038's complete
identity/member sequence, order, codec, charge, actions and delivery 232. No
existing payload may be removed, replaced, reordered, recharged or re-encoded.

## 3. Reference Frontier

After the complete DA-038 pack, traverse the original baseline edge list in its
frozen order and lexical member order. For each member absent from DA-038,
append one self-delimiting local reference if it fits; continue after overflow.
Never retry a member.

A reference encodes baseline edge position and member index with DA-031's fixed
base-32 varints inside DA-038's absent sentinel. A deterministic resolver maps
it through the frozen edge list and candidate store to exactly one source
member. Charge every rendered reference character against 16,000. The source
payload remains external and uncharged; therefore this is resolver reachability,
not evidence delivery.

No question text, answer, evidence, outcome, type, similarity, fitted feature,
threshold or sweep enters order or admission.

## 4. Blind Gates

Commit all references, exact codes, resolver targets, charges and immutable
DA-038 hashes before evidence. Require 465 exact joins; exact canonical parse
and resolution; no duplicate target; positive admissions and overflows;
unchanged DA-038 charge/order; <=16,000; byte-identical replay; zero calls.
Stop unopened on any mismatch.

## 5. Outcomes and Disposition

After sealing, report how many of DA-039's 18 residual dependency sets are
fully reachable through admitted references, by question type, reference cost,
position and remaining gap.

Report `COMPACT_DEPENDENCY_FRONTIER_SIGNAL` for >=5 newly reachable residuals,
zero protected mutations and every type nonnegative. Report
`WEAK_COMPACT_DEPENDENCY_FRONTIER_SIGNAL` for 2-4 under the same guardrails.
Otherwise report `NO_COMPACT_DEPENDENCY_FRONTIER_SIGNAL`.

This endpoint does not count references as delivered facts. Any dereference,
payload scheduling, reader, runtime, fresh-transfer or adoption claim requires
a separately registered successor.
