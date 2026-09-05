# DA-007 Amendment 001 - Dialogue Identity Mapping

**Date:** August 29, 2026
**Timing:** after protocol commit `ea29c8f9`; before implementation or outcomes

DA-006 stores the frozen `TURN` member index for rejected links but omits its
intended dialogue identity. DA-007 may read the byte-locked LoCoMo corpus only
to map each sealed candidate pair and frozen member index to dialogue IDs.

The corpus cannot change direct order, reserve, prefix, payload type, member
choice, cost, fit decision, arm, endpoint, or analysis. No evidence, answer,
category, cache, embedding, or model access is permitted in the blind process.
