# RESULTS_AF_READ_002 — Chronological anchor window + CC80 pack under fixed budgets

Plan: `AF_READ_002_PLAN.md` (`0ad08cd`) + `AMENDMENT_001_af_read_002_elements.md` (`602265e5`).
Run: 2026-09-22, unattended via `run_all002.ps1`. H120 only. Model/runtime frozen
(BASE seed 5005, temp .6, native thinking off, port 8099); calibration PASS;
PF-J judge-reuse replay PASS (5/5 verdicts identical to AF-READ-001 stored A-arm
verdicts); readers 240/240 SHA-sealed; judges 3 blind passes. A_DEPLOYED reused
byte-identically from AF-READ-001 (zero new A calls).

## Disposition: **WORKS** (first non-DEAD read-path arm in the arc)

Pre-registered bars: IMPROVES = C−A net > 0 & p<.05; **WORKS = C−A net ≥ −4 &
p>.05 & C tokens ≤ .60×A**; SIGNAL; DEAD.

| arm | correct /120 | vs A (McNemar) | mean tok in |
|---|---|---|---|
| A_DEPLOYED (full adapter selection) | **85** | — | 11,110 |
| C_ANCHOR8K_CC80 (8k window + 8k CC80, merged ≤16k) | **81** | net −4 (5W/9L), p=.42 | 4,695 (**42.3%**) |
| B_ANCHOR8K (8k window only) | 59 | net −26 (4W/30L), p=1e−5 | 2,471 |

C lands exactly on the −4 non-inferiority margin with p=.42. Honest margin of
error: paired Wald on 14 discordants gives net **−4 ± 7.3 (≈[−11, +3])** — the
CI does not exclude −11, so this is "meets the registered point margin", not
"demonstrated non-inferiority at CI level".

## Decomposition (post-run, diagnostics)

- **Gate-open (80 V2 seeds): C = A = 59/80. Exact parity.** When the V2 anchor
  fires, window+pack loses nothing to full memory.
- **Fallback (40 BM25 seeds): C 22 vs A 26.** All of the net −4 sits where the
  V2 gate closed and BM25 top-1 picked the seed window — the same subset where
  the anchor mechanism is weakest by construction.
- **CC80 pack carries breadth: B 59 → C 81 (+22).** The chronological
  neighborhood alone (B) is significantly worse (−26); almost every C win over
  B is a multi-item or cross-session answer whose second fact arrived in the
  retrieval pack, not the window.
- B (59) still beats AF-READ-001's 300-char-anchor arm (51) — the neighborhood
  finding from 001 replicated in the right direction; it just isn't sufficient.
- Loss anatomy (9 A-wins): 4 × C abstained-ish ("I don't know") on
  cat-1/4 gold that full memory surfaced; 2 × date drift; 3 × truncated
  multi-item answers. 5 C-wins include 2 date questions C answered correctly
  and 2 where C beat A on identical gold text.
- Neither B nor C ever emitted NOT ENOUGH INFORMATION (A: 2/120). An 8k
  window almost always *looks* answerable; abstention behavior does not
  transfer with this context format.

## Reading

AF-READ-001 showed a 300-char anchor cannot carry reading (−17). AF-READ-002
shows the fix is neighborhood (8k) plus breadth (CC80): statistically
indistinguishable from full-memory reading at **42% of its input tokens**, with
the entire residual gap in the gate-closed subset. This is the first
read-path configuration in the arc that a pre-registered reader test did not
kill. It is not superiority: at n=120 and net −4, C may be up to ~11 items
worse, and the WORKS call is exactly on its registered boundary.

## What it does not license

Single model (Qwen3-8B reader), single corpus (LoCoMo H120), one seed per
call, three-pass blind judge with no human audit. Non-inferiority at a point
margin. No product-path token accounting (deployed carries full history every
turn; 42%/turn compounds, but that is an engineering claim to be measured, not
claimed here).

## Next candidates

1. Scale: same three arms on the full 1,540-question LoCoMo dev — n is what
   this result lacks most.
2. Fallback seeds: the whole gap is BM25-top-1 seed choice; test the V2 gate's
   next-best anchor (2nd argmax) or a 2-window fallback on the 40-item subset.
3. Budget sensitivity: 8k/8k was one point; the frontier (does A-worth
   plateau at 12k total?) is unmeasured.

Artifacts: `artifacts/af_read002/{contexts.json,build_report.json,pilot.json,pfj.json,
reader/,blind_surface.json,judges/,results.json,run_all.log}`.
