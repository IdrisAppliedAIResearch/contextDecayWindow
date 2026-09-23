# AF-READ-001 — Does the V2 anchor gate beat the deployed read path at the reader?

**Status: PREREGISTERED (this file committed before any implementation).**
**Depends on:** AF-FT-001 CLOSED (`7d9bad72`), AF-FT-002/003 CLOSED (`d5230cdf`),
AF-PRE-011 CLOSED (`d12d5229`). **Zero prior calls; this study spends the first ones.**
**Operator constraint (user, 2026-10-02):** the reader model (Qwen3.8-27B, local) contends with the
coding agent for the same GPU; the user spins the agent down and drives the run from PowerShell.

## Question

The deployed product reads memory through the timeline (cosine ≥ .48, chronological union,
as-shipped, no cap). V2 (AF-FT-001) is a 6-layer cross-encoder that picks an anchor turn in ~2 GB
with a calibrated P(null). Does adding V2 as a **gated anchor producer** improve reader answer
accuracy, and at what context cost?

## Arms (one reader call per question per arm, identical frozen template)

| arm | context | source |
|---|---|---|
| **A_DEPLOYED** | frozen committed timeline prompt, byte-identical to `experiments/locomo_relevance_timeline/artifacts/native_prompts.jsonl.gz` | deployed read path, as-shipped |
| **B_ANCHOR** | V2 ungated argmax turn **±2** (≤7 turns), rendered as `<record>` block(s) in the identical instruction shell, sessions/dates from the frozen adapter | BERT context |
| **C_GATE** (primary vs A) | if P(null) < **τ = 0.2** → B_ANCHOR context; else → A_DEPLOYED context | the product proposal |

- **τ = 0.2** pre-registered from V2 seed-0 held-out coverage table (65% anchor coverage, 5% null
  leak). P(null) is computed over the frozen pool builder (BM25∪event, same K regime as calibration);
  the anchor is the ungated argmax (AF-FT-002 forensics: V2's landscape is healthy, median BM25 rank 6).
  P(null) is logged per item, so τ-sensitivity is an offline replay of the gate, never a re-run.
- Window ±2 is AF-PRE-011's ORACLE_W2 geometry (120/120 any-evidence when centred on gold).

## Items

- **Primary: H120** — the build2 held-out 120 (`anchor_ft/artifacts/build2.json.heldout`): cats 1–4,
  answerable, **never trained by V2** (V1H excluded them), never used to pick B/C hyperparameters
  beyond the single registered τ above. All 120 map 1:1 to frozen prompts (verified).
- **Descriptive: D120** — sample2 (frozen; **contaminated by model selection**: V2's recipe was chosen
  partly on it). Reported single-judge-pass, flagged descriptive, never enters any bar.

## Reader

llama-server, Qwen3.8-27B-UD-Q4_K_XL, port 8099, ctx 40960, `--parallel 1`,
`--reasoning off --reasoning-budget 0`, seed 5005, BASE params byte-identical to
`experiments/locomo_relevance_timeline/runtime.py` (temp .6, top_p .95, top_k 20,
`reasoning_format='none'`, n_predict 4096, cache_prompt false). Native prompt via `apply-template`
with the thinking-off suffix asserted. Launch command is read from the frozen
`study_E/.../restart005/launch.json` with port/ctx overrides; server binary path, file SHA, props,
and offload line are recorded in the run header.

**Calibration gates before any scored call** (inherited from the frozen runtime): arithmetic
reproducibility (two identical '45'); judge calibration on the 5 registered fixtures, all 15
verdicts exact; every prompt tokenized and asserted `tokens + 4096 ≤ 40960` before its arm runs.

**Pilot gate:** first 10 primary items × 3 arms; measured per-call seconds and token counts are
committed with the wall-clock estimate before the full schedule is entered.

## Judging

Frozen `src/analysis/hh001_prompt.py` judge; blinded surface (arm identity stripped, seeded shuffle);
primary = 3 passes (seeds 9100/9101/9102, temp .2) majority; descriptive = 1 pass (9100).
**Commit order is the evidence:** all reader answers committed before any gold file is opened by the
judge phase; judge output committed before scoring.

## Statistics and bars (fixed now; §9.3)

Primary contrast **C_GATE vs A_DEPLOYED** on H120, paired exact McNemar.

- **WORKS:** net ≥ **+8** correct and p < .05.
- **SIGNAL:** net ≥ **+4** (any p). Below that: **DEAD** — no reader value for the gate at this scale.
- Guardrail (registered, not a bar): B_ANCHOR − A_DEPLOYED net reported per category; a B loss of
  more than −8 triggers the documented alternative read (anchor-selection errors, not gating, own
  the result) and is reported as such, not folded into C's verdict.
- Budget table: median/mean/p95 context chars and tokens per arm are reported. A is as-shipped
  (uncapped); if A's median exceeds C's by more than 2×, that is a finding (same-or-better accuracy
  at a fraction of the context), not a fairness violation — both numbers ship.
- Cat-5 / adversarial items are **out of scope** (AF-FT-001: the null head is topic-bearing, not
  answer-bearing; no gold answers exist). Registering this exclusion, not hiding it.

## Call budget (the user-authorized spend)

| phase | calls |
|---|---|
| calibration (reader 2 + judge 15) | 17 |
| pilot 10 × 3 arms | 30 |
| primary readers 120 × 3 | 360 |
| primary judges 360 × 3 | 1080 |
| descriptive readers + 1-pass judges 360 + 360 | 720 |
| **total** | **≈ 2,207** |

Estimated wall clock 5–9 h at the historical 8–15 s/call, `--parallel 1`; the pilot replaces the
estimate with measurement. Failure recovery is per-call file resume; no call is ever re-issued if
its file exists and parses.

## Preflight (PF1–PF10 answers)

- **PF1** Inputs: build2.json (`7d9bad72`), frozen timeline prompts/adapters (committed), V2 ckpt
  `ckpt_V2_20261011` (reproducible), launch.json (restart005), judge/reader template SHAs — all
  hash-checked at build; run fails loudly on drift.
- **PF2** V2 pnull + argmax recomputed by `build` must reproduce AF-FT-001's recorded per-item
  numbers on the held-out slice (identity, not count); A prompts used byte-identical.
- **PF3** Gate ordering enforced by phase files: build → calibration → pilot → readers (+commit) →
  judges (+commit) → score; each phase refuses to start if the prior phase's complete-file is absent.
- **PF4** Bars reachable: n=120, discordance needed for +8 ≈ 14/6 at p<.05 — non-zero under H1;
  pilot prints nothing about direction.
- **PF5** Keys: `qid = sample_id:index` and prompt SHA; no timestamps as keys.
- **PF6** Reproduction anchor: A arm prompts replay the frozen timeline run's exact bytes (SHA
  identity against `native_prompts.jsonl.gz`).
- **PF7** No feedback loops; single pass per arm (no state between calls).
- **PF8** n=120 detects ≥ +8 with power ≈ 2/3 at p<.05; it cannot resolve per-category effects
  (reported descriptively only); it cannot separate gate errors from anchor errors without the
  logged P(null)/argmax, which are therefore mandatory columns.
- **PF9** Surrogate audit: "C beats A" can be true while gating adds nothing if only fallback items
  differ — impossible: on fallback items C uses the identical A prompt; all discordance is carried
  by anchored items by construction (logged and asserted).
- **PF10** Availability is not a verdict: this study *is* the reader measurement; adoption still
  requires the packing-cap product decision and the deployed-resolver overlap analysis.

## Artifacts & commands

`experiments/probes/anchor_reader/{AF_READ_001_PLAN.md, af_read001.py, run_read.ps1,
artifacts/{contexts.json, gate_log.json, reader/, judges/, results.json}}`.
Phases: `build` → `pilot` → `full` → `judge` → `score`; server lifecycle owned by the script
(launch, health, GPU-release asserts; terminate in `finally`). Nothing is written outside the study
directory except commits at phase boundaries.
