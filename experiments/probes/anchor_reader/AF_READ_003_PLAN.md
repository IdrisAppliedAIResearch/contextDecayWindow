# AF-READ-003 — Scale: chronological anchor window + CC80 pack on the full LoCoMo dev

Status: LOCKED at this commit. Implementation follows in a separate commit.
Lineage: AF-READ-002 (`0ad08cd` + `602265e5`) established WORKS at n=120
(net −4, p=.42, 42.3% tokens) on the point margin only; this study buys the
precision n=120 lacked. No mechanism, budget, producer, prompt, server or
judge change is permitted here — everything is frozen from 002.

## Population

All LoCoMo dev (locomo10.json) main questions, category 1–4: n=1,540.
Exclude the 120 AF-READ-001 primary qids (already run; their 002 verdicts are
reused byte-identically for the pooled secondary). New population: n=1,420.
Each item tagged `af1_descriptive` if its qid was an AF-READ-001 descriptive
item, else `never_run` (secondary split only; both are main cat 1–4 gold).

## Arms (frozen)

- **A_DEPLOYED** — frozen native prompt from `native_prompts.jsonl.gz`
  (row['prompt'], native thinking-off template); shell identity asserted for
  every item as in AF-READ-001.
- **B_ANCHOR8K** — contiguous chronological window ≤8,000 chars of deployed
  adapter elements around the seed (AMENDMENT_001 units), alternating-end
  growth, `af_read002.grow_window` (imported, unmodified).
- **C_ANCHOR8K_CC80** — B block ∪ legacy-CC80 pack ≤8,000 chars
  (`retrieve_long_term`, `EpisodicConfig(read_policy='legacy_cc80',
  recency_window_n=0)`, imported `af_read002.cc80_select`), merged
  chronologically, ≤16,000 total, lowest-rank CC80 elements dropped first
  (drops recorded), replayed twice for determinism.
- Seed producer (frozen from 002): V2_20261011 gate, pnull<τ=.2 → V2 argmax
  anchor turn; else BM25 top-1 turn (`af_read002.seed_bm25`).
- Vectors: cached Qwen3-Embedding only; **zero embedding calls**, assert
  0 misses.

## Protocol (frozen from 001/002)

Server per `restart005/launch.json` pinned command, port 8099, ctx 40960,
parallel 1, reasoning off. BASE seed 5005 temp .6 top_p .95 top_k 20
n_predict 4096. Calibration gate (45-twice + 15 judge fixtures) before any
study call. Readers committed before gold opens. Blind 3-pass judge
(render_judge_prompt native, seeds 9100/9101/9102, temp .2), all three arms
(new items have no stored verdicts; no PF-J reuse — the judge-fixture
calibration is the determinism anchor). Resumable; every response file
persisted on completion.

## Statistics and bars (registered before any new call)

Primary: new-population McNemar, **C−A**, n=1,420.
Proportional to the 002 bars, fixed now:

- **IMPROVES**: net > 0 and p < .05.
- **WORKS**: net ≥ −48 (≡ −3.33%) and p > .05 (not significantly worse) and
  mean C input tokens ≤ .60 × mean A input tokens.
- **DEAD**: net < −94 (≡ −6.67%) and B−A net < −94.
- else SIGNAL.

Additional registered label (upgrade, not a replacement): **CI-NONINFERIOR** —
one-sided exact 95% CI lower bound of (p_C − p_A) > −3.33%. 002 explicitly
conceded it lacked CI-level evidence; this study reports whether it has it.

Secondaries (non-dispositioning): B−A McNemar; pooled-1,540 re-run of C−A
reusing 002 verdicts; gate-open vs fallback partition (H120 showed exact
59/59 gate-open parity and all loss in fallback — this tests it at n≈1,420);
`af1_descriptive` vs `never_run` split; abstention counts; mean tokens/arm;
cap-saturation and drop counts.

Power sketch (from 002 discordance rate 11.7%): ~165 expected discordants,
SE(net) ≈ 13 items. If truth is net −3.33% (−47 items), WORKS fires ~always,
CI-NONINFERIOR needs net > −27 (fails at truth exactly on the old margin —
expected and honest). If truth is parity, two-sided net CI ≈ ±26: superiority
of C beyond the 3.3% margin (47 items) is rejectable either way.

## Preflight

- **PF1** inputs hash-locked at build: adapter/selections/prompts/
  native_prompts jsonl.gz, both embedding DBs, af_read001+002 contexts.json.
- **PF2** mechanism identity: B/C builders are the imported 002 functions;
  on 5 H120 replay items the 003 builder must reproduce 002's stored
  `b_sha`/`c_sha` byte-identically. A-shell identity asserted on all 1,420.
- **PF3** ordering: calibration → pilot → full readers (commit hashes, gold
  unopened) → judge → score; gates execute before gated phases (same code
  shape as 002).
- **PF4** bars reachable: 002 observed 11.7% discordance and 0 cap failures
  at n=120; cap loops bounded; all four dispositions possible at n=1,420.
- **PF5** comparison keys: qid strings + content SHAs only.
- **PF6** reproduction anchor: the 5-item H120 block-SHA replay above; plus
  calibration replay of the frozen 45/'45' + judge-fixture gate.
- **PF9** surrogate audit: judge correctness can pass while answer is wrong
  (fluency) — three blind passes + fixture calibration; no human audit
  (declared residual). Contexts carry no gold (gold-free by construction;
  contexts.json keys asserted gold-free at build).
- **PF10** this is the live reader evaluation; availability is not claimed
  anywhere — every arm gets real reader calls.

## Cost / runtime

4,260 reader calls + 12,780 judge calls ≈ 17,040; measured 002 rates imply
~6–10 h unattended. Zero embedding calls; V2 gate scoring is local MiniLM.

## Dispositions own this study

Reported per the registered bars above, on the new population, with the
pooled number secondary and clearly labeled. No reinterpretation after the
table is seen.
