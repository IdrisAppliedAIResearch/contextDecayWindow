# RS003 Stage-0 Results: Specialist Admission Oracles

**Pre-registration:** `RS003_STAGE0_PRE_REGISTRATION.md`, commit `d9edfc26`
(branch `study/rs003-specialist-stage0`).
**Amendment:** `AMENDMENT_RS003_001_cc80_identity_check.md` (instrument check
#5 proxy -> exact reproduction identity; recorded before any arm metric was
produced).
**Artifacts:** `artifacts/rs003_{temp,mh,sem}_results.json`. All arms
double-run identical (PF6/§7). Zero model calls: every vector is a frozen
cache lookup; every mechanism is regex, frozen spaCy NER, frozen
`rank_cc80`, or exact numpy arithmetic.

## Bottom line

**R-TEMP: KILL. R-MH: KILL (all three arms). R-SEM: DEAD (family).**

No specialist family reaches even the registered SIGNAL tier against CC80's
frozen order on its own population. The ceiling is not the ordering
objective's *ranking of retrievable gold* — every family's gold-first
ORACLE pack reaches full admission on 100% of its population at both 8k and
16k — so gold is mechanically packable; what failed is every deterministic
re-ordering tried as a route to it. The remaining gaps behave like the
representation-capacity residuals characterized by the DA-arc (DX/DA-014
line), not like a mis-ordered similarity rank.

## Instrument (all three scripts, before any metric)

- `ORACLE_full` coverage 1.0 on 120/120; gold dia-ids all in-pool.
- Committed blocks within cap; B/C controls replayed verbatim from
  committed `dialogue_ids="…"` spans.
- Gold mechanical admissibility: 120/120 items pack their full gold set at
  8k; 61/61 B-misses admissible at 16k (R-MH gate needed ≥10).
- CC80 reproduction identity (AMENDMENT_RS003_001): harness `rank_cc80`
  order equals `retrieve_long_term(legacy_cc80, recency_window_n=0)`'s own
  `ranking.order` exactly on 120/120, and its selected count equals the
  committed `n_cc80` on 120/120. The originally registered ±2 pack-count
  proxy fails (22.17 vs 24.35) for a benign reason — the deployed packer
  budgets rendered episode tags, not raw joined text — documented before
  results.
- Recomputed zero-gold-in-B rate on the 14-item audit population: 8/14
  (0.571). The recorded forensic figure (~72% over a 24-item subset) uses a
  population whose membership file is absent from the repo; reported side
  by side per §7, not reconciled.

## R-TEMP (cat2, n=20, registered rule pack)

| arm | full-admission | zero@Bmiss | mean cov |
|---|---|---|---|
| B_as_is | 11/20 | 7 | 0.600 |
| **CC80_16000** | **18/20** | 0 | 0.950 |
| T1 gold-anchor (best of 16: d, ±chron/rev, caps) | 12/20 | 6 | 0.600 |
| T1_gold_d7_chron_16000 (registered judge arm) | 10/20 | 8 | 0.500 |
| T2 relative-resolution Δ7 16000 | 5/20 | 11 | 0.250 |
| ORACLE (gold-first) | 20/20 | 0 | 1.000 |

Verdict **KILL** (registered: KILL iff T1 margin < +10pp over CC80_16k;
BUILD iff margin ≥ +10pp, T1 zero-admission ≤ CC80 zero-admission, and T2
recovers ≥50% of the T1 margin; the between-tier is reported as SIGNAL,
never BUILD, and is only meaningful at ≥ +20pp on the parseable subset with
T2 ≥ 50%).
Observed: T1 margin **−40pp** (registered judge arm 50%; best of the 16
registered window variants 60%; CC80 90%); on the
gold-parseable subset (16/20) margin −37.5pp; recovery not computable
(T1 margin negative). Disposition gate is item-count based per the
registration ('+10pp = 2 items' at n=20): T1 10 vs CC80 18 (−8 < bar 2;
parseable subset 10/16 vs 16/16, bar 3). Gold-answer dates parseable on
16/20 items; bucket decomposition (relative wins over gold-parse): 9
absolute-in-gold (6 day anchors, 3 month anchors), 8 relative-in-evidence,
3 unparseable. Dual-parser resolution agreement where both sides parse: 4/7.

**OCR review fixes (post-result, verdict-invariant).** OCR scan of the
implementation found three rs003_temp.py defects, all fixed and re-executed
with identical arm numbers and KILL: (1) the disposition gate compared
rounded float rates, which can misbehave exactly at the +10pp boundary —
now gated on integer item counts (bar 2; parseable bar 3); (2) the
registered expression 'the week before' was matched for bucketing but never
resolved (silent T2 drop) — now resolves to anchor−7 (no cat2 evidence turn
contains it, so arm numbers are unchanged); (3) month/year shifts in
`resolve_relative` could raise ValueError on end-of-month/Feb-29 anchors —
now clamped via `calendar.monthrange` (no such anchor occurs in this data).

**Gold-parser faithfulness note (implementation fix, post-result,
verdict-invariant).** The initially committed run resolved
`The <weekday> before <date>` to the resolved anchor *day* (window ±Δ around
that day). The registered text assigns that form a *month window containing
the resolved anchor*; the faithful re-run above is the committed number. The
faithful variant is marginally weaker on the judge arm (10/20 vs 11/20 — the
wider month window dilutes chronological packing on conv-26/conv-42), so the
KILL is stronger under the literal registration. A third reading (strict
full-date-first cascade, weekday rule subsumed) also KILLs (−35pp). All three
variants KILL; no arm in any variant comes within +10pp of CC80_16k.

Why it loses: the registered kill-branch premise itself — cat2 gold is not
temporally localized. Gold turns for a single question spread across months
and sessions, so a ±d window around a parsed anchor date (even a perfect
one) drops gold rather than adding it; and CC80 at 16k already admits full
gold sets on 18/20 cat2 items. Date-window *filtering* is a negative on this
corpus at these budgets. Consistent with the recovered brief's own kill
condition ("kill if gold-anchor oracle doesn't lift cat2").

## R-MH (cat1 multi-hop, n=26, set-coverage)

| arm | full-admission | wins/losses vs CC80_16k | p (one-sided) | reg@cat≠1 |
|---|---|---|---|---|
| B_as_is | 0/26 | — | — | — |
| **CC80_16000** | **14/26** | — | — | — |
| D1 PPR dual-anchor ray | 10/26 | 2/6 | 0.965 | 0 |
| D2 facility-location protected | 6/26 | 3/11 | 0.994 | 12 |
| D4 cluster-diversity (A3-style) | 15/26 | 1/0 | 0.500 | 0 |
| ORACLE_pack_16000 | 26/26 | — | — | — |

All three **KILL**. D4's single discordant gain (1 item, 57.7% vs 53.8%,
p=0.5) is noise-level; D1's Personalized PageRank diffusion over
kNN(k=4,τ=.30)+temporal(±1,±2)+NER co-occurrence edges actively demotes
gold relative to raw similarity; FL's marginal-gain greedy (12 regressions)
confirms E005/TC-007's original finding on new data. Check (d)
(zero-admission halving) was vacuous because CC80_16k already has 0
zero-admissions among B-misses; resolved conservatively (cannot pass),
which only withholds BUILD and cannot manufacture it.

Interpretation: multi-hop gold for the 12 recoverable cat1 items is in the
pool and packable (ORACLE 26/26) but sits low in *every* similarity-graph
neighborhood we built — the HippoRAG-lite recipe the recovered brief
promoted does not carry this corpus's multi-hop answers under a
zero-LM-graph constraint.

## R-SEM (cat3+cat4 semantic lane, n=74, 8k primary)

| arm | full-admission | margin vs CC80_8k | p | regressions@cat1+2 |
|---|---|---|---|---|
| B_as_is | 52/74 | −13.5pp | — | — |
| **CC80_8000** | **62/74** | — | — | — |
| R2_RRF (k₀=60) | 63/74 | +1.4pp | 0.500 | 4 |
| R1_head (answer-aware CV head) | 58/74 | −5.4pp | 0.927 | 14 |
| ORACLE_rerank | 74/74 | +16.2pp | — | — |

Family verdict **DEAD** per §6 (BUILD: none; SIGNAL ≥+3pp & p<.10: none).
ORACLE instrument passed fully (74/74 items pack gold at 8k), so the 16.2pp
ceiling is real and *reachable at budget* — but a gold-label-trained,
conversation-level-CV answer-aware head lands 5.4pp *below* CC80: the
remaining semantic-lane misses are not separable from hard negatives by
dense/BM25/overlap/recency/length/session features. cat3 alone (n=6,
stated, not hidden): B 1, CC80 2, R2 3, R1 3, ORACLE 6 — underpowered, no
reading. This is the honest null the recovered brief pre-sanctioned.

## Cross-family reading (bounded per §9.1)

Closed by this study — exactly this, no more: on LoCoMo's dev-120 audit
population at 8k/16k raw-char packs, **date-window retrieval,
zero-LM graph-ray expansion, protected facility location, cluster
diversity, RRF, and feature-based answer-aware reranking each fail to beat
frozen CC80 order on the population the recovered briefs assigned them.**
Open and unchanged: the ceiling gap between CC80 and gold-first packing
(+35pp R-MH, +16pp R-SEM) is real and mechanically reachable — some route
to it exists, but it is not re-weighting, re-ordering, or windowing the
same vector space. That matches the DA-arc conclusion (compact carriers /
dependency addressability, not ranking, is what moved these residuals).
Router dispatch (PLAN-RS003) has no surviving specialist to dispatch to at
Stage-0 bars.

## Limitations

- Populations are small (20/26/74); sign tests on n=26 are coarse
  (smallest achievable p≈0.015–0.03).
- T1 uses dates parsed from *gold answers* (registered oracle-side design);
  deployment-grade anchor extraction would be strictly weaker, so T1's
  −35pp is an upper bound of the temporal-lane win.
- The R1 head is an oracle-cap simulation (gold training labels); its
  −5.4pp says the ceiling is not feature-reachable, not that a smaller real
  head could not tie CC80.
- Gold evidence labels are noisy (parser agreement 4/7 on dual-derivable
  items; label answers sometimes non-dates).
- B-miss zero-admission check (d) vacuous at 16k (control already 0).
- X1–X4 miss typology not recomputable here (registered limitation §6).

## Next (for user decision, not auto-run)

1. Accept the three kills; record digest entries; close branch PR.
2. The surviving lever from the recovered briefs is the DA-arc line
   (exact carriers/dependency addressing) where +16/+35pp ceilings are
   already characterized — Stage-0 found nothing in re-ranking.
3. Optional, pre-registerable: re-run R-MH Stage-0 on NF-004's 1,098-item
   sealed corpus (bigger n; but same-family prior is 0/3 here).
