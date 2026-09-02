# DA-067 Scratchpad

## 2026-08-31 - Registration

- Entire DA-066 stream is an immutable prefix.
- Append exact unigram occurrence anchors plus fixed radius 1-5 neighbors.
- Query-token first-appearance order, then episode source order.
- Signal requires >=.98 complete reachability and zero displacement.
- Seal before answer-marker join.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- Complete required-episode reachability 465/465; zero displacement.
- Median stream size 228 episodes; p90 248.
- Twenty-seven gains beyond DA-066.
- Gain-only added traversal p50 62/p90 128 episodes; max 157.
- Gain-only completion position p50 158/p90 212.
- Capacity ceiling is removed, but cumulative token/work flooding remains.
- Next: deterministic minimal query-pair witness intervals.
