# DA-003 Evidence-Blind Edge Utility Report

**Status:** `STOPPED_AT_CAUSAL_ACCOUNTING`
**Standing:** post-outcome exploration on spent NF-004 LoCoMo
**Protocol commit:** `16d4bdee`
**Blind-edge commit:** `df20aca3`
**Calls:** 0 embedding, 0 model, 0 cache misses
**Date:** August 29, 2026

## Stop

The first evidence join fired the protocol's causal-accounting stop before any
feature model ran. The registered `BENEFIT` label required the admitted
neighbor itself to carry all evidence missing from `DIRECT`. That identity is
false for some one-edge counterfactuals.

Exact packing is skip-on-overflow, not prefix truncation. Inserting one neighbor
changes the running character total, which changes later fit/skip decisions.
Consequently, a different low-ranked candidate can enter downstream and carry
the missing evidence even when the linked neighbor does not.

Across 25,941 primary edge rows inspected only to characterize the fired stop:

- 48 complete-item gains are carried by the linked neighbor as registered;
- 9 additional gains are downstream packing side effects;
- 40 edges cause complete-item harm;
- 25,844 are neutral.

The first mismatch is `conv-49`, source index 165. A rank-5 seed promoted its
rank-189 neighbor. The neighbor entered, but a different newly fitted candidate
carried the missing evidence. Calling this neighbor utility would assign causal
credit to the wrong unit.

## Consequence

No univariate AUC, grouped model, gate, threshold, or predictor result is
reported. The blind artifact remains valid: 26,100 unique first-emitter edges,
4,731 duplicate nominations removed, byte-identical replay, and zero calls.

The next rule must operate on the actual decision object: the complete packing
perturbation produced by admitting an edge, including every newly admitted and
displaced candidate. An edge-local benefit score alone cannot certify the
result because the packer has nonlocal state.

This stop authorizes no selector, implementation change, reader, or adoption.
