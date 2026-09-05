# DA-093 Scratchpad

- Reuse DA-078 immutable history and exact pointer language.
- Index reuse is an execution optimization; parse objective and tie order stay
  identical to DA-078.
- Encoded form must strictly dominate literal DA-091 packets per row.
- No evidence labels, question features, scores, model, embedder or cache calls.

## Result

- 3,499/3,499 eligible streams selected exact prompt-relative encoding.
- Savings fraction p10/p50/p90: 13.73%/22.50%/35.05%.
- Selected cumulative chars p50 1,895; frames p50 2; peak p50 1,816.
- Exact source decode; 4,556 noneligible rows and DA-078 unchanged.
- Replay identical; zero calls.
- Next: characterize pointer fragmentation and source locality before choosing a
  reader-facing dependency representation.
