# DA-096 Scratchpad

- Preserve DA-095 dominant node and exact local spans.
- Bind source distance once; local pointers carry only start and length.
- DA-095 is immutable per-row fallback; no expansion or displacement.
- Zero model, embedder and cache calls.

## Result

- 3,458/3,499 select (98.83%).
- Incremental savings vs DA-095: 0.44%/0.956%/2.13%; median misses 1%.
- Absolute savings vs literal: 3.09%/7.30%/16.54%.
- Exact decode, one source, protected controls and replay pass; zero calls.
- Close rendered binding header. Next: typed control-plane node binding with
  local-span payload only.
