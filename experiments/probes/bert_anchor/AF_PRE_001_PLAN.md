# AF-PRE-001 — zero-shot anchor identification probe (v2)

**Status:** PLAN ONLY, revised v2. Plan-only commits precede any implementation, label, or fixture-score file. **Supersedes** v1 (`79eb8c1d`) after external critique (`AF_PRE_001_REVIEW_001.md`); nothing had run under v1.
**Date:** September 20, 2026. User authorization: new anchor-finding arc; zero-shot probe first. Fully offline: no reader or judge calls, no training, no change to frozen retrieval, the .48 threshold, `episodic` 0.3.0, or any sealed artifact. The manipulated input is *which anchor gets protected*.

## 1. Hypothesis and scope

A frozen BERT-class **cross-encoder**, untrained, localizes a question's event anchor where purely lexical and bi-encoder instruments cannot — measured on queries where the entity name alone does not solve the task. Inherited gap: raw cosine >=.48 drops 17 of 128 Study E anchor exchanges (complete evidence 111/128; 128/128 with script anchors, `temporal_da_fusion/RELEVANCE_REPORT.md`).

**Anchor:** the exchange carrying the named event (E generator's unique meeting-name carrier, `study_E/corpus.py`). Admission role only — no horizon/cutoff prediction (unvalidated per `reader_anchor/REPORT.md`; one variable at a time). Discriminative encoders are the same instrument class as the carried Qwen3-Embedding; zero generative calls preserved; the paused LLM planner is untouched. Cross-encoder model download authorized by user on 2026-09-20 and recorded in `AF_PRE_001_REVIEW_001.md`.

**Partition ruling (user, 2026-09-20):** the repo carries contradictory dev/holdout regimes (`nf004_measurement.py:23-24` vs the AV-arc handoff). This probe recognizes **no confirmation-grade LoCoMo surface**. All LoCoMo items come from one seeded random stratified pool across all conversations and every resulting number is characterization, registered as such.

## 2. Arms

Candidates: full complete exchanges (the product protection unit, `episodic/_timeline.py`). Per-exchange score pooled from <=512-token sentence windows; window counts and positions logged. Pooling policy is provisional: if Part 1 measurement shows >90% of exchanges on both surfaces fit one window, max-pool language is deleted and single-window scoring stated before lock (v1's borrowed TC-009 prior applies to LongMem episodes, not these surfaces). Deterministic tie-break: lowest source turn. Predicted anchor absent or past a supplied horizon: fall back to no-anchor (`PURE`) for that question, counted as a miss.

| arm | anchor source | role |
|---|---|---|
| `PURE` | none | sealed floor (111/128 on original E) |
| `ORACLE` | script gold | ceiling (128/128); fidelity replay only |
| `LEX` | exact quoted-name match | trivial on original E by generator construction |
| `BM25` | bag-of-words over exchange text | standard lexical floor |
| `QWEN-BI` | carried Qwen3-Embedding cosine, max over sentence windows, cached vectors | deployed-instrument comparison at zero new download |
| `CE` | `cross-encoder/ms-marco-MiniLM-L-6-v2`, pinned revision + SHA-256, max-pool | the candidate |

NLI zero-shot deferred to post-hoc diagnostic only (relation mismatch, template freedom; review item 8). `ORACLE` equals gold-union by definition and is not re-run.

## 3. Surfaces

**E-original (fidelity, not disposition).** 128 before-questions, sealed. `LEX`=gold=128/128 by construction (`corpus.py:22` uniqueness enforcement; event sentence first). Used only for the Part 1 replay and to report where `CE` could not lose. Additionally Part 1 characterizes the 17 dropped anchors' stratum composition from sealed artifacts (expected: proposal/irrelevant/future only) with the explicit caveat that the gap may be a generator-RNG artifact rather than a difficulty axis — if so, recorded before any interpretation of recovery counts.

**E-paraphrase (primary disposition surface).** All 128 queries rewritten by one frozen deterministic template that removes the quoted meeting name (e.g., *what was the delivery location just before the review for this item?*); gold anchors mechanically unchanged. The generator guarantees name uniqueness, so stripping the name leaves `LEX` without its carrier: paraphrase E is where interaction scoring has room to beat lexical matching. Rewrites committed before any model score exists; the template, not an annotator, produces them; no gold is touched.

**LoCoMo pool (naturalness, characterization).** n=120 primary questions, seeded stratified draw across conversations and categories 1-4 (category 5 excluded: no evidence annotations, undefined single-anchor gold). Gold = the pair containing the annotated evidence turn that introduces the question's event; pre-registered tie rule (earliest such pair) and multi-evidence rule (any annotated-introducing pair counts). **Two independent annotation passes** on the full sample, each blind to arm outputs and to the other pass and to `LEX`; Cohen's kappa registered. **kappa < .70 ⇒ the dev surface is an instrument failure (§9.2); no dev-side claim of any kind is made.** No LEX-in-the-loop review. Label files commit after prediction seal.

## 4. Registered dispositions (fixed before any run; both reachable in each direction; PF4 discharged on the calibration slice, not on scored data)

**Calibration slice:** n=60 questions drawn from the same pools, double-annotated and committed **before** predictions; used solely to demonstrate each bar's reachable range. Excluded from scoring.

- **`WORKS`** — on E-paraphrase, `CE` top-1 anchor recovery exceeds `max(LEX, BM25, QWEN-BI)` top-1 by a paired exact-McNemar p<.05 **and** by registered net margin >= +10 items of 128. **Binding successor, registered here:** before any fine-tuning study, a paired native-reader pilot on E-paraphrase items discordant between `PURE` and the `CE`-anchored selection plus equal matched controls (~40 items x 2 contexts; local reader, no paid API), bar: net >= +5 correct, p<.05 exact sign test. Until that pilot runs and passes, `WORKS` may be described only as "anchor localization demonstrated offline"; the word "adequate" (to product, to the reader, to anything) is out of bounds.
- **`SIGNAL`** — on E-paraphrase, `CE` beats every lexical/bi-encoder arm in net discordant pairs (any margin, direction consistent across both E-paraphrase and the LoCoMo pool), with kappa >= .70 on the dev sample. Reading: a registered fine-tuning successor is justified with measured priors; no product word permitted.
- **`NO_SIGNAL`** — otherwise. Reading: the zero-training instrument is not demonstrated — an instrument statement, not a verdict on anchor-finding (§9.2); the planner question may be reopened with this measurement attached.

Every reported quantity carries its interval (binomial or bootstrap, chosen now: 95% Wilson for proportions, exact sign/McNemar for paired counts). Structural floor displayed wherever monotone counts appear: union selection cannot lose admitted records; availability is a derived identity of anchor recovery, never a second measurement.

## 5. Known landmines, carried

TC-004/TC-009/DMR-004 mechanical-signal priors (honest prior: `CE` fails); entity-mention confounding neutralized by the paraphrase surface, not by argument; spent-corpus ceiling on all LoCoMo readings; the 17's possible RNG composition (Part 1a); annotation noise quantified by kappa rather than assumed away; new-model environment additions limited to one cross-encoder family, pinned by SHA.

## 6. Preflight

**Part 1 — Exploration (locks nothing; findings amend before lock, recorded).**
(a) Replay `PURE`/`ORACLE` on E-original: reproduce sealed 111/128 and 128/128 by identity and payload digest; report the 17's stratum composition.
(b) Instrument identity fixtures, expected outcomes committed **before** instrument code: per arm, one planted positive (carrier must rank first) and one adversarial hard negative naming the item and a location but not the event (carrier must outrank it). An arm that sweeps a fixture it cannot fail is an instrument failure, not a pass.
(c) Token/window distribution per surface; pooling clause kept or deleted on measurement.
(d) Paraphrase template applied; `LEX` zero-hit on paraphrases verified (if `LEX` still solves paraphrases, the surface is void and the plan returns before running).

**Part 2 — Checklist.** **PF1** inputs hash-counted: sealed E artifacts and relevance artifacts, `locomo10.json`, pinned model SHA-256, vector-cache manifest. **PF2** identity = the Part 1a replay (proves the inherited gap and the anchor's role) plus per-arm planted pass/fail fixtures. **PF3** commit order: plan v2 -> code + paraphrase template + fixtures (expected outcomes first) -> Part 1 gate results -> calibration labels -> predictions sealed -> dev gold labels -> results; planted gate-failure fixture blocks scoring. **PF4** bars' reachability demonstrated on the calibration slice (each arm's range shown, each bar's non-stopping branch observed to exist) before lock. **PF5** keys: exchange-content and question-text hashes. **PF6** Part 1a against sealed digests. **PF7** no feedback; single deterministic pass; repeat-shard bit-identity recorded. **PF8** n=128 paraphrase + n=120 pool detect gross localization failure at the registered margins; they cannot resolve small top-k differences or any reader effect — the pilot owns the latter. **PF9** surrogate audit: top-1 recovery passes while the exchange merely co-mentions the date without the event; gold is the generator carrier and the annotation-introducing pair, nothing more; residual accepted, and the binding pilot exists precisely because this residual is real. **PF10** availability is not a verdict; the reader pilot in §4 is the registered live evaluation, and it is binding on WORKS.

**Scoring boundary:** selector/encoder code never reads gold labels, annotations, or the calibration file; labels enter measurement scripts after prediction seal.
