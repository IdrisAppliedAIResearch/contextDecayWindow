# DA-020 Scratchpad

## 2026-08-30 - Registration

- DA-019 stopped unopened solely because its real-stream duplicate-rejection
  criterion was unreachable after upstream edge deduplication.
- DA-020 freezes DA-019's exact rule and blind selection. Required SHA:
  `b418495e649c96befa33a738a9fda0f68e56127b76f881ccc71ac4c853acd31f`.
- Required activity is 571 NF and 188 LongMem substitutions; real rejection
  counts remain fit 8,631, lexical 359, semantic 6,786.
- Only protocol change: duplicate handling is a synthetic identity test, while
  real streams must prove zero duplicate opportunities.
- Zero model/new embedding calls. No rule tuning is authorized.

## 2026-08-30 - Blind reproduction

- Corrected preflight passed and reproduced all 1,563 DA-019 rows byte-for-byte.
- Activity remains 571 NF and 188 LongMem; fit/lexical/semantic rejection counts
  remain 8,631/359/6,786. Real duplicate opportunities are zero; synthetic
  duplicate handling passes.
- Blind reproduction committed at `1bcd1e7e`. Evidence opened only afterward.

## 2026-08-30 - Outcome

- `NO_PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL`.
- NF-004 970->966: 0 gains, 4 losses, p=.125. Losses span conv-26/30/43/49.
- LongMem 188->188: 2 gains, 2 losses, p=1. Gains include temporal and
  single-session-user; losses include multi-session and single-session-user.
- NF replacements improve median cost 140->116 and cosine .430->.464, yet remove
  5 target identities and add 2. LongMem improves 276->241.5 and .167->.226,
  while removing 4 and adding 3.
- Unique query-token preservation plus cosine dominance is not an evidence
  protection invariant. No tuning, reader or adoption follows.

