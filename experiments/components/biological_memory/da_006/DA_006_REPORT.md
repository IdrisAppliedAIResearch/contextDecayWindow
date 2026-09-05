# DA-006 Reserved Headroom and Compact Link Report

**Status:** `STOPPED_AT_CAUSAL_ACCOUNTING`
**Protocol commit:** `6d9edf91`
**Blind-selection commit:** `78f80701`
**Standing:** post-outcome diagnostic on spent NF-004 LoCoMo
**Calls:** 0 embedding, 0 model, 0 cache access
**Date:** August 29, 2026

## Stop

The evidence join fired the registered causal-accounting stop. Exact
skip-on-overflow packing under `16,000 - R` does not necessarily produce a
subset of the 16k direct pack. Rejecting an earlier large pair can allow a later
pair to fit, so changing the core budget can itself add evidence before any
link payload is rendered.

One `PAIR_R512` gain is carried by this core-packing side effect rather than the
linked pair. The protocol requires every gain to be link-carried, so no
registered arm result or disposition is reported.

## Post-Stop Characterization

The complete opened matrix is retained only to characterize the stop:

| Arm | Link-carried gains | Core side-effect gains | Losses |
|---|---:|---:|---:|
| `PAIR_R256` | 10 | 0 | 73 |
| `TURN_R256` | 30 | 0 | 73 |
| `PAIR_R512` | 43 | **1** | 123 |
| `TURN_R512` | 35 | 0 | 123 |
| `PAIR_R1024` | 48 | 0 | 220 |
| `TURN_R1024` | 35 | 0 | 220 |
| `PAIR_R2048` | 46 | 0 | 456 |
| `TURN_R2048` | 34 | 0 | 456 |

Even descriptively, prospective reservation loses far more edge actions than
links recover. Compact turns improve fit at 256 characters and produce 30
link-carried gains versus 10 for full pairs, but reservation still causes 73
losses.

## Consequence

The next core must be an immutable subset of `DIRECT_16K`, not a fresh replay
at a smaller budget. The mechanically valid construction is to retain a prefix
of the already selected direct identities and drop only its suffix to create
headroom. That isolates reservation loss from skip-on-overflow rerouting.

No reserve, renderer, reader, production change, or adoption is authorized.
