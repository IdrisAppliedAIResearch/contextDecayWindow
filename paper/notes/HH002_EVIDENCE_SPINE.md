# HH-002 evidence spine

Every value below is computed from the artifact named beside it by
`scripts/hh002_spine.py`. Nothing is typed by hand.

## 1. Provenance

- Upstream harness: `https://github.com/mem0ai/mem0` at `7b3abd06`, tree `evaluation/`, paper `arXiv:2504.19413`
- Vendored prompt digests (SHA-256 of the upstream git blob):

| File | SHA-256 |
|---|---|
| `vendor/llm_judge_accuracy_prompt.txt` | `44fb3d8f7a1f37b2430772cf90518a32172e4056b7a0dec085402763fd179b9f` |
| `vendor/rag_answer_prompt.txt` | `744495b77f2955d437017fd33a0b7156ef41426b7ae8277e5efb92382f234b78` |
| `vendor/rag_system_message.txt` | `0c6b92630ba4c22fd29e718d095abb2d6ffba10c04d00962e94bca4a65b23249` |

- Commitments digest: `f3eb871a1f80120f9e328b29051b1ffdb72b0bfc88f0d1fc0949cee8e5b6a711`
- Model: `gpt-4o-mini-2024-07-18`, embedder `text-embedding-3-small`
- Artifact `commitments.json` SHA-256: `1ca3931c8b97dd7b01b535bce9841f4526189aa028cf48b96d8ecb57e2f8866b`

## 2. Artifacts

| Artifact | Records | SHA-256 |
|---|---:|---|
| `A_FULL/predictions.json` | 1540 | `34da50011c5d962b22db571989fea269e7dcd5cf09e7ed02e35945bda33e0e59` |
| `A_FULL/judged_r1.json` | 1540 | `31933075d01b24e3498c9c4d19f2a51117ef79442024f4402170ea7cb95f64dd` |
| `A_CDW/predictions.json` | 1540 | `c7fb86a2f683bea739d4e1331d979f3ed61a84006f287441ec3a7bb8ced52047` |
| `A_CDW/judged_r1.json` | 1540 | `6f56cebcdd34fdfb33d1c93ec9a89d95f0d7f238d0227716012a84f25a42c3ab` |
| `A_CDW_NOTS/predictions.json` | 1540 | `ae4d763f5ebcd8910a4118202011758538ad0472ceed4a7df67508fd8a426304` |
| `A_CDW_NOTS/judged_r1.json` | 1540 | `cbedd6689e2c6d9b2ec71b41887e82accc4119099243b93912cbbc3257a15f03` |
| `A_RAG/predictions.json` | 1540 | `c1976e1948aaf37d183218119776ceec795899cf771d71abc2fbd6bbf213fcde` |
| `A_RAG/judged_r1.json` | 1540 | `939c8ea830cf7a27f0faa971252a6922ab18933e3df519ba7e7a7e959d344311` |
| `A_RAG/judged_r2.json` | 1540 | `b7fdbcced75548082e5968bfd1852b82c9949919071d65242a382e0ed416bc7d` |
| `A_NONE/predictions.json` | 1540 | `e8a8ea40cbd57ef3c120cd4a5b545b6a1d3a4c001e5291ded0ff01de8d0341ea` |
| `A_NONE/judged_r1.json` | 1540 | `4b12162984f80777343fac198a890683e0c41ac6cbcc958c7a7dce85247756fe` |
| `A_RAG_1000_K1/predictions.json` | 1540 | `cfbf6b663d18081b564a36ab6f03fa5af98bf13aef37cb59cc6462c2b93dd5e7` |
| `A_RAG_1000_K1/judged_r1.json` | 1540 | `44dea0bb4d39451632f0025d7af25ecac7cdbe8ac6ed0762582393979320a81a` |
| `A_RAG_1000_K2/predictions.json` | 1540 | `0894a599a6033673a02ff0578b35f339f6749a0d887c47494e21d4eacdaf7ce9` |
| `A_RAG_1000_K2/judged_r1.json` | 1540 | `c4855a521201c7ab21ff34566378e1f907a5c2236c6b1d1adec1aa0c02bef12f` |
| `A_RAG_500_K4/predictions.json` | 1540 | `13e96075de4ff18686486ff6421d36813571a910e8468836e1a7cce2092b0a7c` |
| `A_RAG_500_K4/judged_r1.json` | 1540 | `7b8ba567843e46d87bd8562ec59bd929f40dee3db323b3801ceece7c2515da61` |

## 3. Scores

Standing follows commitment order, not determinism. The five registered
arms were named in `HH_002_PRE_REGISTRATION.md` §5 before the first
generation call; the sweep was added after `A_RAG` missed its target and
is DESCRIPTIVE.

| Arm | llm_score | f1 | exact_match | n | malformed | Standing |
|---|---:|---:|---:|---:|---:|---|
| `A_FULL` | 72.47% | 0.4127 | 0.0052 | 1540 | 0 | REGISTERED-LIVE |
| `A_CDW` | 79.09% | 0.5108 | 0.0331 | 1540 | 0 | REGISTERED-LIVE |
| `A_CDW_NOTS` | 71.56% | 0.4366 | 0.0279 | 1540 | 0 | REGISTERED-LIVE |
| `A_RAG` | 45.78% | 0.3057 | 0.0403 | 1540 | 0 | REGISTERED-LIVE |
| `A_NONE` | 26.30% | 0.1529 | 0.0071 | 1540 | 0 | REGISTERED-LIVE |
| `A_RAG_1000_K1` | 39.16% | 0.2712 | 0.0253 | 1540 | 0 | DESCRIPTIVE |
| `A_RAG_1000_K2` | 50.65% | 0.3307 | 0.0266 | 1540 | 0 | DESCRIPTIVE |
| `A_RAG_500_K4` | 65.32% | 0.4144 | 0.0325 | 1540 | 0 | DESCRIPTIVE |

## 3a. Scores by question category

LoCoMo category 1 is single-hop, 2 temporal, 3 multi-hop, 4
open-domain. Category 5 is adversarial and is skipped by
`evals.py:22`, so it reaches no number in any row.

| Arm | cat 1 (n=282) | cat 2 (n=321) | cat 3 (n=96) | cat 4 (n=841) |
|---|---|---|---|---|
| `A_FULL` | 67.38% | 49.53% | 55.21% | 84.90% |
| `A_CDW` | 71.63% | 68.54% | 55.21% | 88.35% |
| `A_CDW_NOTS` | 72.34% | 32.09% | 57.29% | 87.99% |
| `A_RAG` | 32.98% | 29.91% | 42.71% | 56.48% |
| `A_NONE` | 21.28% | 11.21% | 38.54% | 32.34% |
| `A_RAG_1000_K1` | 32.27% | 23.99% | 39.58% | 47.21% |
| `A_RAG_1000_K2` | 45.39% | 34.58% | 42.71% | 59.45% |
| `A_RAG_500_K4` | 58.87% | 48.60% | 45.83% | 76.10% |

**Timestamp effect** (`A_CDW` − `A_CDW_NOTS`), by category: cat 1 -0.71, cat 2 +36.45, cat 3 -2.08, cat 4 +0.36.

## 3b. Points above the no-memory floor

The floor is **26.30%** overall and is **not uniform**: cat 1 21.28%, cat 2 11.21%, cat 3 38.54%, cat 4 32.34%.

**Rows measured on this rig only.** Subtracting this floor from a
row quoted from Table 2 is forbidden — see `DO_NOT_WRITE.md` item
35. The floor was measured here, and the strata of the quoted rows
were never published.

| Arm | Raw | Above floor |
|---|---:|---:|
| `A_FULL` | 72.47% | 46.17 |
| `A_CDW` | 79.09% | 52.79 |
| `A_CDW_NOTS` | 71.56% | 45.26 |
| `A_RAG` | 45.78% | 19.48 |
| `A_RAG_1000_K1` | 39.16% | 12.86 |
| `A_RAG_1000_K2` | 50.65% | 24.35 |
| `A_RAG_500_K4` | 65.32% | 39.03 |

## 4. G-CTRL

Judge variance, `A_RAG` scored twice over the same 1540 sealed answers: rates {'1': 45.7792, '2': 45.7143}, spread **0.06 points**, 3 items flipped (0.19%).

Tolerance in force: **±3.00 points** (registered rule: ±3.0 or the measured spread, whichever is wider).

| Arm | Published | Measured | Delta | Within |
|---|---:|---:|---:|:--:|
| `A_FULL` | 72.90% | 72.47% | -0.43 | yes |
| `A_RAG` | 60.53% | 45.78% | -14.75 | NO |

**G-CTRL: FAILED**

## 5. Paired contrasts

`p` is one-sided for the named treatment beating the named control, so a
row whose treatment lost reads `p = 1`. Both directions of the
`A_CDW`/`A_FULL` contrast are printed because the paper quotes the
component-favouring one, and a spine that held only the losing direction
would leave that quotation untraceable.

**Registered vs post-hoc.** `HH_002_PRE_REGISTRATION.md` §7 registers one
directional claim: `A_CDW` > `A_RAG`. Every other row here is post-hoc.
`A_CDW` > `A_FULL` is emphatically post-hoc - §10 prediction 4 predicted
the opposite sign, that the component would land *below* full context.

| Treatment | Control | Endpoint | Delta (pts) | Gains | Losses | Ties | p | Standing |
|---|---|---|---:|---:|---:|---:|---:|---|
| `A_CDW` | `A_RAG` | llm_score | +33.31 | 558 | 45 | 937 | 6.615e-114 | REGISTERED-LIVE |
| `A_CDW` | `A_RAG` | f1 | +24.16 | 433 | 61 | 1046 | 1.949e-70 | REGISTERED-LIVE |
| `A_CDW` | `A_NONE` | llm_score | +52.79 | 852 | 39 | 649 | 1.485e-200 | post-hoc |
| `A_CDW` | `A_NONE` | f1 | +43.96 | 738 | 61 | 741 | 6.973e-149 | post-hoc |
| `A_CDW` | `A_FULL` | llm_score | +6.62 | 210 | 108 | 1222 | 5.593e-09 | post-hoc |
| `A_CDW` | `A_FULL` | f1 | +15.32 | 339 | 103 | 1098 | 9.309e-31 | post-hoc |
| `A_FULL` | `A_CDW` | llm_score | -6.62 | 108 | 210 | 1222 | 1 | post-hoc |
| `A_FULL` | `A_CDW` | f1 | -15.32 | 103 | 339 | 1098 | 1 | post-hoc |
| `A_CDW` | `A_CDW_NOTS` | llm_score | +7.53 | 185 | 69 | 1286 | 1.016e-13 | post-hoc |
| `A_CDW` | `A_CDW_NOTS` | f1 | +9.09 | 218 | 78 | 1244 | 8.717e-17 | post-hoc |
| `A_FULL` | `A_RAG` | llm_score | +26.69 | 507 | 96 | 937 | 1.025e-68 | post-hoc |
| `A_FULL` | `A_RAG` | f1 | +8.83 | 304 | 168 | 1068 | 1.97e-10 | post-hoc |
| `A_CDW` | `A_RAG_500_K4` | llm_score | +13.77 | 276 | 64 | 1200 | 8.358e-33 | post-hoc |
| `A_CDW` | `A_RAG_500_K4` | f1 | +11.23 | 262 | 89 | 1189 | 3.293e-21 | post-hoc |
| `A_RAG_500_K4` | `A_RAG_1000_K2` | llm_score | +14.68 | 318 | 92 | 1130 | 1.582e-30 | post-hoc |
| `A_RAG_500_K4` | `A_RAG_1000_K2` | f1 | +11.30 | 255 | 81 | 1204 | 2.083e-22 | post-hoc |

## 6. Cost per answer

| Arm | Mean prompt tokens | Total prompt tokens | Mean context chars | Units delivered |
|---|---:|---:|---:|---:|
| `A_FULL` | 25,405 | 39,124,100 | 96,241 | 1.00 |
| `A_CDW` | 4,243 | 6,534,218 | 15,978 | 47.62 |
| `A_CDW_NOTS` | 3,696 | 5,692,078 | 15,987 | 60.30 |
| `A_RAG` | 570 | 877,864 | 1,838 | 1.00 |
| `A_NONE` | 84 | 129,027 | 0 | 0.00 |
| `A_RAG_1000_K1` | 1,047 | 1,612,699 | 3,647 | 1.00 |
| `A_RAG_1000_K2` | 2,012 | 3,099,196 | 7,298 | 2.00 |
| `A_RAG_500_K4` | 2,030 | 3,126,431 | 7,352 | 4.00 |

## 7. Rows quoted, not measured

These come from arXiv:2504.19413 Table 2 and were **not** re-run here.
Five of them are the Mem0 authors' reproductions of other people's
systems, not those systems' own reports.

| System | Published | Attribution |
|---|---:|---|
| Mem0 | 66.88% | Mem0 authors, own system |
| Mem0g | 68.44% | Mem0 authors, own system |
| Zep | 65.99% | Mem0 authors' reproduction |
| OpenAI memory | 52.90% | Mem0 authors' reproduction |
| A-MEM | 48.38% | Mem0 authors' reproduction |

## 8. Prohibitions

Grep these before publishing. Each is a sentence this study's design
makes false.

- Do **not** write that this component beat Mem0 *on the published
  table*. Mem0's row was not re-run here; it needs a vendor account
  this study does not have. It is quoted with attribution.
- Do **not** report a paired test against Mem0, Zep or A-MEM. Their
  per-item answers were never published.
- Do **not** call any of this `CONFIRMATORY`. LoCoMo is spent on both
  splits and generation ran against a vendor API, so `AGENTS.md` §4's
  byte-identical rerun rule cannot be met. `REGISTERED-LIVE` at best.
- Do **not** describe the result as a capability claim. LoCoMo fits a
  modern context window; full context wins the published table.
- Do **not** compare any number here to Mem0's current 92.5%. That is
  a different harness, a different answerer model and top_k=200.
- Do **not** claim breadth. The arm carries no coverage objective.
