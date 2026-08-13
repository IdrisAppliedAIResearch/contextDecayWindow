# NF-004 Memory Update

NF-004 is complete: `WORKS`, availability only. On 1,098 sealed LoCoMo QAs at
16k, pair ranking raises complete exact-evidence delivery from 843 to 935 over
session-score inheritance: 140 gains, 48 losses, ratio 2.92, one-sided exact
p=6.19e-12. All six conversations are net positive. Source order is 258; at
32k the registered arms are 961 versus 1,024.

G0-G7 pass. The 2,749-entry vector cache is file/content/model sealed and has
zero misses; development reproduces 702/773 at 16k and 773/826 at 32k; both
development and holdout replays are byte-identical. Measurement made zero
embedding and generation calls.

Scope is the finding. LongMemEval still supports the characterized `rank
coarse, pack fine` mechanism at 32k; LoCoMo prospectively confirms the opposite
ranking direction at 16k. Binding ratio alone did not explain the corpus
difference. NF-004 measures evidence availability, not reader correctness, and
authorizes no live run, promotion, or adoption.
