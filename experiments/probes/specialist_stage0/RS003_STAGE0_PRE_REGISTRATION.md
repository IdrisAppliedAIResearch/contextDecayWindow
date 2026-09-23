# RS003 Stage-0: Specialist Admission Oracles (R-TEMP / R-MH / R-SEM)

**Status: PRE-REGISTERED (this commit precedes all implementation).**
**Date: 2026-09-23. Branch: `study/rs003-specialist-stage0`.**
**Design sources: the three recovered specialist briefs** (`research-salvage`:
`RESEARCH_RTEMP_full.md`, `RESEARCH_MH_full.md`, `RESEARCH_SEM_full.md`), as
ratified in session 2026-09-22.

## 0. Question and standing

PLAN-RS003 proposes three deterministic specialist retrievers dispatched by a
router. Before building or routing anything, each family faces a **Stage-0
admission oracle**: does the family's perfect (or near-perfect, for the
realistic arm) mechanism move *gold-evidence admission* on the committed
AF-READ-002 population enough to justify existence?

- **Zero model calls.** No reader, no judge, no LLM, no embedding inference.
  All vectors are content-cache lookups; every needed text is verified present
  (§1), so a cache miss is a hard failure, not a silent embed.
- **Availability is not a verdict (PF10).** Nothing here claims answer
  accuracy. Outcomes are dispositions about *research priority*: BUILD /
  SIGNAL / KILL per family. No adoption, no reader claim, no benchmark score.
- One-sided tests, bars fixed here, before any arm runs. A disposition tier
  not written in this file cannot be introduced later (AGENTS §9.4).

## 1. Inputs (PF1) — verified present and counted 2026-09-23

| Input | Identity | Count |
|---|---|---|
| LoCoMo raw `C:\Users\muzaf\Downloads\locomo10.json` | SHA-256 `79FA87E9…EA698FF4` | 10 convs, 1986 QAs |
| Adapter `experiments/locomo_relevance_timeline/artifacts/adapter.jsonl.gz` | blob `b83cca75…` | 3,011 elements |
| AF-READ-002 contexts `experiments/probes/anchor_reader/artifacts/af_read002/contexts.json` | blob `a7c72df3…` | 120 items (cat1 26, cat2 20, cat3 6, cat4 68) |
| AF-READ-002 results `…/af_read002/results.json` | committed | A 85 / B 59 / C 81 |
| Forensic audit population `scratch/audit002_disc_items.json` | committed | 14 items (A-hit/B-miss) |
| Embedding caches `experiments/external/locomo/artifacts/locomo_dev_embeddings.db` + `experiments/components/biological_memory/nf_004/artifacts/nf004_holdout_embeddings.db` | blobs `2483d779…` / committed | 4,985 texts; **0 of 3,011 adapter texts and 0 of 120 questions missing** (verified) |
| `episodic` package `rank_cc80` / config | committed | read-only use |
| spaCy `en_core_web_sm` | frozen model, CPU | NER only (R-MH D1) |

Judge outcomes per item come from `scratch/audit002_table.json`
(`{qid, A, B, C}` correct flags; A 85 / B 59 / C 81 reconciles with
`results.json` counts: B=59 here — the "66" in older digests is the pre-audit
value; the committed table governs).

## 2. Shared definitions (all families)

**Population.** The 120 AF-READ-002 held-out items. Per family:
primary category populations in §4–§6.

**Pool.** All adapter elements of the item's conversation (3,011 across 10
convs), in adapter file order (chronological). The committed B/C packs span
whole conversations with no probe cut, so eligibility = whole conversation;
a gold dia-id outside the pool is an instrument failure (0 found at probe).

**Element identity.** Adapter row = speaker-adjacent turn pair: `id` (content
hash), `text` (embedding key), `element` (rendered `<record …>` string),
`dialogue_ids` (list of the 1–2 LoCoMo dia-ids), `session`, `date`
(`session_N_date_time`, all 287 unique strings regex-parseable).

**Pack construction (all arms, registered rule).** Given an arm's total order
over the pool (ties broken by ascending adapter index), build the block by
skipping on overflow: walk the order, append `element` joined by `"\n"`,
charge exact serialized length (elements + joiners), skip (never truncate)
what does not fit. Caps: **8,000** and **16,000** chars (same as committed
`cap_b` / `cap_c_total`).

**Coverage (primary metric).** For item *i* with gold dia-id set *G*, pack dia
set *P* = union of `dialogue_ids` of packed elements:
`coverage = |G ∩ P| / |G|`. Derivatives: **full-admission** (coverage = 1),
**zero-admission** (coverage = 0), **zero-admission-among-B-misses** (items
with `B = 0` in the audit table). **Cost** = packed block chars; token proxy
= chars / 4.

**Statistics.** Exact one-sided binomial sign test on discordant full-admission
pairs (arm vs control), `scipy`-free (`math.comb`). Report n, wins, losses, p.
No post-hoc tier changes.

**Determinism.** Frozen cache vectors (float32 bytes), frozen regex, frozen
spaCy model, `OMP_NUM_THREADS=1`, `PYTHONHASHSEED=0`, all sorts with explicit
tie-breaks (score desc, adapter index asc), zero RNG anywhere, `numpy` only.

## 3. Controls (shared)

- `B_as_is` — committed `block_b` dia-ids parsed from `dialogue_ids="…"` spans
  (verbatim replay; ≤8k).
- `C_as_is` — committed `block_c` dia-ids (≤16k).
- `CC80_8k`, `CC80_16k` — frozen `rank_cc80` (0.8 dense + 0.2 BM25, min-max,
  deployed tie-breaks) + this harness's packer at 8k/16k.
  *Instrument check:* mean n-packed elements must sit within ±2 of the
  committed mean `n_cc80` (= 24.5); packer/renderer differ from
  `retrieve_long_term`'s episode tags, so this is tolerance-matched, not
  byte-exact — registered here because it cannot be byte-exact.
- `ORACLE_full` — every pool element (no budget). **Must** give coverage 1.0
  on all 120 items or the harness is broken and no dispositions issue (§9.2).

## 4. R-TEMP (temporal; primary population cat2, n=20)

**Diagnosis under test (from forensics):** cat2 gold answers are anchored to
session timestamps; retrieval never sees dates; `when`-questions carry no
time expression (verified 1/20). The failure is either *admission* (evidence
turn not packed) or *resolution* (turn packed, reader fails `yesterday`).
R-TEMP (a retrieval specialist) exists only if admission is the binding
constraint.

**Date machinery (frozen regex parser, no LM):**
- Session anchor: `H:MM am/pm on D Month, YYYY` → ISO datetime (verified
  287/287 parseable).
- Gold parser (ordered): full dates in orders `D Month, YYYY` / `Month D,
  YYYY` / `D Month YYYY` (also `9October` glued form); `Month YYYY` → month
  window; `The <weekday> before <date>` / `first weekend of <Month YYYY>` →
  month window containing the resolved anchor; `YYYY` → year window; else
  **unparseable** (expected ≈ 8/20, incl. non-dates like "Max"/"UK" — LoCoMo
  label noise, counted, not repaired).

**Arms.**
- `T1_gold_window(Δ)` — perfect oracle: window `[gold_date − Δ, gold_date + Δ]`
  over session timestamps; candidate order = chronological (and
  reverse-chronological fill as secondary); pack at 8k and 16k.
  Primary: Δ = 7 days, chronological, 16k. Report Δ ∈ {1, 3, 7, 14}.
  Unparseable gold → arm admits by empty window (contributes no admission;
  the rule stays well-defined on all 20).
- `T2_relative_solver` — realistic arm: frozen relative-expression regex
  (yesterday / today / the day before yesterday / last <weekday> / last
  {week,month,year} / the week before / the previous {week,month,year} /
  `<n words> {days,weeks,months,years} {ago,before,after,later,earlier}` /
  this {past,last} {week,month}) matched in **gold-evidence turn texts**
  (oracle selection of turns; resolution itself is mechanical), resolved
  against the evidence turn's session ISO anchor → window (Δ=7) → pack.
  Reports (a) resolution agreement with parsed gold date (both parseable),
  (b) full-admission vs controls. (8/20 items carry a relative expression in
  evidence text — verified at probe.)
- Controls §3.

**Bucket decomposition (reported, not gating):** per item
`{absolute-in-gold, relative-in-evidence, duration-difference, unparseable}`
with per-bucket coverage for T1 and controls.

**Disposition (one-sided, cat2 n=20, at 16k vs `CC80_16k`):**
- **BUILD** iff `T1_gold_window` full-admission ≥ **+10pp** (≥2 items) over
  `CC80_16k` **and** T1 zero-admission is ≤ `CC80_16k` zero-admission, **and**
  `T2_relative_solver` recovers **≥50%** of T1's margin.
- **KILL** iff T1 margin <+10pp: perfect date-window retrieval cannot move
  cat2 admission; residual cat2 failure is read-side resolution or gold
  noise; R-TEMP does not enter PLAN-RS003.
- Between: BUILD only if T1 margin ≥ +20pp on the parseable subset with
  T2 ≥ 50% — reported as **SIGNAL** (successor = better resolver), never
  BUILD. (With n=20, +10pp = 2 items; this is stated as weak-power.)

## 5. R-MH (multi-hop set coverage; primary population cat1, n=26)

Registered population: cat1 = 26 ≥ 25, so the recovered brief's fallback
(set-coverage set, |gold| ≥ 2, n=39 verified) is reported as secondary, not
primary.

**Graph (index-time per conversation, no new embeddings):**
- Nodes: pool elements; vectors from cache (unit-normalized float32).
- Edges: (a) kNN cosine k=4, floor τ=0.30 (within conversation); (b) temporal
  adjacency ±1, ±2 by adapter index; (c) spaCy NER entity co-occurrence
  (PERSON/ORG/GPE/LOC/ORG-family; entity = lowercased text; entities with
  document frequency > 20% of conversation elements excluded; entity
  occurrence = lowercased entity text present in element text).

**Arms (query-time, zero LM):**
- `D1_ray` — spaCy NER on question; seeds = entity-matching elements (top-10
  by CC80 rank) ∪ top-5 CC80; fixed-iteration Personalized PageRank
  (α=0.85, 30 iters, dense 1024-node max matrix per conversation) seeded at
  seeds; order = PPR score desc; **protected prefix** = top-4 CC80 elements
  packed first, then PPR order, skip-on-overflow.
- `D2_FL_protected` — pool = top-200 by CC80; protected prefix = top-4 CC80;
  then greedy marginal gain of `f(S) = Σ_j max_{i∈S} max(0, cos(i,j))` over
  the pool, skip-on-overflow to cap. Ties: ascending adapter index.
- `D4_A3_cluster` — pool top-200 CC80; deterministic clustering
  (farthest-first from highest-CC80, k=16; Lloyd 10 iterations); admission
  score = min-max CC80 norm + 0.1 × [element's cluster unvisited]; skip-on-overflow.
  Included as the expected-null control (E005 arm ported; TC-007 predicts parity).
- `ORACLE_pack16k` — gold-carrying elements first (chronological), then CC80
  order, at 16k: family ceiling.
- Controls §3.

`D3_doc2query` and `D5_session_quota` are **deferred** (per recovered brief:
D3 needs an index LM pass; D5 is closed-adjacent via TC-008) — registered
here as out of scope for Stage-0.

**Mechanical admissibility (instrument, §9.2):** among the 61 B-misses, ≥10
must have gold content cost ≤ 16k (sum of gold-carrying element lengths +
joiners) or the 16k branch is an instrument failure and no D-arm disposition
issues.

**Disposition (one-sided, cat1, 16k):** a D-arm **advances (BUILD)** only if
ALL of: (a) full-admission ≥ **+10pp** over `CC80_16k` **and** ≥ +10pp over
`B_as_is`; (b) exact sign test vs `CC80_16k` p < **0.05**; (c) full-admission
regressions among the 94 non-cat1 items ≤ **1**; (d)
zero-admission-among-B-misses down **≥50% relative** to `CC80_16k`.
**SIGNAL tier (registered now):** full-admission ≥ +5pp and p < 0.10 →
successor study; anything below → KILL for this corpus. If only D1 clears,
that is the registered expected result (associative reach, not selection
objective).

## 6. R-SEM (semantic lane; primary population cat3+cat4 pooled, n=74)

Rationale (recovered brief): cat3 n=6 is uninterpretable alone; pool
cat3+cat4 = the semantic lane; report cat3 separately, stated, not hidden.
Budget: **8k** (B's budget) primary.

**Arms.**
- `ORACLE_rerank` — gold-carrying elements first (chronological), then CC80
  fill, at 8k: family ceiling. Instrument: ≥90% of items must have gold cost
  ≤ 8k, else report and cap conclusions at mechanical ceiling.
- `R2_RRF` — Reciprocal Rank Fusion of dense-only and BM25-only orders
  (k₀=60; ties by adapter index), pack at 8k. (Threshold re-calibration is
  *not applicable*: budget packs have no K filter; registered so it cannot be
  claimed later.)
- `R1_head` — logistic head, features per (question, element): [dense cos,
  BM25 min-max norm, RRF rank norm, question-token overlap fraction
  (frozen `_ranking.tokenize`), recency `1/(1+elements_from_end)`, log
  char length, session-fraction index]; labels = element carries gold
  dia-id (training labels only; inference is feature-only — leakage
  direction: features never see gold). Hard negatives: non-gold elements
  with any digit-bearing/date-like token ∪ top-10 dense non-gold, ≤15 per
  item, deterministic index sampling. Training: full-batch GD, lr 0.5,
  2000 iters, L2 1e-3, zero init, z-scored features (train-fold stats).
  Evaluation: 5-fold **conversation-level** CV — frozen test folds
  [(26,30), (41,42), (43,44), (47,48), (49,50)]; each test conversation
  scored by the model trained on the other 8.
- Controls §3.

**Disposition (one-sided, n=74, 8k, vs `CC80_8k`):**
- Family **BUILD** iff `ORACLE_rerank` clears full-admission ≥ +10pp over
  `CC80_8k` and some mechanism arm clears the R-MH-style bar (a)+(b) at 8k.
- **SIGNAL** iff an arm reaches ≥ **+3pp** full-admission with p < 0.10
  (ledger floor: <3pp is not a result on this instrument).
- **DEAD** otherwise — the honest null the recovered brief pre-sanctions:
  keep R-SEM frozen, spend PLAN-RS003 on surviving families.
- No-regression analog (the internal "12 targeted items" do not exist in this
  corpus): full-admission regressions among cat1+cat2 (46 items) ≤ 2.
- X1–X4 miss typology from `RESULTS_009.md` is not recomputable here (it
  needs per-item audit artifacts of the miss_audit probe); registered as a
  reported limitation, not silently substituted.

## 7. Determinism / identity anchors (PF6)

- `ORACLE_full` coverage = 1.0 on 120/120 items (else harness broken).
- B_as_is / C_as_is ids parsed from committed blocks; recomputed
  zero-gold-in-B-pack rate on the 14-item audit population is recorded; the
  committed forensics recorded "72% of B's 24 misses zero-gold" over a
  24-item subset whose membership file does not exist in the repo — the
  recomputation is reported next to the recorded figure, and any gap is a
  reported population-definition note, not a silent reconciliation.
- Every arm re-run twice; selected id-sequences must match exactly
  (second-run check), per §"byte-identical seeded prefix rerun".

## 8. Preflight

- **PF1** Inputs verified §1 (counts, hashes, cache coverage 3011/3011,
  120/120).
- **PF2** Mechanism identity: packer = skip-on-overflow exact-charge
  (matches `pack_stm_payload` policy; verified against `grow_window` ≤ cap on
  all 120 committed blocks); CC80 = imported `rank_cc80` itself, not a
  reimplementation; NER = `en_core_web_sm` frozen.
- **PF3** Gates: ORACLE_full and mechanical-admissibility checks execute in
  code before any arm's metrics are written to the results file (assertions
  placed before the metric loop; reviewed).
- **PF4** Bars reachable: §4–§6 each state the minimum-item move (+2 items at
  +10pp on n=20; 3 items at +10pp on n=26; +3pp ≈ 3 items on n=74); oracle
  ceilings themselves demonstrate the non-stopping branch can exist.
- **PF5** Comparison keys: adapter content-hash `id` + dia-ids; no
  generated ids, timestamps, paths.
- **PF6** Reproduction anchors §7.
- **PF7** No feedback mechanisms (single-pass scoring).
- **PF8** No ablation arm needed; arms are contrasts by construction.
- **PF9** Surrogate audit: coverage-of-gold-dia-ids can pass while the item
  is unanswerable (gold noise ≈ 11% floor; judge floor applies equally to all
  arms; PF10 restates availability ≠ verdict). Full-admission over cat1 with
  mean |gold| = 2.85 — reported per-item, not averaged away.
- **PF10** Stated in §0. No reader claim in any disposition.

## 9. Outputs

`experiments/probes/specialist_stage0/artifacts/`:
`rs003_temp_results.json`, `rs003_mh_results.json`, `rs003_sem_results.json`
(per item × arm: coverage, ids count, cost), plus
`RS003_STAGE0_RESULTS.md` with per-family dispositions, every bar's number,
and per-item discordance lists. Commit order: pre-registration (this file,
no code) → implementation → run artifacts + report.

## 10. Explicitly not done here

No router, no reader, no judge, no new embeddings, no Doc2Query index pass,
no adoption, no parameter search beyond registered values. Numbers land once;
implementation bugs found in review are fixed before first results generation;
after results exist, changes to arms, bars, or populations are amendments.
