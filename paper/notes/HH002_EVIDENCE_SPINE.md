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

## 3. Scores

| Arm | llm_score | f1 | exact_match | n | malformed judgements |
|---|---:|---:|---:|---:|---:|
| `A_FULL` | 72.47% | 0.4127 | 0.0052 | 1540 | 0 |
| `A_CDW` | 79.09% | 0.5108 | 0.0331 | 1540 | 0 |
| `A_CDW_NOTS` | 71.56% | 0.4366 | 0.0279 | 1540 | 0 |
| `A_RAG` | 45.78% | 0.3057 | 0.0403 | 1540 | 0 |
| `A_NONE` | 26.30% | 0.1529 | 0.0071 | 1540 | 0 |

## 4. G-CTRL

Judge variance, `A_RAG` scored twice over the same 1540 sealed answers: rates {'1': 45.7792, '2': 45.7143}, spread **0.06 points**, 3 items flipped (0.19%).

Tolerance in force: **±3.00 points** (registered rule: ±3.0 or the measured spread, whichever is wider).

| Arm | Published | Measured | Delta | Within |
|---|---:|---:|---:|:--:|
| `A_FULL` | 72.90% | 72.47% | -0.43 | yes |
| `A_RAG` | 60.53% | 45.78% | -14.75 | NO |

**G-CTRL: FAILED**

## 5. Paired contrasts

| Treatment | Control | Endpoint | Delta (pts) | Gains | Losses | Ties | p |
|---|---|---|---:|---:|---:|---:|---:|
| `A_CDW` | `A_RAG` | llm_score | +33.31 | 558 | 45 | 937 | 6.615e-114 |
| `A_CDW` | `A_RAG` | f1 | +24.16 | 433 | 61 | 1046 | 1.949e-70 |
| `A_CDW` | `A_NONE` | llm_score | +52.79 | 852 | 39 | 649 | 1.485e-200 |
| `A_CDW` | `A_NONE` | f1 | +43.96 | 738 | 61 | 741 | 6.973e-149 |
| `A_FULL` | `A_CDW` | llm_score | -6.62 | 108 | 210 | 1222 | 1 |
| `A_FULL` | `A_CDW` | f1 | -15.32 | 103 | 339 | 1098 | 1 |
| `A_CDW` | `A_CDW_NOTS` | llm_score | +7.53 | 185 | 69 | 1286 | 1.016e-13 |
| `A_CDW` | `A_CDW_NOTS` | f1 | +9.09 | 218 | 78 | 1244 | 8.717e-17 |
| `A_FULL` | `A_RAG` | llm_score | +26.69 | 507 | 96 | 937 | 1.025e-68 |
| `A_FULL` | `A_RAG` | f1 | +8.83 | 304 | 168 | 1068 | 1.97e-10 |

## 6. Cost per answer

| Arm | Mean prompt tokens | Total prompt tokens | Mean context chars | Units delivered |
|---|---:|---:|---:|---:|
| `A_FULL` | 25,405.3 | 39,124,100 | 96,241.4 | 1.00 |
| `A_CDW` | 4,243.0 | 6,534,218 | 15,978.0 | 47.62 |
| `A_CDW_NOTS` | 3,696.2 | 5,692,078 | 15,986.9 | 60.30 |
| `A_RAG` | 570.0 | 877,864 | 1,838.2 | 1.00 |
| `A_NONE` | 83.8 | 129,027 | 0.0 | 0.00 |

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
