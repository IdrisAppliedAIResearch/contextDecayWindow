# DA-037 Report

## Verdict

`NO_LONGMEM_SENTINEL_ATOMIC_SIGNAL`

The sentinel composition raises complete delivery from DA-033's 222 to 230,
with nine gains and one loss. Net gain is eight and the paired exact p-value is
.021484375, but the registered zero-loss requirement fails. DA-031's 211
deliveries remain fully protected.

The blind codec selected sentinel on 453/465 questions and saved 723 characters
at the median. Six gains resolve initial-size blockers, two resolve prior
atomic consumption, and one resolves a multi-carrier conjunction. This confirms
that exact representation capacity reaches the intended residual classes.

The single loss also identifies the structural defect: independently replaying
the same atomic traversal under a different codec can change which tail members
fit. Preserving only DA-031 is insufficient once DA-033 is the stronger order.
The next construction must freeze the complete DA-033 member sequence, re-
encode it exactly, and allow append-only admissions afterward.

Blind allocation SHA-256 is
`a4e33b71295547c2ab04e016e1c9d8e2fa629e8d345001be039f5c881e046573`;
outcomes replay byte-identically at
`fef6f6af2bc789692814a835dd56c4ea104604f019082e81f0e04096fb9b7b0f`.
Model, embedding and cache calls: zero.
