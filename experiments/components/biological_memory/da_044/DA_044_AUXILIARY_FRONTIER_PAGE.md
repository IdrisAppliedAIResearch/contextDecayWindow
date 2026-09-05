# DA-044 Fixed Auxiliary Frontier Page

**Status:** `COMPLETE; WEAK_AUXILIARY_FRONTIER_PAGE_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-043 result commit `53fdb0e4`
**Standing:** evidence-blind protected LongMem materialization probe
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Does a fixed first-32 page of dependency payloads convert DA-042's graph
addressability into exact evidence delivery when materialized in separate
bounded capacity without changing the DA-038 prompt?

DA-043 finds every residual at one node, maximum depth 30. This fixes page depth
32 before outcomes. The experiment adds capacity and must report that cost; it
does not test a better ranking score.

## 2. Locked Control

Use all 465 LongMem questions. Freeze DA-038's complete 16,000-character prompt
identity/member sequence, order, codec, charge, actions and delivery 232. No
control payload may be removed, replaced, reordered, recharged or re-encoded.

## 3. Auxiliary Page

From DA-042's deterministic absent-member frontier, take nodes 1 through 32 in
order. Render each source member canonically as a self-delimiting ordinal,
speaker and exact text block. Append the longest contiguous prefix whose exact
serialized size is <=16,000 characters; stop at the first overflow.

The page is a separate transient buffer. Its characters are fully charged and
reported but do not displace the protected prompt. No question text, answer,
evidence, outcome, type, similarity, fitted feature, threshold or sweep enters
page order or admission.

## 4. Blind Gates

Commit exact page nodes, payload identities, serialized blocks and charges
before evidence. Require 465 exact joins; canonical byte-identical decode;
prefix-only nodes; depth <=32; positive pages and at least one overflow or
depth truncation; page <=16,000; unchanged DA-038 prompt charge/order;
byte-identical replay; zero calls. Stop unopened on mismatch.

## 5. Outcomes and Disposition

Report complete exact evidence delivery against DA-038, question types,
DA-039 blocker rescues, page chars/nodes, added characters per gain and the
250 one-hop ceiling.

Report `AUXILIARY_FRONTIER_PAGE_SIGNAL` for >=12 gains, zero losses and every
type nonnegative. Report `WEAK_AUXILIARY_FRONTIER_PAGE_SIGNAL` for 5-11 under
the same guardrails. Otherwise report `NO_AUXILIARY_FRONTIER_PAGE_SIGNAL`.

Any gain is attributed to fixed structurally targeted auxiliary capacity. No
reader, runtime, fresh-transfer or adoption claim follows.
