# DA-041 Constant-Cost Frontier Head Reference

**Status:** `COMPLETE; FRONTIER_HEAD_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-040 result commit `4f478b0a`
**Standing:** evidence-blind protected structural reachability probe
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can one canonical head reference expose the complete deterministic dependency
frontier at constant metadata cost after the immutable DA-038 pack?

DA-040 makes 7/18 residuals resolver-reachable with five-character per-member
references, but 11 remain because metadata cost grows linearly. The original
baseline edge order and lexical member order already define a deterministic
linked sequence, so individual member addresses may be redundant.

## 2. Locked Control

Use all 465 LongMem questions at 16,000 characters. Freeze DA-038's complete
identity/member sequence, order, codec, charge, actions and delivery 232. No
payload may be removed, replaced, reordered, recharged or re-encoded.

## 3. Head Reference

Construct the ordered unique list of members absent from DA-038 by traversing
the original baseline edge list and lexical member order. If the list is
nonempty, append the canonical code `sentinel + H + sentinel` when it fits.

The deterministic external resolver interprets the marker as the head of that
entire immutable list; advancing follows the sealed order until exhaustion.
Exact resolution must reproduce every absent `(neighbor_id, member)` target.
Charge the complete marker against 16,000. External payloads remain uncharged.

No question text, answer, evidence, outcome, type, similarity, fitted feature,
threshold or sweep enters construction or admission.

## 4. Blind Gates

Commit marker codes, full resolved target lists, charges and immutable DA-038
hashes before evidence. Require 465 exact joins; canonical parse; exact complete
resolution; positive admissions and overflows; unchanged DA-038 charge/order;
<=16,000; byte-identical replay; zero calls. Stop unopened on any mismatch.

## 5. Outcomes and Disposition

Report how many of DA-039's 18 residual dependency sets are fully reachable
through admitted heads, by type and blocker.

Report `FRONTIER_HEAD_SIGNAL` for >=12 newly reachable residuals, zero protected
mutations and every type nonnegative. Report `WEAK_FRONTIER_HEAD_SIGNAL` for
5-11 under the same guardrails. Otherwise report `NO_FRONTIER_HEAD_SIGNAL`.

This is external-resolver reachability, not delivered evidence. Dereference,
payload scheduling, reader, runtime, fresh transfer and adoption require a
separately registered successor.
