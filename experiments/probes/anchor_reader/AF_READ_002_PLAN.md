# AF-READ-002 — Chronological anchor builder under fixed budgets (PRE-REGISTRATION)

Status: LOCKED at commit of this file. No implementation in this commit.
Predecessor: AF-READ-001 (`f75f590d`, DEAD: ±2 window replaced memory, net −17).

## Question

AF-READ-001 killed "anchor window *replaces* memory" (332 tok = 51/120 vs
deployed 10.7k tok = 85/120). Untested: anchor-*ordered* chronological retrieval
that keeps whole turns and spends a bounded budget. Does growth past+future
around the anchor, capped at 8k chars (+8k CC80), hold deployed accuracy at
roughly a third of its tokens?

## Arms (H120 primary only — the build2 heldout, fresh to V2)

| arm | content | char cap |
|---|---|---|
| A_DEPLOYED (reused) | frozen AF-READ-001 answers + votes, SHA-verified | ~28.7k median |
| B_ANCHOR8K | anchor builder only | 8,000 |
| C_ANCHOR8K_CC80 | anchor builder + CC80 relevance pack, deduped, one chronological block | 8,000 + 8,000 = 16,000 max |

**Reuse is registered, not ad hoc.** A-arm responses are re-used byte-identically
(reader prompt SHA must equal AF-READ-001 `contexts.json` a_sha; BASE unchanged:
seed 5005, temp .6, n_predict 4096, thinking off). A-arm judge votes are reused
under PF-J below. No new A calls.

## Anchor builder (frozen spec)

1. **Seed.** V2 (ckpt_V2_20261011) scores all conversation turns; pool P(null)
   with τ=0.2 exactly as AF-READ-001. Gate open → seed = V2 argmax. Gate closed
   → seed = BM25 top-1 turn (arms.BM25, champion contract). The gate picks the
   seed *producer*; the builder always builds — no arm can degenerate to empty.
2. **Growth.** Alternating rings s+1, s−1, s+2, s−2, … over source-order turns;
   a turn joins iff the re-rendered block stays ≤ cap; non-fitting turns are
   skipped and the ring walk continues until nothing more fits (whole turns
   only — never mid-turn truncation).
3. **Envelope + budget.** Identical record envelope as AF-READ-001 arm B
   (session-contiguous `<record session=... date=... dialogue_ids=...>` runs,
   speaker-prefixed lines, chronological source order), rendered through the
   frozen `render_reader_prompt` shell. Budget = len(rendered record block),
   excluding instruction shell.
4. **CC80 (arm C only).** The legacy CC80 budget packer as pre-timeline-adoption
   (library/component path pinned at implementation; PF2 requires byte-identical
   replay of one reference block). Query = the question; vectors = the frozen
   MiniLM embedding DB backing the timeline artifacts. Candidates exclude turns
   already in the anchor block; its block ≤ 8,000 charged separately. Anchor
   block + CC80 turns merge into ONE chronologically rendered envelope block.
5. Contexts are gold-free; gold stays in the sealed gold.json until judging.

## Reader + judge protocol (unchanged from AF-READ-001)

Server: same frozen launch pin, port 8099, ctx 40960, parallel 1, thinking off
(suffix asserted), calibration gates (arithmetic ×2 + 15 judge fixtures) before
any scored call. BASE as above; fit gate tokens+4096 ≤ 40960.
Judge: `render_judge_prompt`, 3 passes, seeds 9100/9101/9102, temp .2 top_p .9,
blind surface over the three arms simultaneously, majority correct, empty = 0.
**PF-J (reuse validation):** replay 5 A-arm judge prompts × 3 seeds (15 calls);
verdicts must match the stored AF-READ-001 votes or the run aborts.

## Bars (fixed now, both tiers, reachable in each direction)

- **IMPROVES** = C−A net > 0 with p < .05.
- **WORKS (non-inferior compression)** = C−A net ≥ −4 AND two-sided McNemar
  p > .05 AND mean C tokens_in ≤ 0.60 × mean A tokens_in.
- **SIGNAL** = C−A net ≥ −8 or B−A net ≥ −8 (builder retains most; successor
  budget/scheduler tuning justified).
- **DEAD** = C−A < −8 and B−A < −8 (full memory dominates at these budgets too).
B−A and per-category/token tables are reported regardless. τ-sweep (0.05/0.2/0.4)
and gate-open-vs-closed seed provenance reported offline.

## Preflight

- PF1 inputs: AF-READ-001 contexts/gold/answers/vote SHAs recorded; V2 ckpt SHA;
  embedding DB SHA from part1.json; BM25 contract = arms.py.
- PF2 identity: V2 argmax/pnull replay == AF-READ-001 build for all 120 (GPU);
  A-prompt SHA equality for all 120; CC80 reference block byte-identical.
- PF3 gates execute before scored calls (calibration file-gates, asserted).
- PF4 achievability: block-size distribution computed offline pre-lock — cap
  binding expected (median B near 8k, min > 0); reachable bars by construction.
- PF5 keys: qid + content SHAs only.
- PF6 anchor: server-native arm-A template identity (as before) + PF-J.
- PF7 n/a (no feedback loop). PF8 n/a.
- PF9 surrogate: judge blind to arm; empty answers score 0; reuse cannot flip A
  votes (PF-J).
- PF10 live reader: this IS the live read; availability alone claims nothing.

## Budget and order

~240 reader (B, C) + 360 new judge + 15 PF-J ≈ 615 calls, est 2–4 h.
Commit order: this plan → implementation + frozen contexts (gold sealed) →
pilot → reader answers complete → blind surface → judge votes → score.
Runner mirrors AF-READ-001 (script-owned server lifecycle, resumable, phase
commits; run_all pattern unchanged).
