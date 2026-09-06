# Preliminary temporal–DA fusion: implementation and preflight

Exploratory Part 1 complete, September 6, 2026. Plan: **168b9cfd**. Implementation: 4324f641; instrumentation repair: e19704ad; committed structural gate/output: **76a6e9b9**; analysis: 6556c468. Existing exposed Study E data only. No reader or embedding calls; no efficacy disposition or adoption.

**The draft runs correctly and finds six missing evidence records, but displaces seven others. It does not establish that this fusion improves retrieval overall, and it says nothing new about reader correctness.**

## What was implemented

Study E C1 retains its entire protected temporal block. The remaining retrieval order uses the original DA-001 TEMPORAL function, extracted unchanged from its pinned source AST: each original semantic seed emits itself, then its previous and next source-session neighbor. Duplicates are emitted once. All original candidates are seeds; there is no fitted seed-count cutoff and no recursive frontier. The existing whole-episode renderer and 32,000-character retrieval allowance remain, as does additive last-32 continuity.

This is a **DA-001 link adaptation**, not a port of the full DA-098/101 allocator. Synthetic Study E episodes are mapped to DA pair nodes, and each history is mapped to one session. All-seed traversal is also a new configuration. No compact codec, member selection, learned association, effective-update parser or score threshold was added. Temporal adjacency supplies candidate priority, not a guarantee that neighbors explain each other.

The query rule activates 160 histories: 128 answerable before queries and 32 before queries whose answer is absent. All 32 latest contexts are unchanged. Protected temporal admissions are preserved exactly. Other semantic records may be displaced, and later-event candidates remain possible as in the original semantic route.

## Existing-run diagnostics

| Questions | C1 complete evidence | Fusion complete evidence | Gains | Losses |
|---|---:|---:|---:|---:|
| All before, 128 | 109 (85.16%) | 108 (84.38%) | 6 | 7 |
| Straight, 32 | 27 | 28 | 2 | 1 |
| Irrelevant notes, 32 | 28 | 27 | 1 | 2 |
| Future update, 32 | 28 | 25 | 1 | 4 |
| Unaccepted proposal, 32 | 26 | 28 | 2 | 0 |
| Latest, 32 | 21 | 21 | 0 | 0 |

Six of the 19 existing misses are rescued; 13 persist and seven new misses appear. All 13 discordant questions have **identical record counts across arms**. Across all before questions, counts match on 119/128; each arm retrieves 40–41 records, median 40. Thus the observed rescues are not explained by retrieving a larger number of records. This is still no proof that the links are selectively useful across questions.

The draft replaces a median 11 records per before question (range 6–17) and delivers a median 20 records first emitted by links outside the protected block (18–22). Median serialized retrieval length is 31,345.5 versus 31,356.5 characters, and both maxima are 32,000. Additive continuity makes full context approximately 57,000 characters; 32,000 is not the full reader-context limit.

All 32 absence contexts change. Because these questions have no required location evidence, availability is not an applicable success metric; the zero completeness counts in raw diagnostics must not be called zero accuracy or proof of unchanged abstention.

## Concrete cases

All six rescues are effective location updates admitted as the next neighbor of an earlier semantic seed:

| Project | Parent turn → rescued turn | Recovered location | Records in each arm |
|---|---|---|---:|
| Meadow-840 | 63 → 64 | warehouse | 40 |
| Harbor-553 | 81 → 82 | laboratory | 41 |
| Orchard-584 | 53 → 54 | office | 40 |
| Harbor-967 | 60 → 61 | workshop | 41 |
| Riverside-978 | 58 → 59 | annex | 40 |
| Riverside-324 | 80 → 81 | annex | 40 |

The seven losses are Meadow-797 turn 55 (depot), Orchard-664 turn 44 (hangar), Meadow-455 turn 61 (hangar), Meadow-784 turn 49 (annex), Orchard-604 turn 71 (studio), Meadow-283 turn 47 (laboratory), and Harbor-701 turn 73 (office). These records were supplied by C1's semantic fill and are displaced in the fusion. Protecting the temporal block does not protect all sufficient evidence. Meadow-784's lost update is itself reachable by a link from turn 48, demonstrating that link reachability is still not packed delivery.

Full questions, source text, required-record changes and parent identities are in `artifacts/diagnostic_rows.json`; all label-free ordered selections, links and rendered contexts are in `artifacts/blind_outputs.json`.

## What the precedents establish

- DA supplies an executable temporal-link mechanism. Here it recovers six real misses at the same record counts, demonstrating a complementary route in those cases.
- DA-098's strongest availability result used a compressed accounting scheme and a preserved earlier allocation. Its 1068/1098 result does not predict performance under Study E's full rendered-record accounting, and was never a reader-success result.
- HH-005 documented that DA substitution can exchange useful context for other useful context: 32 reader gains and 48 losses against ASPECT-v1. The current 6/7 availability trade is consistent with that displacement concern, but is a different population, mechanism configuration and endpoint.
- The score-curve probe established that missing updates already have high query correlation. This fusion changes delivery order, not those correlation scores. It provides no evidence that a fused score gradient becomes smoother or that a completion threshold exists.

The narrow finding is complementarity with displacement. It supports examining admission decisions if this design is developed further; it does not justify adopting this traversal or declaring DA fusion generally unnecessary. No post-result tuning was performed.

## Preflight evidence and limits

| Check | Executed evidence |
|---|---|
| PF1 | Manifest hashes checked for all five input files; 192 histories/26,880 records. Clean pinned E, D, engine and DA checkouts; input hashes in `preflight.json`. |
| PF2 | Exact original DA function AST executed; two-session neighbor fixture, active and inert orders, full 140-record real traces, duplicate/permutation assertions. New mapping disclosed above. |
| PF3 | Outputs/gate committed at 76a6e9b9 before analysis implementation/execution. Failed-gate fixture rejects measurement. Analysis verifies committed artifacts and output hash before reading labels. |
| PF4 | No efficacy bars. Active/inert traversal fixtures and measurement gain/loss/empty-required fixtures pass. The empirical treatment is active on 160 cases. |
| PF5 | Ordered source identities preserved; query and source-content digests attached to every row, anchored to hashed historical input. |
| PF6 | All 192 original reader payloads reproduced byte-for-byte; all stable trace fields reproduced. Link-disabled fusion and repeated fusion also exact on all 192. Only measured latency and tuple/list serialization normalized, documented in `IMPLEMENTATION_NOTE.md`. |
| PF7 | Frozen finite seed sequence with unique emission; original function asserts full permutation on each active real history. No state persists across calls. |
| PF8 | All available 140-record histories replayed, not a shortened ablation. This cannot test longer online feedback or transfer. |
| PF9 | Exact rendered fragments verified; complete cases also checked against sufficient text sets. Availability is not answer correctness; more candidates are not selective completion. Mechanism receives no labels; source scan plus planted forbidden-read fixture passes. |
| PF10 | No reader calls or answer scores. A common-runtime reader comparison is required before a success claim; native reasoning settings must be explicitly verified then. |

Preflight took 8.92 seconds with four workers and one numeric thread each, 9.55 CPU seconds. This short Python-heavy replay did not saturate four cores; no long compute job was left running. The initial preflight stopped on a latency equality check before outputs or label-based analysis; the repair did not change selection.

## Reproduction and review

From the repository root, with the pinned external worktrees available:

```powershell
.venv/Scripts/python.exe -X utf8 experiments/probes/temporal_da_fusion/preflight.py
.venv/Scripts/python.exe -X utf8 experiments/probes/temporal_da_fusion/analyze.py
```

These commands intentionally refuse artifact overwrites. Reproduction requires a fresh output location/checkout with generated artifacts absent; preserve the committed outputs. The draft depends on local pinned worktrees and is not yet a portable package.

The preliminary implementation and preflight are complete. Review this trade before choosing another admission rule, a full compressed DA port, or a fresh reader experiment. Prior Study D/E findings and deployed behavior remain unchanged.
