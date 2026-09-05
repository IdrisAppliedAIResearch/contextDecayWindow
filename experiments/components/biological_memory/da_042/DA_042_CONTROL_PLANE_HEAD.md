# DA-042 Control-Plane Dependency Head

**Status:** `COMPLETE; CONTROL_PLANE_HEAD_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-041 result commit `f0353238`
**Standing:** evidence-blind protected architecture probe
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can the complete deterministic dependency frontier remain exactly addressable
with zero rendered-budget displacement when its head lives in the context
envelope rather than the evidence text?

DA-041 reaches 17/18 residuals with a three- or five-character prompt marker.
The final miss has no marker slack. This tests placement of the same head, not
a new order, score, dependency graph or payload policy.

## 2. Locked Prompt

Use all 465 LongMem questions at 16,000 characters. Freeze DA-038's complete
rendered identity/member sequence, order, codec, charge, actions and delivery
232 byte-for-byte. The treatment prompt must have exactly the same charge and
payload identities as DA-038.

## 3. Context Envelope

Construct the same ordered unique absent-member list as DA-041. Store one
typed `dependency_head` field in the context object, outside the rendered
evidence string and its 16,000-character budget. The field resolves through
the frozen edge/member order to the complete target list.

The head has zero rendered characters but is not free storage: it contains only
a typed handle to the already frozen resolver sequence, not source text,
question features, scores, evidence labels or payloads.

## 4. Blind Gates

Commit every head, resolved target list and immutable DA-038 hash before
evidence. Require 465 exact joins; every nonempty frontier has one typed head;
exact complete resolution; byte-identical DA-038 charge/order; zero rendered
character delta; byte-identical replay; zero calls. Stop unopened on mismatch.

## 5. Outcomes and Disposition

Report how many of DA-039's 18 residual sets are fully resolver-reachable.

Report `CONTROL_PLANE_HEAD_SIGNAL` for >=17 newly reachable residuals, zero
prompt mutation and every type nonnegative. Report
`WEAK_CONTROL_PLANE_HEAD_SIGNAL` for 12-16 under the same guardrails. Otherwise
report `NO_CONTROL_PLANE_HEAD_SIGNAL`.

This is graph addressability only. It does not count handles as delivered facts
or establish dereference, payload scheduling, reader use, runtime, fresh
transfer or adoption.
