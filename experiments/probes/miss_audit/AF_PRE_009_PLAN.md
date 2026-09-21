# AF-PRE-009 (registered before code runs, 2026-09-20): what limits the 56/120 — audit of the 64 misses

**Question:** on the AF-PRE-005 best run (`ungated_newFT`, ckpt2, 56/120 on sample2,
`a237be71`), what is the *limiting factor* of the remaining 64 errors? Not a new mechanism:
a mechanical attribution of the errors, so that the next probe targets the real ceiling.

**Why a registered audit and not a read-through:** a miss taxonomy invented after reading
cases can explain anything (§3 — a surrogate that passes while the property it certifies is
false: "we know why we lose" can be true or unfalsifiable). Every category below is computed
from committed data by a rule fixed now, and the categories are assigned in a strict priority
order so the counts are mutually exclusive.

## Reproduction gate (PF6) — instrument check before attribution

Recompute ckpt2 ungated top-1 over **all turns** of each sample2 conversation, the frozen
AF-PRE-005 contract (max_len 256, seed 20260920, `unified_anchor/artifacts/ckpt2`).
**The hit count must be exactly 56/120** and the item set must match the registered n=120.
A miss on this gate is an instrument failure and the audit stops; no attribution is reported.

## Data available per item (all committed, no new annotation)

`locomo10.json`: `qa[i].question`, `.answer` (gold answer string), `.evidence` (list of dia_ids,
1..n), `.category`; turns carry `speaker`, `dia_id`, `text`; `session_N_date_time` per session.
Gold = earliest evidence turn (`ft_pipeline.eligible_all`). Scoring is **strict single-gold**.

Note recorded pre-run: AF-PRE-001's registered gold rule counted *any* annotated-introducing
evidence turn, while `ft_pipeline.eligible_all` collapses to the earliest one. Category **E1**
below measures what that collapse costs; it is not a re-scoring of 005 (its verdict and its
numbers stay as recorded) — it is a measurement of how much of the error mass is label
identity rather than model capability.

## Categories (priority order; first match wins; all mechanical)

- **E1 WRONG-EVIDENCE.** Predicted turn is a *different* annotated evidence turn of the same
  item. The model returned answer-bearing evidence; the gold rule wanted the earliest.
- **E2 DUPLICATE-TEXT.** Not E1, and the predicted turn's normalized text equals the gold's,
  or token-Jaccard ≥ 0.90. The earliest-copy rule is unimplementable from text alone.
- **E3 ANSWER-ELSEWHERE.** Not E1/E2; gold contains **none** of the answer's content tokens,
  and the predicted turn **does**. Answer-seeking succeeded, earliest-anchoring failed.
- **E4 TRUE-RANKING-FAIL.** Gold contains the answer's content tokens and was still beaten.
  Sub-split by ckpt2 rank of gold: **E4-near** (rank 2–3) vs **E4-far** (≥ 4).
- **E5 RESIDUAL.** Everything else (neither turn contains the answer value). Counted and listed
  for a bounded read of ≤ 12 items, *illustration only*: reading cannot reclassify, and any
  post-reading account is labeled posthoc.

**Answer-presence test (frozen):** normalize to lowercase, strip punctuation; an answer is
"present" in a turn if the answer string is a substring, or all of the answer's content tokens
(len > 2, not in a 40-word stop list) occur in the turn. Content-token sets, no embeddings, no
reader calls.

## Reported alongside (descriptive, no bar)

- 2×2 table over all 120 items: answer-value present at gold × item correct.
  A strong association is the quantitative statement of the limiting factor, not a story.
- ckpt2 rank of gold on the 64 misses (median; how many rank 2; how many beyond 20).
- How many of the 64 BM25 gets right (complementarity of the two scorers).
- How many of the 64 have gold outside the AF-PRE-005 pool rule (what the *gated* deployed
  architecture could never fix).
- Fixable ceilings, stated as upper bounds with interactions ignored:
  56 + |E1| (label identity), + |E2| (duplicate text), + |E4-near| (margin-level ranking).

## Preflight (`PREFLIGHT.md` §4)

- **PF1 inputs:** `C:\Users\muzaf\Downloads\locomo10.json` (10 conversations, 1,527 eligible
  cat-1–4 items — counted in `unified_anchor/results.json` context); `unified_anchor/artifacts/
  {sample2.json, ckpt2/}` (`a237be71`); `bert_anchor/part1_artifacts/part1e_locomo_pool.json`.
  All read-only here.
- **PF2 mechanism identity:** the arm being audited is *ungated ckpt2 over all turns* — the
  exact code path of `ft_pipeline.evaluate/run_surface('ungated_newFT')`, reused by import, not
  reimplemented; its registered output is 56/120 and the reproduction gate tests that identity.
- **PF3 gate ordering:** reproduction count is asserted before any category is computed; the
  script raises and writes nothing on mismatch.
- **PF4 reachability:** every category can be empty and every category can be non-empty on the
  frozen input — E1 is reachable iff some sample2 item has ≥2 evidence turns (counted at
  preflight, reported), E3/E4 partition on answer-presence which holds for some items and not
  others (counted at preflight).
- **PF5 comparison keys:** per-item keys are `sample_id:qa_index` (stable in the source file,
  as used by every AF-PRE probe) — no generated ids, no paths.
- **PF6 reproduction anchor:** 56/120, exact, above.
- **PF7 absorbing states:** n/a (no feedback loop; single pass over frozen items).
- **PF8 adequacy:** n=64 errors, of which E1/E2/E3 are exact counts; the audit cannot detect a
  factor that is only visible to a reader (e.g. pragmatic mismatch), and says so.
- **PF9 surrogate audit:** "answer present" can be true while the turn is not the anchor
  (an answer mentioned twice), and false while the turn is the only solvable anchor (inferential
  items). Residual: answer-presence is a lexical proxy; E3/E5 sizes are therefore floors/ceilings,
  not proof. Stated in Limits.
- **PF10 live evaluation:** this is a measurement of committed predictions; availability is not
  a verdict and no capability claim is made from it. Only the reader pilot can produce that.

## Limits of this audit (pre-stated)

Answer-presence is a lexical proxy: for cat-1 multi-hop and cat-3 inferential items the answer
value is often legitimately absent at *every* evidence turn, which lands in E3/E5 without
proving the item is solvable by any ranker. This audit can therefore say which factor carries
the error mass and what each is worth; it cannot prove a fix works. No LLM readers; no new
training; BERT-class serial GPU; seeds 20260920. Category 5 stays excluded as registered.

## Reading order (fixed)

Run, reproduce, compute, commit counts; only then read cases. Git order is the evidence.

## Preflight measurement recorded before the audit runs (`0e98b31d`)

On the frozen sample2: **30/120** items carry ≥2 annotated evidence turns (E1 reachable);
**0/120** have any other turn whose normalized text equals the gold's (so **E2 is unreachable
and is expected to come back empty** — an empty E2 is not a finding); the answer value is
present at gold on **52** items and absent on **68** (E3 and E4 both reachable). Answer-presence
over all 120 is therefore computable in both states, and the 2×2 has four possibly-nonempty
cells except the duplicate-text axis.
