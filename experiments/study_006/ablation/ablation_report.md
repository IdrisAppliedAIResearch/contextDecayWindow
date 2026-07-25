# Study 006 — 35-Turn Ablation (S6-T-014) and GO/NO-GO (S6-T-015)

**Date:** July 25, 2026
**Pre-registration SHA:** `5def302`
**Amendment in force:** `AMENDMENT_001_selection_scale.md` (C = 50, floor per span)
**Run:** `experiments/study_006/ablation/runs/study_006_ablation_001/`
**Runtime:** llama.cpp `b9294-0f3cb3fc8`, Qwen3.6-27B-UD-Q6_K_XL, ctx 50,000,
single slot, seed 5005, `PYTHONUTF8=1`
**Duration:** 35 turns in 10m 03s

## Checks

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| Speed (single-slot) | > 30 tok/s | 38.7 min / **43.6 mean** / 48.5 max | **PASS** |
| Determinism | prefix replay identical | 10/10 prompts and responses, and 10/10 vs Study 005 (S6-T-003) | **PASS** |
| Raw store permissive | non-content turns stored | 35 of 35 turns stored; 478 of 798 spans ineligible, all source episodes retained | **PASS** |
| Segmentation | spans with round-trip offsets | 798 spans; 100% offset round-trip | **PASS** |
| Eligibility | rejections logged with reasons | 478 logged: 313 no-entity-or-numeric, 163 below-minimum, 2 above-maximum | **PASS** |
| First dream pass | fires at ~31 | fired at **turn 31**, transition event | **PASS** |
| Records written | ≥1, offset-verbatim, provenance resolves | **50** records, 0 offset failures, 0 provenance failures | **PASS** |
| Extractive assertion | passes; zero inference calls | **inference_calls = 0** | **PASS** |
| Civil plant formed | civil fact present after event 31 | **all 5 civil plant rows present** | **PASS** |
| Non-content in LTM | zero | **0** (50 content, 0 markers) | **PASS** |
| Read path | ≥1 distilled span in post-31 context with provenance | **13 distilled spans** retrieved across turns 32–35, each carrying `distilled_id`, `dream_event`, `source_episode_ids`, `source_turns` | **PASS** |
| Purity | no cross-domain merge | topic_2 = 30/30 civil; topic_3 = 5/5 art | **PASS** |
| Context ceiling | peak well under 80% | peak **10,383** of 50,000 = **20.77%** | **PASS** |

**All applicable checks pass.**

## Dream event detail

| Field | Value |
|---|---|
| Turn / type | 31 / transition |
| Segmenter | `spacy:en_core_web_sm:3.8.0:sentencizer` |
| Extractor | `spacy:en_core_web_sm:3.8.0:ner` |
| Episodes evaluated | 30 |
| Spans evaluated | 798 |
| Spans eligible | 320 |
| Survivors after dedup | 319 (1 collapsed) |
| Records written | 50 (cap) |
| Marker written | no |
| Coverage floor in force | 0.15 |
| Inference calls | **0** |

The span counts reproduce the replay exactly — 798 spans, 320 eligible, 319
survivors at the turn-31 civil event — which is independent confirmation that the
replay harness modelled the live pipeline faithfully.

## Formation

All five civil plant rows are present in the distilled store:

| Fact | Present |
|---|---|
| civil_project (`Halcyon Crossing`) | yes |
| civil_span (`main span`; `847`) | yes |
| civil_engineer (`Dr. Anara Bekova`) | yes |
| civil_steel (`S460ML`) | yes |
| civil_load (`92.4`; `metric tons per axle`) | yes |

This exceeds what replay predicted. Replay placed `civil_load` at rank 33 and
`civil_engineer` at 42; at C = 50 both are inside the cap, so the civil domain
forms on all five rows rather than the one Bar 1 requires.

## Composition and compression

Selected records: **40 assistant / 10 user**. Distilled text is **5,823 chars
against 125,321 raw = 4.65%**.

The source split is worth recording plainly: the density policy still selects
mostly assistant spans, and terse specification rows (`Tensile Strength: 620–780
MPa`, `Yield Strength: ≥ 460 MPa`) remain the highest-scoring items. The 1.5×
user weight is a tiebreaker, not a dominance rule, and behaves as pre-registered.
What changed with Amendment 001 is that the cap is now wide enough for the user
facts to be selected *as well as* the dense assistant rows, rather than instead of
them — `The total main span is 847 meters.` ranks 6th and is written.

## Not exercised at 35 turns

Turn-111 flush, the probe guard, the breadth probes, and the sparse-topic marker
path are not reachable in 35 turns. These were covered by the adversarial fixture
and the retrospective replay, as the sprint plan anticipates.

---

# S6-T-015 — GO/NO-GO

```
DECISION: GO — all applicable checks passed; adversarial fixture and 4/4
retrospective replay passed pre-ablation. Control + full v6 run authorized.
```

**Conditions carried into S6_007, recorded before the runs:**

1. `renaissance_art` and `monetary_policy` had the least replay margin (ranks 29
   and 36 against C = 50). Neither was exercised by this ablation, which reaches
   only the civil event.
2. `art_pigment`, `art_patron_role`, `marine_photophores` and `marine_feeding`
   remain unselected at any defensible cap. Q5 and Q8 depend on them, so the
   **Bar 3 regression risk recorded at lock stands and is expected to materialise**.
3. The distilled store will be roughly 17× larger than Study 005's. Retrieval and
   arbitration are unmodified and untested at that size; their behaviour is an
   observational measure in S6_008, not a tuned parameter.

**Authorized by:** Muzaffer Ozen, Idris Applied AI Research — 2026-07-25
