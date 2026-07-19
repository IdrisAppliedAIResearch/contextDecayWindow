# Study 003 Figure Provenance

These publication figures are generated assets. Do not hand-edit the SVG files.

From the repository root, regenerate and verify them with:

```powershell
.\.venv\Scripts\python.exe scripts\generate_study_003_figures.py
.\.venv\Scripts\python.exe scripts\generate_study_003_figures.py --check
```

The generator uses only the Python standard library and writes accessible,
vector SVGs. Quantitative marks are derived from the accepted
`study_003_full_002` artifacts under `experiments/study_003/runs/run_001/`.

| Figure | Primary source artifacts | Scope and caution |
|---|---|---|
| `study-overview.svg` | `condition_c/rubric/scores.md`, `condition_c/metrics/memory_store.csv`, `ltm_analysis/promotion_events.csv` | Graphical overview of the scripted design and reported outcomes; the final topic count is explicitly labeled as an over-merge. |
| `memory-architecture.svg` | `pre_registration.md`, Amendments 002–004, and the accepted implementation | System schematic, not an empirical result. LTM is shown as write-only and promoted episodes remain in STM. |
| `confirmatory-outcomes.svg` | `condition_c/rubric/scores.md`, `condition_c/metrics/memory_store.csv` | Direct rubric and locked success-bar comparison; no uncertainty estimate is implied. |
| `topic-context-trajectories.svg` | `condition_c/metrics/memory_store.csv`, `model_performance.csv`, `consolidation_events.csv` | Per-turn descriptive trajectories. “Estimated tokens” is the study's constructed-context estimate, not tokenizer-ground-truth prompt usage. |
| `ltm-promotion-outcomes.svg` | `ltm_analysis/promotion_events.csv`, `episode_scores.csv` | Descriptive counts from one accepted run. Marine biology is marked structurally unevaluated rather than assigned a zero rate. |
| `filter-score-distributions.svg` | `ltm_analysis/episode_scores.csv` | All 90 evaluated rows. Boxes use inclusive quartiles; whiskers show observed minima and maxima, not 1.5-IQR fences. Promotion routes are alternatives, and the empty-LTM all-or-nothing bypass was suspended. |

Color is redundant with direct labels, symbols, and line styles. Each SVG also
contains a machine-readable title and description for screen readers.
