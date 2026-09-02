# DA-045 Report

## Verdict

`REPLACEABLE_NODE_STREAM_SIGNAL`

A fixed first-32 traversal exposes all 18 residual payloads while keeping the
DA-038 prompt immutable and limiting peak auxiliary capacity to one 2,048-
character frame.

| Residuals | Exposed | Peak cap | Prompt mutations |
|---:|---:|---:|---:|
| 18 | **18** | 2,048 chars | 0 |

The result separates peak capacity from cumulative work:

| Through required node | p50 | p90 |
|---|---:|---:|
| Cumulative exposed chars | 5,569 | 17,692.2 |
| Exposed frames | 7 | 16 |
| Peak frame chars | 1,851.5 | 2,037.1 |

This is materially different from DA-044's 14,817-character simultaneous page.
The stream never adds more than 2,048 characters at once and reaches every
residual type, including all multi-session and temporal cases. It still spends
tokens over time and skips oversized non-required nodes; the mechanism is
bounded working capacity, not free retrieval.

Most importantly, sequential exposure is not reader success. A reader must
recognize the relevant frame, retain or use it after replacement, and stop
appropriately. Those are now the remaining causal questions. Testing them
requires a separately registered reader/tool protocol; another offline
substitution score would not answer them.

Blind stream SHA-256 is
`ba527732771e4bcba3d7e5b289b5cb8f3f9daf9b53f0601acac293e401ef2a0a`;
exposure replays byte-identically at
`174204459562cee0c8062632b607e1e3960add2ab418bf2f922871dbaf818fc1`.
Model, embedding and cache calls: zero.
