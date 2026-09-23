# AF-PRE-004 (registered before run, 2026-09-20): event-gated retrieval — the gating combinator

**Proposal under test:** the three prior probes killed score-mixing (AF-PRE-002 S3: 29→17)
and gradient-sharing (AF-PRE-003 INTERFERENCE: 29→8), both because one scalar score must
both trust and distrust lexical answer overlap. Neither killed **gating**: the event regex
selects *candidates* (no query-answer logic), and any reranker then chooses *within* the
pool. The trust/distrust decision moves from the score to the pool construction, where
both cues can coexist. This is the successor explicitly deferred in AF-PRE-002 RESULTS.

## Pipeline (deterministic, frozen before scoring)
For each question q in a conversation:
1. **Answer branch:** A = BM25 top-20 turns.
2. **Event branch:** entities(q) = quoted spans + capitalized multiword spans (stoplist:
   leading interrogatives). E = turns with event family_count ≥ 1 (AF-PRE-002 frozen
   lexicon, unchanged) containing at least one entity substring (case-insensitive),
   capped at 30 by turn order.
3. **Pool** P = A ∪ E. Reranker picks top-1 in P; ties → earliest turn.

Rerank arms (same pool, serial loads):
- **P1** zero-shot pinned MiniLM CE (AF-PRE-001 weights).
- **P2** the AF-PRE-003 fine-tuned checkpoint (its answer collapse was measured on the full
  pool; inside a gated pool it may be a different model — registered as a test, not a rescue).
- **P3** BM25 argmax in P (pool-internal reference; isolates what the gate alone does).

## Reference numbers (all previously run, same 17 + 120 items)
| arm | E-17 | sample-120 |
|---|---|---|
| BM25 | 0 | 29 |
| zero-shot CE | 0 | 25 |
| fine-tuned CE (full pool) | 17 | 8 |
| regex event rule (no model) | 17 | 1 |

## Bars (binding)
- **PASS-GATE:** P1 ≥ 16/17 on E **and** net P1−BM25 ≥ +10 on sample-120 with McNemar p < .05.
- **CARRIES:** P1 ≥ 16/17 E **and** net P1−BM25 > 0.
- **DEAD:** otherwise — gating does not solve what mixing and sharing failed; report which
  half died.
- P2 results are descriptive (no bar; it had no registered right to one).

## Failure of nerve, pre-stated
- If P1 keeps E at 17 but loses to BM25 on answers, the reranker is the dying half — echo
  and meta failure inside the pool — and the honest product statement becomes: gate for
  events, leave answers to BM25 (still two mechanisms, now with measured justification).
- If P2 beats P1 on answers, that is post-hoc arm comparison; it may justify a new probe,
  not a reinterpretation of this one.

No LLM readers. GPU loads serial: CE then FT-CE, freed between. Seeds 20260920.
