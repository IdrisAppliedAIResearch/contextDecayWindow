# Evidence spine — PAPER-002

**Purpose.** Every number admissible in `paper/PAPER_002.md`, with its artifact and
its evidentiary standing. Built before any prose was written, so the draft is
assembled from this file rather than checked against it afterwards.

**Why this file exists.** `AGENTS.md` §8 requires every claim to trace to a
committed artifact. The academic-research-skills pipeline verifies *external*
citations against Semantic Scholar, OpenAlex, Crossref and arXiv; it has no notion
of this repository's internal artifacts, which is where every headline number
lives. This is the internal equivalent of that gate.

**How to use it.** A number may appear in PAPER-002 only if it appears here. A
number here may appear in PAPER-002 only with its standing honoured — see §1. The
companion file `DO_NOT_WRITE.md` holds the claims that may not be restated at all.

---

## 1. The standing taxonomy

Four levels. The taxonomy is the paper's honesty mechanism: it is applied once,
here, so the prose does not have to hedge sentence by sentence.

| Standing | Definition | What the paper may say |
|---|---|---|
| **CONFIRMATORY** | Pre-registered; sealed holdout; bars, endpoint and budget locked before the number existed; registration commit carries no implementation file | State it as an established result of this programme, with its scope |
| **DETERMINISTIC-OFFLINE** | Zero generative model calls; counts and identities rather than scores; byte-identical on replay; untouched by the instrument band | State it as measured, with the corpus named. Not a benchmark score |
| **NOT DEMONSTRATED** | A scored live comparison whose gap falls inside the measured 3.0-point instrument band | Report the number *and* the label. "Not demonstrated is not refuted" |
| **WITHDRAWN** | Corrected or retracted in `ERRATA.md` | Never restate. See `DO_NOT_WRITE.md` |

**The band, since it governs level three.** Five replicates of the deployed
configuration — identical corpus, settings, seed and standing runtime, back to back
in one server process (PID 29344) — scored **11.0, 8.0, 8.0, 8.0, 8.0**. Max minus
min is **3.0** on a 13-point rubric, against a decision rule committed *before* the
replicates ran. It is a switch, not a spread: replicates 2–5 are byte-identical
across all 121 turns; replicate 1, the only one meeting an empty server slot,
diverges at turn 1 (343 chars vs 80, from a byte-identical 757-byte prompt) and
never re-converges. Rater disagreement was measured separately and is near zero
(64 of 65 items unanimous), so this is run-to-run variation, not scoring noise.
`experiments/study_011/noise_band/` — `NOISE_BAND_REPORT.md`, `band_verdict.json`,
`DECISION_RULE.md` (committed `c07e1e27`).

Binding, and it cuts both ways: the band **may not be cited in support of any
adoption decision for K-first packing**. Study 011's B1 fired and that verdict is
final.

---

## 2. CONFIRMATORY

Five results. These are the only numbers in the arc that carry a sealed holdout with
bars locked before the seal opened. Three of the five are negative, which is the
point: the surviving design is small because these were built well and returned
nothing.

### C1 — NF-004, LoCoMo ranking granularity ★ the arc's strongest result

Pre-registration `95f0d25c8e898998dcbf0c8b95d370896c57c929`. Six sealed LoCoMo
conversations, 1,098 fully resolvable canonical QA records, 16,000-character
budget, **0 model calls and 0 embedding calls during measurement**.

| Arm | Complete evidence | Any evidence |
|---|---:|---:|
| `S_SESSION_RANK` (baseline) | 843/1,098 | 950/1,098 |
| `P_PAIR_RANK` (treatment) | **935/1,098** | **1,027/1,098** |
| Source order (no-ranking control) | 258/1,098 | 352/1,098 |

140 gains, 48 losses, 910 ties; net +92; ratio **2.92** against a registered bar of
2.0; one-sided exact binomial **p = 6.19e-12**. All six conversations net positive
(+7, +6, +13, +30, +15, +21). All five source categories net positive. Median packed
chars 15,986 vs 15,988. At the 32k secondary: 961 → 1,024. Median best-evidence rank
**9 → 2**; p90 **80 → 34** (opened only after the disposition was committed).
G0–G7 all PASS, including G3 vector seal 2,749/2,749 read-only hits with zero
misses, and **G7 replay SHA equal to the committed G6 SHA**.

`experiments/components/biological_memory/nf_004/NF_004_REPORT.md`,
`artifacts/g6_holdout_outcomes.json`, `artifacts/g7_result_integrity.json`

**Scope cap, binding:** availability only. No reader, live, universal-rule,
promotion or adoption claim is authorized.

### C2 — DMR-004, no mechanical sufficiency signal *(negative)*

Pre-registration `fd99a917…eefcfda` at `6ea982fa`. Sealed 180-query holdout, two
blind raters, PF3 verifying commit ordering from git history (protocol → labels →
registration → compiler → holdout labels → gates), registration commit carrying
exactly one file. **The strongest confirmatory construction in the repository.**

Youden's J **0.320** against a bar of ≥0.50 (FAIL); false-finite rate **0.188**
against ≤0.15 (FAIL); `LOOKUP` recall 0.800 against ≥0.60 (PASS); well-formed span
share 1.000 (PASS). Raw accuracy 0.706 — against an always-`OPEN` degenerate control
scoring **0.650**, which is why J and not accuracy was the registered statistic.
Inter-rater J ≈ 0.76 against the compiler's 0.320. Annotation agreement: raw 0.889,
Cohen's κ **0.770**.

Failure structure: 31 misses, of which 12 are *"Which happened first, A or B?"* —
a family flagged in writing before the compiler existed and deliberately not
patched. Adding registered markers `first`/`last` moved development J **0.363 →
0.220**.

`experiments/components/biological_memory/dmr_004/DMR_004_REPORT.md`

**Disposition:** a model-free adaptive controller is **not authorized**, and the
compiler **must not** be replaced with a second language-model call inside this arc.

### C3 — DMR-001, degenerate event formation *(negative)*

Pre-registration `f563b6c5…d28c41` at `33ed8c5d`. 2,000-episode sealed holdout.

**52 of 74 events close because `max_event_size` binds — forced fraction 0.703
against a bar of 0.35.** Drift precision on holdout 1.000 (20/20 drift boundaries
matched; 0 of 52 forced boundaries matched). The locked threshold 0.70 sits above
the holdout p95 (0.626) yet fires on 178/961 = 18.5% of eligible development
episodes against 20/1,703 = 1.2% of holdout. G1, G2, PF1–PF10 PASS (PF2: independent
implementations agreed on 0 mismatches across 1,724 episodes).

`experiments/components/biological_memory/dmr_001/DMR_001_REPORT.md`

**Two cautions.** The second G3 check is a **preflight defect — unreachable by
construction** (recorded, not repaired); the disposition does not depend on it.
G4/G5 were computed post-stop and are descriptive only — **they must not be cited
as results**.

### C4 — DMR-001C, transfer stability confirmed, boundary claim refuted

Rule frozen at DMR-001B's anchor `ad6f9451…c5ecc5e6`; registration commit `b839f8fd`
carries no file under `src/` or `tests/` (verified with `git show --stat`); corpus
fetched after the freeze. **50 unread LongMemEval haystacks, 11,453 episodes, 2,128
real session seams.**

- **G4 CONFIRMED.** Per-stream fire rate 3.41%–7.35%, p05–p95 3.83%–6.38%, ratio
  **1.67×** — against DMR-001's fixed threshold swinging 9× to infinity.
- **G5 FAIL.** T_ADAPT precision 0.837, recall 0.253, macro F1 **0.387**;
  `C_PERIODIC_4` (chop every four episodes) reaches **0.606**. The detector loses to
  fixed periodic chopping by 0.219.

**Self-audit recorded and honoured:** macro F1 against a dense-boundary corpus
(base rate 0.186, seams every 5.4 episodes) rewards frequent firing, so it was a
poorly chosen statistic — **and it is not being re-scored.**

`experiments/components/biological_memory/dmr_001c/DMR_001C_REPORT.md`

### C5 — SAL-001, no independent surprisal-proximity signal *(negative)*

Pre-registered; deterministic 60-history LongMemEval holdout; label-blind scoring
sealed. 93 eligible sessions, 545 exchanges, 98 marked, 92 session-level AUC
replications.

Adjusted neighbour AUC **0.41599** against a bar of ≥0.60; one-sided permutation
**p = 0.99134** against ≤0.01; bootstrap 95% [0.35132, 0.48388]. Raw 0.29984, prior
0.39929, next 0.47705. **Five of six strata below chance.** The registered effect is
in the opposite direction. Posthoc own-exchange AUC 0.621.

`experiments/components/biological_memory/sal_001/SAL_001_REPORT.md`

**Consequence:** HYPOTHETICAL-001's P1–P4 surprisal capture is killed.

---

## 3. DETERMINISTIC-OFFLINE

Zero generative calls, byte-identical on replay, unaffected by the instrument band.
These are counts and identities. They are real measurements and they are not
benchmark scores.

### D1 — NF-005, source-turn information dilution

465 turn-labelled LongMemEval items, 32,000-character budget, turn packing fixed,
0 model calls. Disposition `INFORMATION_DILUTION_SUPPORTED`, capped `CHARACTERIZED`
because the corpus was already observed.

| Arm | Any exact evidence | All exact evidence |
|---|---:|---:|
| Episode rank, episode pack | 351/465 | 201/465 |
| Episode rank, turn pack | 361/465 | 208/465 |
| **Turn rank, turn pack** | **461/465** | **454/465** |
| Source order, turn pack | 64/465 | 7/465 |

**100 gains, 0 losses, 365 ties; one-sided exact binomial p = 7.89e-31.** Median
best evidence rank 5 → 1; p90 131 → 7; median delivered 46 → 109 turns.

**Mechanism.** LongMemEval evidence episodes median **2,550 characters**; their
exact flagged source turns median **298**; LoCoMo adjacent pairs median **241**.
831 of 881 evidence flags are on user turns. Spearman rho **0.484** between parent
length and worse normalized own-cosine rank.

G0–G8 PASS. G5 vector seal 167,918 hits, zero misses. G8 outcome and replay SHA both
`06e4cbea…d7b7b322`.

`experiments/components/biological_memory/nf_005/NF_005_REPORT.md`

**Scope cap:** splitting changes length and semantic localization together, so this
**does not isolate raw character count**.

### D2 — NF-006, internal statement ranking

Corrected internal 121-turn store, 119 Q11-eligible episodes, 32,000 serialized
chars, 0 generation calls. Selections sealed outcome-blind at `ef074cda` before
measurement.

| Arm | Total | Civil | Art | Monetary | Marine | Units | Chars |
|---|---:|---:|---:|---:|---:|---:|---:|
| C0 episode rank / episode pack | **12/17** | 5/5 | 2/4 | 1/4 | 4/4 | 15 | 31,569 |
| C1 inherited rank / statement pack | **7/17** | 3/5 | 2/4 | 1/4 | 1/4 | 51 | 31,931 |
| T1 own-statement rank / statement pack | **14/17** | 5/5 | 1/4 | 4/4 | 4/4 | 80 | 31,991 |

Against C0: 3 gains, 1 loss, net +2. Against C1: 8 gains, 1 loss, net +7. **Targeted
gate 21/21 vs 21/21 — zero losses.** G0–G9 all PASS (G4: 791 statement units — 119
user, 672 assistant).

`experiments/components/biological_memory/nf_006/NF_006_REPORT.md`

**Two boundaries that must travel with this number.** The registered T1 trace
selects **no statement whose source turn is 90** — all four monetary items are
present, but DX-001's exact carrier remains unresolved. And art falls **2/4 → 1/4**:
this is a breadth composition trade, not universal dominance.

### D3 — NF-007, the coverage-count family closes

`STOP — FLOOR_INERT`. Labelled explicitly as an **instrument stop, not a mechanism
failure**: the registered instrument cannot distinguish treatment from control.

NF-006's sealed T1 already touches **all 16** carried clusters, so a one-per-cluster
floor forces zero admissions and displaces zero incumbents. Allocation after entry
is sharply uneven: cluster 0 (82/91 civil) supplies **30 of 91 candidates = 33.0%**;
cluster 12 (132/137 monetary) **14 of 137 = 10.2%**; the five art-majority clusters
(3, 5, 8, 9, 15) together **9 of 168 = 5.4%**. **44 of 80 slots go to clusters 0 and
12.** Part 1: 119 parents → 791 statements across 16 nonempty clusters; Renaissance
art contributes **194 of 791 candidates (24.5%)** while T1 delivers 1 of 4 art facts.

Artifact 4,228 bytes, SHA-256 `91804a13…ded68f05`; second execution byte-identical.

`experiments/components/biological_memory/nf_007/NF_007_REPORT.md`

**Gate lesson worth reporting:** the first Part 1 execution returned the stopping
branch only because its evaluator searched for nonexistent short domain labels. The
invalid artifact is preserved and corrected by standalone amendment.

### D4 — EC-002, packing priority is a causal delivery gate

500 EC-001 stores replayed with **only packing order changed**; 0 reader inference,
0 embedding calls. A0 = recency→K→coverage (deployed); A1 = K→recency→coverage.

| Outcome | A0 | A1 | Gains | Losses |
|---|---:|---:|---:|---:|
| Any evidence session | 109/470 (23.2%) | **261/470 (55.5%)** | 152 | **0** |
| All evidence sessions | 34/470 | 137/470 | 103 | 0 |
| Any exact answer turn | 79/470 (16.8%) | 196/470 (41.7%) | 119 | 2 |
| All exact answer turns | 20/470 | 106/470 | 86 | 0 |

+32.3 percentage points on the primary. Within the 401-question top-four subset,
96 → 248 with 152 gains and no losses. Delivered K episodes rise **26 → 476**.

**The medians concealed the change** — block size stays 31,920 chars and path counts
stay 16 recency / 0 K / 1 coverage. Residual: 209/470 still recall no evidence
session.

`experiments/external/longmemeval/EC_002_REPORT.md`

**Scope cap:** A0 is a reproduction under recomputed embeddings, not a byte-exact
replay. **EC-001 is permanently unreplayable at bit granularity** — its cache was
not retained, and CC-006's protection is prospective only.

### D5 — IC-001, packing gates internally too

Corrected 121-turn internal run, both orders over frozen candidate identities;
0 inference, 0 embedding, no vector re-derived.

Q11 **6/17 → 7/17** (one gain, zero losses). Targeted across eight probes
**14/21 → 18/21** (four gains, zero losses). **Under the deployed order the
similarity path delivered zero episodes and zero characters at 8 of 8 probes**;
under K-first, 9 episodes and 14,796 characters. At Q11, B1 delivers 12 episodes in
31,863 characters against B0's 8 in 31,946 — four more episodes in 83 fewer
characters.

`experiments/internal/packing_priority/IC_001_REPORT.md`

**Note for §"what LV-001 measured":** B1's window contains the turn-1 and turn-2
episodes B0 dropped — the two formatting-rule plants LV-001 reported the shipped
configuration could not see.

### D6 — Study 011, the deployed similarity tier is inert

| Arm | Config | Q11 avail | Targeted | K-path episodes | Score /13 |
|---|---|---:|---:|---:|---:|
| A | STM only, N=32 | 9/17 | 7/21 | 0 | 8.0 |
| B | LTM only, K=0.48 | 0/17 | 10/21 | 19 | 7.5 |
| C | Both, K-first | 10/17 | 10/21 | 13 | 7.0 |
| D | Both, recency-first (deployed) | 9/17 | 7/21 | 1 | 8.0 |

**Arm D scored identically to Arm A on all thirteen questions**, with byte-identical
windows at three late probes (31,969 chars at turn 117, 30,588 at 118, 31,867 at
119). That identity is an offline-verifiable fact and is *not* touched by the band.
The C − D = −1.0 score gap **is** — see §4.

`experiments/study_011/study_011_report.md`

### D7 — AR-001, the target was affordable

Exact minimum for ≥14/17 breadth items = **5,058 characters across 5 episodes**
(turns 90, 112, 113, 115, 118), leaving 26,942 of the 32,000 budget unused. Greedy
variant reaches 15/17 at 5,455. All 17 costs 7,592. Domain minima: civil 826, art
3,182, monetary 2,913, marine 824.

`experiments/components/retrieval_mechanism_ledger/artifacts/ar_001/AR_001_report.md`

**Scope cap, mandatory:** both optima are computed **with the answer key**. They are
bounds, not methods. And per Cycle 1 objection C2, four of the five optimum episodes
are prior probe exchanges whose earlier answers were largely wrong.

### D8 — E005 and the deployed baseline

A0 baseline **6/17** across 3/4 domains at 31,946 chars / 8 episodes. Best
gate-passing configuration `A3_l0.1_r0.0_k16`: **12/17 across 4/4 domains**, 15
episodes, 31,569 characters, 4 of 5 oracle episodes, 16/16 targeted preserved.
Facility location led on raw count at **13/17** and **passed no gate** — monetary
0/4 at every setting.

`experiments/components/retrieval_mechanism_ledger/artifacts/e005/E005_report.md`

**Correction that must travel with it:** "every one of 146 configurations beat 6/17"
is true only on the 119-episode pool. Per-pool minima are **7 / 5 / 4**, and on the
deployed 34-episode pool the shipped configuration scores **5/17 against the
baseline's 6/17**. See `DO_NOT_WRITE.md`.

### D9 — DX-001, the selection miss that ships

Target turn 90, cosine rank **112/119**, cosine **0.0560**, 2,862 chars, 4 monetary
items. Configurations examined 146; configurations that selected it: **0**. It needs
cosine **0.225032** and has 0.05599; **20 of 119** episodes clear that bar.
Terminated on budget with 431 chars remaining. **M1 cluster collision REFUTED** —
its cluster is never entered, so the diversity term was payable in full at every
step.

`experiments/components/retrieval_mechanism_ledger/artifacts/dx001/DX_001_report.md`

### D10 — DR-002, the pool binds first, structurally

The four highest-cosine episodes carry none of the enumeration probe's facts. Both
art contributors sit at cosine ranks **50 and 86**, so the deployed 34-episode pool
**contains no art episode and cannot reach four domains at any setting**. This
follows from the pool's contents, not from a measured comparison — which is why it
is the load-bearing claim of the forced order. Dropping the 19 lowest-cosine of 119
costs an entire domain.

`experiments/components/retrieval_mechanism_ledger/artifacts/e005/dr_002/DR_002_report.md`

### D11 — Cost and operating envelope (CC-003 / CC-005 / DX-002)

- **Delivered context is bounded because enforced.** Replaying 1,000 committed
  episodes through the library at 32,000 chars: 0 of 1,000 turns breach; p95 moves
  **+18 characters** across the final five buckets. **It truncates on 895 of those
  turns**, dropping up to 70 episodes and wanting up to 65,864 characters. Both
  readings belong together.
- **Disk is cheap.** 4,743 bytes per turn at the margin, 86% embeddings; about
  **48 MB at 10,000 turns**.
- **Latency binds.** **190 ms at 1,000 candidates**, clustering **81%** of it and
  rising from 37%. Exponent **1.25** over 50–1,000. Comfortable to a few thousand
  episodes; unusable in an interactive loop somewhere before 10,000.
- **The growth was the harness's.** In the Study 010 runner the block rose +23,238
  and +28,701 chars; replayed through the extracted library it moves +18.

`experiments/components/deployment_closeout/`

**Runtime identity:** llama.cpp, 27B generation model at UD-Q6_K_XL, one slot, fixed
seed, speculative decoding disabled; Qwen3-Embedding-0.6B over SQLite with
`sqlite-vec`. Selection timings exclude embedding. One machine. Only the exponent
and the clustering share plausibly transfer.

### D12 — The component's certified guarantees (CC-002 / CC-006)

All **132 committed selection payloads** and **3 committed rendered blocks**
reproduce their SHA-256 byte-for-byte through the installed `episodic` library.
`context()` is a pure function of store state, query and budget, verified
byte-identical across two processes. Full suite **1,007 tests** at closeout (1,028
at CC-006). The DX-001 embedder call-shape sentinel (H1) is asserted on every store
open; pool trimming exists only under an `unsafe_` name carrying DR-002's finding
in its docstring (H2).

`experiments/components/library_extraction/CC_002_library_extraction.md`,
`experiments/components/embedding_cache/CC_006_report.md`

### D13 — Ranking-budget controls, and two refuted explanations

At 32k on LoCoMo development, all-evidence: **source order 279 / session rank 773 /
pair rank 826 of 868**. Session ranking beats source order by **494 items**, far
outside the pre-declared within-five non-discrimination interval — **the
slack-budget explanation is refuted**. Pair ranking beats session ranking at every
truncated budget 4k→80k, tying only at 96k when everything fits.

**The cross-corpus binding-ratio scope condition is REJECTED.** Seven overlapping
cells have opposite all-evidence signs; the sharpest is LoCoMo 4k at median 19.85×
net **+123** against LongMemEval 24k at median 19.39× net **−14**.

Primary budget 16k was chosen because its baseline is off-ceiling (702/868 = 80.9%)
at binding ratio 4.96× — **explicitly not for the largest treatment effect.**

`experiments/external/locomo/RANKING_BUDGET_CONTROL_REPORT.md`

### D14 — EC-001, external calibration

All 500 cleaned LongMemEval-S questions through the unchanged shipped component.
Only **69 of 470 answerable (14.7%)** place every evidence session below the top
four; median evidence-session rank **2**, p95 23. **401 of 470 have evidence in the
top four, but only 96 of those 401 retrieve any evidence session.** Any-session
recall 109/470 (23.2%). Every block truncated; median composition **16 recency, 0
non-recency K, 1 coverage**; **91 of 109 session hits come from recency**.

`experiments/external/longmemeval/EC_001_REPORT.md`

**Binding, Amendment 010:** the 20.0% equal-quota and 12.22% post-stratified figures
are **Codex-substituted integrity scores**. They may **not** be placed against any
published LongMemEval result. The pinned GPT-4o evaluator was unavailable.

**Also load-bearing for the positioning section:** the benchmark authors'
LLM-assisted indexing and time-aware query expansion **were available and
deliberately not adopted**, because they add generative calls to the memory path.

### D15 — The three-arm granularity synthesis (NF-003)

Same 465 items, same 32k budget: session-rank/session-pack **375/465**;
session-rank/episode-pack **388/465**; episode-rank/episode-pack **351/465**. Finer
packing +13 (17 gains / 4 losses); finer ranking −37 (26 gains / 63 losses). The 63
items rescued by coarse ranking have median own-episode cosine rank **46** (p90 135);
the 26 gained by fine ranking, median **10** (p90 21).

`experiments/components/biological_memory/nf_003/NF_003_THREE_ARM_FINDING.md`,
artifact SHA-256 `4473c8c5…2a16c1b6`

**Scope cap:** posthoc characterization on an exhausted corpus. **Not** a registered
universal law. Reconciled with NF-005 as: *rank at the finest unit whose embedding
remains informative; pack at the finest affordable unit.*

---

## 4. NOT DEMONSTRATED — inside the 3.0-point band

Report the number, report the label. **"Not demonstrated" is not "refuted."** These
may well be real; a single run per arm on this instrument cannot tell.

| Result | Gap | Source |
|---|---:|---|
| Study 009 memory-tier contrast, S 9.0 vs L 12.0 | 3.0 | `experiments/study_009/` |
| LV-001 targeted regression, 3.5/8 → 1.5/8 | −2.0 | `experiments/components/live_validation/LV_001_report.md` |
| Study 011 tier-isolation, Arm C 7.0 vs Arm D 8.0 | −1.0 | `experiments/study_011/` |
| Corrected treatment series, 8.5 → 12.0 | 3.5 | Exceeds the band — and **exceeding a band is not being demonstrated** |

**Study 009 has *less* protection than Study 011, not more.** Arm S ran 2026-07-26
21:19; Arm L is a preserved Study 007 artifact from 16:36 the same day. Neither
manifest records a server PID. The process state of the arc's cleanest architectural
contrast is uncontrolled and unknowable from the committed artifacts.

**LV-001 in full, because it is the honest centre of the paper.** The shipping
configuration's six-item offline advantage produced **+1** correctly attributed item
(B1 WEAK) and a **2.0 loss** on targeted probes (B2 FAIL, four times the registered
0.5 tolerance). B2 was registered as a kill. Status: **not promoted**. The mechanism
is legible — asked for the two formatting rules planted in turns 1 and 2, the
shipping configuration reported it could not see the start of the conversation.
Offline, that same configuration preserved 16/16 targeted items. **Preserving an
item's availability and preserving the answer that depends on it are not the same
property, and this programme had measured only the first.**

---

## 5. Programme-level ceilings the paper must state

1. **LongMemEval is exhausted.** Every item has been used. No confirmatory claim is
   available from that corpus again; a registration written today inherits that
   ceiling.
2. **The runtime is not bit-reproducible.** Identical 757-byte prompt at seed 5005,
   `--parallel 1`, no speculative decoding: responses diverge at character 79. The
   standing byte-identical-rerun rule is satisfiable *between runs sharing server
   process state* and **not** between a cold-start run and a warm-start one — and
   **no study in the arc pinned process state.**
3. **Availability is not correctness.** Measured, by LV-001, moving in opposite
   directions.
4. **The internal breadth findings rest on a single enumeration probe.** One
   question, worth 17 items, at turn 120.
5. **One embedder, and positive evidence of fragility.** The *same* embedder given
   the same text under a different call shape returns a vector agreeing to cosine
   **0.999837** that flips **6 of 146** committed payloads.

---

## 6. Provenance of this file

Compiled 2026-08-18 on branch `paper-rework` from a full read of `README.md` (below
the `# For LLM Context` divider), `AGENTS.md`, `ERRATA.md` (19 entries),
`paper/reviews/` (Cycle 1's sixteen objections, Cycle 2's ten, the Pass-6 slop
audit), `paper/CLAIM_TO_ARTIFACT.md` (C1–C138), `paper/notes/EVIDENCE_INDEX.md`,
and every study and component report under `experiments/`.

Numbers here are quoted from those reports. Where a report and a summary disagreed,
the report won — which is Cycle 1's own closing diagnosis: *"Pass 3 was written from
the source reports' headline sentences rather than from their boundary sections, and
the boundary sections are where this program keeps its scope discipline."*
