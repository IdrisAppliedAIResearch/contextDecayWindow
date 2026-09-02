# DA-060 Scratchpad

## 2026-08-31 - Registration

- All unordered query token pairs in nested first-appearance order.
- Exact two-token session co-occurrence; union postings, no singleton fallback.
- Seal routes before required-session join.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Complete required-session coverage 465/465.
- Routed sessions p50 43; fraction p50 .909/p90 .957.
- Only one median session better than singleton union; pair union remains broad.
- Next test exact contiguous query bigram postings.
