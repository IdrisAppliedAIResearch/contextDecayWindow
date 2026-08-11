# BA-001 Retrieval Benchmark Causal Audit Report

**Date:** August 11, 2026
**Outcome:** `CHAIN_PACKING_ONLY_GAIN - CHARACTERIZED`
**Design commit:** `94ed623a67fe5a893521323796b74d68aa4feebd`
**Authorization commit:** `af5f3209b75f68c18b548172e913101c3542ea28`
**Amendment 001 commit:** `dcb33a5639fa3a81248b3a53ea0b1dc7944e388d`
**Implementation commit:** `35cd4e2ae971e724ef23e5baa35fa58f32b53d67`
**Preflight commit:** `5f7943e7c4db7e167362431f21d4a02ea1c1d47c`
**Result commit:** `ee40d21d75221abf5afc9cead1bb0f86c90aa3a8`
**Result digest:** `6e2ae2cba14509805ac35abd916db5d577595bff3cb3b3dd9359f791a378c20e`
**Calls:** zero model calls; zero embedding calls; zero live runs

## 1. Answer

E006 chained retrieval did not discover more required evidence than fixed-query
retrieval when candidate volume was held equal. At the registered 15-candidate
cell, both candidate sets contain the exact same 9/17 required facts. The fixed
query packs 7/17; the chain packs 9/17 because its final ranking lets two civil
facts survive the 32,000-character budget.

The observed E006 improvement is therefore an ordering-and-packing effect, not
a demonstrated associative-discovery effect. The original comparison against
X0 also gave the chain 15-20 candidates and 12 selected episodes versus X0's
8 selected episodes, so it mixed mechanism, opportunity, and delivery volume.

No live run existed. The 6/17 to 9/17 result was offline availability, not a
model score. It remained below the 14/17 breadth threshold, so it would not by
itself have changed Q11's binary outcome.

## 2. What Was Mechanically Missing

Against `HYPOTHETICAL_001_MECHANICAL_BIOLOGICAL_MEMORY_MODEL.md`, the source
audit finds eight mechanisms absent and one partial resemblance:

| Reference mechanism | E006 status | Mechanical finding |
|---|---|---|
| Tag decay and symmetric capture | Absent | No tag, salience event, temporal window, or retroactive state update |
| Sequential/recombinant replay | Partial | Retrieval uses ordered hit feedback, but no stored sequence is replayed and no connectivity changes |
| Storage/retrieval separation | Absent | No persisted episode edges and no independent accessibility gate |
| Competitive retrieval plasticity | Absent | `seen` prevents duplicate hits, but no winner is strengthened and no competitor is suppressed |
| Transformation and fast/slow stores | Absent | No gist store, detail decay, or transfer between substrates |
| Supersession lineage | Absent | No contradiction or retrievability update path |

E006 is mechanically pseudo-relevance feedback: retrieve by cosine, average the
hits into a new cue, exclude seen episodes, and retrieve again. It is not the
reference model's graph traversal. Calling both procedures "associative" hid
that distinction.

## 3. Why Art Failed

Art was not absent from memory and was not universally unreadable.

- All four registered art facts exist in eligible source episodes.
- The best E006 chain admits generic art turns 43, 45, and 54 but no registered
  art fact. The original fact-bearing sources are deep in the Q11 cosine list;
  turn 55, which contains all four facts together, is rank 87 at cosine 0.1091.
- The chain already reaches turn 54. A radius-1 temporal adjacency expansion
  therefore reaches turn 55 and all four missing art facts. This is an oracle
  reachability result only: it does not show that a budgeted adjacency selector
  would deliver them or improve an answer.
- On the frozen `c121_l` corpus, changing granularity from whole episodes to
  spans raises enumeration recall from 0.0625 to 0.6250. Across all 24 queries,
  span retrieval records 10 gains, 0 losses, and 14 ties. Art-domain macro
  recall rises from 0.375 to 0.750.
- In corrected Study 007 and Study 009 L scores, Q4-Q6 are each 1.0 when art is
  directly cued and available. In LV-001 neither arm receives art evidence and
  both fabricate art answers.

The supported diagnosis is `STORED_BUT_NOT_BROADLY_CUED`: broad whole-episode
similarity misses the specific art bundle, while direct cueing can recall it.
The repository does not identify pretrained-prior conflict as the cause of the
fabrications. That requires a matched reader experiment varying only supplied
evidence wording; cross-study answers cannot supply that causal contrast.

## 4. Benchmark Postmortem

Three benchmark properties made the failure look stranger than it was:

1. **The broad probe asks for enumeration, but retrieval represents whole
   exchanges.** Long assistant text dilutes a short planted fact. Span retrieval
   performs much better on the sealed enumeration queries.
2. **The score is thresholded.** A payload can add correctly attributable facts
   and remain a zero on Q11. Availability and binary score are different
   instruments.
3. **The original chain comparison was volume-confounded.** Always-nonempty
   `top_m` plus `seen` guarantees more candidates with depth. More movement is
   not evidence of a better associative cue.

The art bundle also uses a synthetic title and attribution that can compete
with a model's background knowledge. LV-001 is consistent with that concern,
but does not identify it: evidence absence, model state, and run differ at the
same time.

## 5. Disposition

| Diagnostic | Result | Ceiling |
|---|---|---|
| D0 biological implementation gap | 8 absent, 1 partial | Source characterization |
| D1 matched-volume chain | `CHAIN_PACKING_ONLY_GAIN` | Offline availability |
| D2 temporal adjacency | `ADJACENCY_OPPORTUNITY_PRESENT` | Oracle reachability only |
| D3 representation | `ENUMERATION_GRANULARITY_GAP` | Frozen-corpus association |
| D4 art recall | Stored, directly recallable, not broadly cued | Cross-run confounded reader evidence |
| Prior-knowledge conflict | `PRIOR_CONFLICT_NOT_IDENTIFIED` | Requires a new matched reader study |

No retrieval component is promoted or adopted. A prospective follow-up may test
one temporal-adjacency bridge under matched candidate and exact character
budgets, with targeted no-regression gates before any live run. Span granularity
must remain a separate component rather than being bundled into that study.

## 6. Integrity

PF1-PF10 pass. The audit verifies 20 frozen inputs, seals canonical content
identities before label access, reproduces Rev5's best 9/17 payload and P3's
15-candidate A0/A1/A2 counts, and reproduces the amended `c121_l` Tier 2
aggregates exactly. Eight focused tests pass, including two content-identical
executions. Results are in `artifacts/ba001/`; `manifest.json` binds every
generated output.

The outcome remains `CHARACTERIZED`. It establishes no live answer improvement,
no causal benefit from temporal adjacency, and no validation of the biological
architecture.
