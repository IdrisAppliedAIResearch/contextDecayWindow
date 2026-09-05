# DA-091 Typed Edge With Exact Child Stream

**Status:** `COMPLETE; TYPED_EDGE_CHILD_STREAM_SIGNAL`
**Date:** August 31, 2026
**Parent:** DA-090 result commit `4e40c200`
**Planned embedding calls:** 0
**Planned model calls:** 0

## Question

Can typed dependency metadata replace provenance-only parent payloads at the
capacity boundary while preserving the strongest order and exact target text?

## Frozen Control

Use all 8,055 sealed DA-090 targets. Preserve every DA-089-complete row and
every DA-090 child-only packet row byte-for-byte in route and cost fields. The
only eligible rows are DA-090 `EDGE_COMPONENT_PACKET_STREAM` rows.

DA-078 remains immutable. No packed payload may be removed, replaced, reordered
or recharged. No target, member, edge, score, question token, evidence label or
outcome may affect eligibility or rendering.

## Typed Edge Representation

For each eligible row, retain the already sealed parent episode, child episode,
child member and edge relation as typed out-of-band metadata. Replace the
parent-user, parent-assistant and child component stream with DA-090's exact
fixed packet stream for the child member alone. Packet size remains 1,800
characters and frame cap remains 2,048 characters.

The decoded child bytes and speaker must equal the source member exactly. The
typed edge must equal the sealed DA-090 identities. Existing noneligible rows
must retain route, frame count, peak, cumulative charge and prompt delta.

## Gates And Disposition

Require 8,055 exact joins, 798 eligible substitutions, exact child decode,
strictly lower cumulative charge on every eligible row, no peak increase, zero
DA-078 mutation, byte-identical replay and zero calls.

Report `TYPED_EDGE_CHILD_STREAM_SIGNAL` only if every gate passes. This is a
mechanical dependency representation result, not evidence delivery. Reader
recognition of typed edges, retention, stopping, runtime, fresh transfer and
adoption remain untested.

## Result

All 798 eligible edge-component streams were replaced by typed edges plus exact
child-only packets. Every substitution reduced cumulative exposure and none
increased peak frame size. The other 7,257 rows retained their DA-090 route and
cost fields exactly; DA-078 remained immutable.

Eligible cumulative savings were p10 1,076.4, p50 2,220.5 and p90 3,264.3
characters. Child exposure used p50 two frames, p50 cumulative 2,098 characters
and p50 peak 1,817 characters. Exact replay was byte-identical and made zero
model, embedding or cache calls.

This removes provenance-only parent text from the exposure path and represents
the dependency in the control plane. It does not establish that a reader can
interpret the typed edge or retain and use the streamed child.
