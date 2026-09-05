# DA-095 Scratchpad

- One representation-dominant immutable source node per child.
- Expand all other DA-093 pointers to exact literals; never drop content.
- Compare against DA-091 literal packets; DA-093 remains strongest control.
- No semantic score, question feature, evidence label, model, embedder or cache.

## Result

- 3,499/3,499 select node-local exact encoding.
- Savings vs literal p10/p50/p90: 2.50%/6.36%/14.83%.
- Retains 15.78%/27.87%/50.81% of DA-093 capacity.
- Pointer count 12/25/46 versus DA-094 median 123; exactly one source member.
- Exact decode, protected controls and replay pass; zero calls.
- Next: bind the source node once and encode local start/length coordinates.
