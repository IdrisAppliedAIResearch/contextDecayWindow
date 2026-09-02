# DA-045 Replaceable Dependency-Node Stream

**Status:** `COMPLETE; REPLACEABLE_NODE_STREAM_SIGNAL`
**Date:** August 30, 2026
**Parent:** DA-044 result commit `7e8c89b9`
**Standing:** evidence-blind protected streaming-materialization probe
**Planned embedding calls:** 0
**Planned model calls:** 0

## 1. Question

Can fixed traversal expose the residual dependency payloads with bounded peak
capacity by replacing one transient node frame at a time, rather than flooding
a large auxiliary page?

DA-044 spends a median 14,817 simultaneous characters for five gains. DA-043
finds every residual within depth 30 and every required node <=2,048 rendered
characters. This fixes depth 32 and frame cap 2,048 before outcomes.

## 2. Locked Prompt and Graph

Use all 465 LongMem questions. Freeze DA-038's prompt byte-for-byte and DA-042's
complete ordered dependency frontier. No prompt payload, graph node, edge or
order may be changed.

## 3. Streaming Frames

Traverse frontier nodes 1 through 32 in order. Render each node with DA-044's
canonical ordinal/speaker/text block. If its block is <=2,048 characters,
expose it in a transient frame; otherwise record overflow and advance. Each new
frame replaces the previous frame. The protected prompt remains present and
unchanged; at most one frame is present at once.

Report both peak frame characters and cumulative exposed characters. No
question text, answer, evidence, outcome, type, similarity, fitted feature,
threshold or sweep enters traversal or admission.

## 4. Blind Gates

Commit every frame/overflow, exact payload identity, serialized block and cost
before evidence. Require 465 exact joins; canonical decode; frozen prefix order;
depth <=32; positive frames and overflows; peak <=2,048; unchanged DA-038
prompt; byte-identical replay; zero calls. Stop unopened on mismatch.

## 5. Outcomes and Disposition

Report how many DA-039 residual sets are exactly exposed in at least one frame,
by type and blocker, plus peak/cumulative chars, frames visited and cumulative
characters through each required node.

Report `REPLACEABLE_NODE_STREAM_SIGNAL` for >=17 exposed residuals, zero prompt
mutation and every type nonnegative. Report `WEAK_REPLACEABLE_NODE_STREAM_SIGNAL`
for 12-16 under the same guardrails. Otherwise report
`NO_REPLACEABLE_NODE_STREAM_SIGNAL`.

Sequential exposure is not simultaneous evidence delivery or reader use. A
reader must still recognize relevance and retain/use a fetched node; runtime,
stopping, fresh transfer and adoption remain separate.
