# DA-090 Scratchpad

## 2026-08-31 - Registration

- Preserve all 4,556 DA-089 complete rows exactly.
- Fallback only for 2,701 full-child and 798 anchored overflows.
- Fixed 1,800-char exact packets with component/index/total/role headers.
- Prompt fallback packets child only; orphan fallback packets parent 0/1 then child.
- Replaceable <=2,048 frames, typed edge metadata, zero DA-078 mutation.
- Zero model/embedder/cache calls.

## 2026-08-31 - Result

- 8,055/8,055 complete; all 4,556 DA-089 complete rows unchanged.
- Fallbacks: 2,701 child packet streams, 798 edge-component streams.
- Overall frames p50 1/p90 3; peak chars p50 1,812/p90 1,819.
- Cumulative chars p50 2,033/p90 3,537.
- Full-frontier capacity is exact and displacement-free; reader use untested.
- Byte-identical replay; zero calls.
