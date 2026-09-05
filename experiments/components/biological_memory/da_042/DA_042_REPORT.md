# DA-042 Report

## Verdict

`CONTROL_PLANE_HEAD_SIGNAL`

Moving the dependency head from rendered evidence into the context envelope
makes all 18 DA-038 residual dependency sets exactly addressable with zero
rendered-character delta and zero protected mutations.

| Residuals | Control-plane reachable | Unreachable |
|---:|---:|---:|
| 18 | **18** | **0** |

The blind envelope attaches 461 typed heads resolving 8,055 absent source
members. Every DA-038 prompt keeps its exact identity/member order and charge;
the head contains only a resolver handle, not payload text or evidence labels.

The sequence of results isolates the architecture:

- DA-040: flat five-character member references reach 7/18.
- DA-041: one rendered linked-list head reaches 17/18.
- DA-042: the same head in control-plane metadata reaches 18/18.

This is the upstream separation the earlier data-architecture hypothesis
predicted: facts remain immutable payload nodes, dependency links remain a
separate navigable graph, and the prompt budget no longer has to store the
graph merely to preserve addressability.

This does not raise the 232 delivered-fact score. The remaining problem is how
and when a reader dereferences the graph and materializes payloads without
reintroducing displacement. Reader/tool behavior, runtime and fresh transfer
remain unvalidated.

Blind envelope SHA-256 is
`e1f4ece6c1e55010ee7825a4ff8c56778834a8ae03cc6fa9eea5795a7ee0d7cc`;
reachability replays byte-identically at
`4fbbd7f2e8f9443c5ca552ae2cef40342eda71934fa19f093cce1305959e5896`.
Model, embedding and cache calls: zero.
