# AF-PRE-001 — zero-shot anchor identification probe

**Status:** PLAN ONLY. Plan-only commit precedes any implementation file.
**Date:** September 20, 2026. User authorization: new anchor-finding arc; this probe first, zero training, zero reader calls.
**Scope:** fully offline. No reader or judge calls. No model training. No change to frozen retrieval, the .48 threshold, `episodic` 0.3.0, or any sealed artifact. The only manipulated input is *which anchor gets protected*.

## 1. Hypothesis

A frozen BERT-class cross-encoder, untrained, can identify a question's event anchor well enough to recover evidence that the raw-cosine >=.48 boundary alone drops. The measured gap is inherited: pure threshold loses 17 of 128 Study E before-question anchors (111/128 complete evidence); with script-supplied anchors, 128/128 (`experiments/probes/temporal_da_fusion/RELEVANCE_REPORT.md`).

**Anchor definition (inherited, not restated):** the exchange carrying the named event — the E generator's `anchor` metadata (`experiments/study_E/corpus.py`: the unique meeting-bearing carrier). This is the admission role proven in the relevance timeline. Horizon/cutoff prediction is **out of scope**: the reader-anchor probe found boundary selection unvalidated, and one variable moves at a time.

The arc's premise is instrument class, not cost: a discriminative encoder scored by a frozen model is the same category as the carried Qwen3-Embedding-0.6B. The zero-generative-calls constraint is untouched; the paused one-call LLM planner is not reopened by this probe.

## 2. Arms

All arms select from the same candidate pool: full complete exchanges (the product unit; `episodic` `_timeline.py` protects at exchange granularity). Anchor score per exchange is pooled from <=512-token sentence windows; window count, positions, and pooled score are logged per exchange, and pooling is a registered choice, not silent truncation (TC-009's max-pooling finding is carried as prior).

| arm | anchor source |
|---|---|
| `PURE` | no anchor protection — sealed baseline, 111/128 |
| `ORACLE` | script gold anchor — ceiling, 128/128 |
| `LEX` | lexical: question's quoted name matched in exchange text |
| `CE` | `cross-encoder/ms-marco-MiniLM-L-6-v2` (pinned revision + SHA-256), question vs window, max-pool |
| `NLI` | DeBERTa-v3-base MNLI+ANLI zero-shot entailment against a frozen template ("the named event took place"), entailment probability |

Model choice and template are frozen in the commit that passes gates, before any dev prediction; no post-hoc model swap. Gold-anchor-union is by definition identical to `ORACLE` and not re-run.

## 3. Measurement surfaces

**E (primary).** All 128 before-questions from sealed Study E, gold anchors mechanically derivable from generator metadata — no labeling. Report: top-1/top-3 exchange recovery, gold-anchor rank distribution, **anchor recovery** (of the 17 anchors `PURE` drops, how many each arm admits) and **availability** vs the sealed 111/128 and 128/128 counts.

**LoCoMo dev (naturalness).** ~100 questions from the 848 development split only (conversations other than conv-41/42/47/48, which stay untouched). Gold anchor labeled from evidence-annotation date+speaker plus manual review, then a second-pass review of all disagreements with `LEX`. Gold labels are measurement-only, sealed in a separate commit **after** predictions are sealed. Every LoCoMo number is characterization — the corpus is spent — so on this surface the primary quantity is **arm disagreement and recovery-vs-lexical**, not absolute availability.

## 4. Registered dispositions (both bars fixed before any run, per §9.3)

- **`WORKS`:** on E, predicted-anchor availability equals `ORACLE` 128/128 with zero losses versus `PURE`; on dev, anchor top-1 >= .75 and strictly above `LEX`. Reading: a zero-training anchor source is adequate to prototype product-side; proceed to a registered fine-tuning study.
- **`SIGNAL`:** on E, availability recovers >= half the `PURE`->`ORACLE` gap with zero required-evidence losses; on dev, top-1 above `LEX` and above chance. Reading: a training arc is justified with a measured prior; `CE` vs `LEX` discordance is its design input.
- **`NO_SIGNAL`:** below both. Reading: the zero-training *instrument* is not demonstrated — this is an instrument statement, not a verdict on anchor-finding (§9.2); the planner question may be reopened with this measurement attached.

`ORACLE`-equality and gap counts are availability, never a reader verdict (PF10).

## 5. Known landmines, carried in writing

- **TC-004/TC-009:** embedding localization and max-pool span scores failed before — the honest prior for `CE` is failure. This probe measures whether an interaction-scoring encoder differs from the mechanical signals that failed at J=.320 (DMR-004) and AP 21/31 (TC-004).
- **Entity-mention confounding:** most E exchanges name the subject. High `LEX` scores on E prove nothing; the informative quantity is where `CE` and `LEX` disagree.
- **512-token windows:** median exchange ~2.5k chars exceeds the encoder limit; pooling policy is logged and reported per arm.
- **Spent corpus:** no LoCoMo result here can be confirmatory.

## 6. Preflight

**Part 1 — Exploration (deliverables before anything locks).**
(a) Replay `PURE` and `ORACLE` on the 128 E before-questions; reproduce the sealed 111/128 and 128/128 counts by identity and payload digest. (b) Run `CE` and `NLI` on a committed 10-exchange fixture; record raw score distributions, window counts, tie behavior, and degenerate cases (constant scores, empty windows, name-free exchanges). Findings may amend this plan before its lock commit — amendments recorded, not silent.

**Part 2 — Checklist.**
**PF1** Inputs hash-counted: Study E corpus and sealed relevance artifacts (`RELEVANCE_REPORT.md`, `relevance_artifacts/`), `locomo10.json` dev subset, model checkpoints pinned by revision and SHA-256. **PF2** `ORACLE` is verified to *be* the protection that closes 111->128 (the replay in Part 1a); `LEX` matcher tested against the quoted-name grammar on E and a negative fixture. **PF3** commit order enforced: plan -> code+models -> gate fixtures -> predictions sealed -> dev gold labels -> results; planted gate-failure fixture blocks scoring. **PF4** both disposition bars shown reachable pre-lock: `ORACLE` (achieves `WORKS` on E by construction) and `PURE` (achieves the floor), so every gate's non-stopping branch demonstrably exists. **PF5** comparison keys: exchange content hashes and question-text hashes, never ids or paths. **PF6** reproduction: Part 1a against sealed digests. **PF7** single deterministic pass per model, no feedback; repeat-shard bit-identity recorded. **PF8** E n=128 plus dev n~100 can detect gross anchor failure; it cannot resolve small top-k differences or any reader effect — stated, not assumed away. **PF9** surrogate audit: recovery-vs-`PURE` can rise while anchor quality is false (an exchange containing the gold date but not the event); gold is the generator's named-event carrier, nothing more. Residual accepted and recorded. **PF10** availability is not a verdict; any live reader confirmation of an anchor source is a separate registered study with the reader.

**Scoring boundary:** mechanism code (selectors, encoders) never reads gold labels or annotations; labels enter only measurement scripts, after prediction seal.
