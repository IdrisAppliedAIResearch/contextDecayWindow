# Study 009 — Pre-Registration (DRAFT v1)
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** LOCKED at registration anchor `37fff74`; Gate 1 contingency invoked before ablation.
**Study 008:** STOPPED AT PRE-RUN GATES (`0a20ef0` / STOP `4a29540`)
**Study 007 accepted treatment:** 12.0/13.0 (best LTM configuration to date)

**Gate-lock note:** Offline digest replay found no fact-aware 4/4 setting
through `d = 50` and `B_digest = 50,000` exact serialized characters. The
pre-registered contingency therefore applies: S+D is dropped and the live
study reduces to the S-versus-L null test. G2 Arm L byte fidelity and G3 Arm S
sanity passed. Human-rater availability remains a hard pre-scoring dependency;
the study waits rather than substituting an agent rater.

---

## Summary

Study 009 corrects a program-level control failure and tests one new component.

**The control failure.** The only clean STM-vs-LTM comparison ever run is Study 004, where STM-only retrieval beat the LTM architecture 11.0 to 7.0. Every control since has been the *previous LTM version* — four studies comparing flavors of LTM against each other. The question the track exists to answer, *does LTM improve recall over the pure STM architecture at all?*, silently left the comparison chain after Study 004. This is the program's recurring surrogate failure class operating at the level of study design: the control became a surrogate for the baseline.

**The structural reason to expect a null result at this scale.** Distilled LTM is a subset of the raw episodic store; STM's K retrieval queries that same store by similarity. At 120 turns nothing has decayed beyond K's reach (Study 002's headline finding: K surfaced middle-domain episodes at turn 115). LTM can therefore only duplicate or displace what K already finds. The 120-turn script is an environment in which LTM's value proposition — compression and coverage when the store outgrows direct search — cannot exist. Study 009 measures this directly instead of assuming it in either direction.

**The new component: a topic-digest context block.** Studies 007–008 established that breadth fails for a reason indifferent to memory tier: an enumeration query embeds near topic centroids, centroids are nearest overviews, and overviews lack the facts. Similarity retrieval — over STM *or* LTM — is structurally mismatched to "list everything." The digest answers the mismatch with structure instead of similarity: a compact, always-on block enumerating each canonical topic with its densest fact spans. It is an **index**, not a retrieval tier: built from the raw store by the existing density machinery, injected every turn within a small fixed character budget, no query classification (and therefore no query-type leakage surface).

Three arms, same seed, blinded human scoring:

| Arm | Architecture |
|---|---|
| **S** | Pure STM (N + K), no LTM tier, no digest — the Study 002 architecture ported to the current runtime and protocol |
| **L** | STM + LTM, the accepted Study 007 treatment configuration, unmodified |
| **S+D** | Pure STM + the topic digest |

The key contrasts: **S vs L** is the null test (the missing baseline); **S vs S+D** isolates the digest. An L+D cell is deliberately omitted — it would double the scoring load to answer a question that only matters if L survives the null test.

---

## Research Questions

**Primary (confirmatory, the null test):** Does the best LTM configuration outperform pure STM on targeted recall at 120 turns? Pre-registered decision rule below; either direction is an informative result.

**Secondary (confirmatory, the component):** Does the topic digest recover breadth (Q11/Q14) without regressing targeted recall?

**Observational:** What does each arm deliver at the probe turns (fact matrices, carried from 008's method); digest composition and cost; context sizes.

---

## Pre-Registered Decision Rules (the null test)

The null test is a comparison, not a bar — either outcome is valuable and neither is a "failure." The consequences are fixed now:

- **If S ≥ L on Q1–Q13:** LTM is formally recorded as **unjustified at 120-turn scale**. The LTM tier is retired from 120-turn studies; its remaining hypothesis (value under decay and store growth) transfers entirely to Study 010's 1,000-turn test. No further 120-turn LTM iteration is permitted without new evidence.
- **If S < L by ≥ 1.0:** the first direct evidence of LTM value at this scale; the retirement is cancelled and the result is analyzed for mechanism (which questions, which delivered facts).
- **If S < L by < 1.0:** reported as within judgment-call variance; treated as the first case (retirement) with the margin disclosed.

**Prediction (P1):** S ≥ L. Refutation consequence: the structural duplication argument above is wrong and must be re-derived before Study 010's design is trusted.

---

## The Topic Digest — specification

The implementation contract. No interpretive latitude is delegated.

1. **Build.** At each dream-cadence point (≈31/61/91/111 — reusing the trigger machinery), rebuild the digest from the raw episodic store: for each canonical topic (current consolidation mapping), select its top **`d` = 2** spans by the existing density score (formation's implementation, imported — one source of truth), subject to the carried eligibility window and 0.95 dedup. Verbatim spans with source-turn provenance; zero inference calls (the extractive assertion applies).
2. **Render.** A `<topic_digest>` block, injected every turn after `<pinned_rules>`, listing each topic name with its spans and source turns. Budget: **`B_digest` = 2,500 characters**, charged at exact serialized cost (the Study 008 Amendment 001 lesson — provenance markup is charged). If topics × `d` exceeds the budget, drop spans round-robin from the largest topics first; never drop a topic entirely (one span per topic is the floor, and a topic whose single span cannot fit is truncated at a word boundary with an ellipsis marker rather than omitted).
3. **Always on.** Injected on every turn in arm S+D, targeted and breadth alike. No query classification. The targeted-recall cost of carrying ~2,500 characters of mostly-irrelevant digest on narrow queries is exactly what Bar 2 measures.
4. **Leakage boundary (carried, binding):** the digest builder may not read `q_facts_key.md` or any rubric artifact; the standing grep + import-graph audit covers it. Density is the ranking; nothing else.
5. **Surrogate audit (per the standing rule):** the check "digest contains a span per topic" certifies presence, not fact-completeness — the same gap Study 007's floor had. Accepted deliberately: the digest's fact-completeness is what the *replay gate* measures against the fact-aware criterion, and the run adjudicates whether delivered facts become recalled facts.

**Interaction with STM (S+D):** the digest is additive; N + K unchanged. Containment dedup applies: a digest span whose source episode is in the STM block is dropped from the digest for that turn (no refill — the digest is a fixed frame, not a budget to fill).

---

## Method

**Arms and execution.** Same fixed seed, same 121-turn script (hash asserted post-decode), same runtime and flags as Studies 007–008, recorded verbatim. Arms byte-identical through the empty-store prefix; divergence begins where architectures first differ. Arm L runs on the **checked-out accepted Study 007 treatment** (separate worktree, full launcher guard set, byte-fidelity check against 007's probe blocks — Bar 0 discipline carried). Arm S is the current runner with the LTM tier and digest disabled *structurally* (the modules absent from the import graph, not flag-off — the Study 004 control lesson, applied to subtraction: build S as its own minimal composition, not as v9-with-features-off). Arm S+D adds only the digest to that composition.

**Evaluation.** Human rater, blinded across three arms (anonymized directories, sealed mapping), locked 14-question rubric, dual scoring on hedge-dependent credit, written rationale per question, **scores for all arms committed before any mechanism log is opened**. 42 scorings; the study waits if the rater is unavailable.

**Gates (offline, pre-run, all fact-aware and rendered-cost-exact):**
- **G1 — Digest replay.** Build the digest offline from the Study 007 preserved raw store; verify it contains ≥1 rubric-critical fact for all four domains within `B_digest`, at exact serialized cost. If density-ranked spans cannot cover 4/4 within 2,500 characters, calibrate `d`/`B_digest` to smallest-sufficient and record; if no setting reaches 4/4, do not run S+D — the digest inherits the formation gap and the study reduces to the null test alone (pre-registered contingency, not an amendment).
- **G2 — Arm L fidelity.** Replay reproduces Study 007's probe blocks to the character.
- **G3 — Arm S sanity.** The S composition's retrieval on the preserved store matches a hand-derived N + K expectation on a fixture; the import graph proves no LTM/digest module loads.

---

## Success Criteria

### Null test — decision rule above (not a bar; either direction is a result)

### Bar 1 — Digest Breadth (the component's direct target)
**Arm S+D: Q11 ≥ 0.5 AND Q14 ≥ 0.5 AND (Q11 + Q14) ≥ 1.5**, with the probe-turn digest shown by the logs to contain rubric-critical facts from all four domains (fact-aware attribution; delivered-but-not-recalled is recorded as such and would be the first true observation of that outcome).

### Bar 2 — Digest Cost (targeted non-regression)
**Arm S+D scores Q1–Q13 ≥ Arm S − 0.5**, Cat 1–3 within 0.5 of Arm S per category. The digest's always-on overhead must not tax narrow queries beyond judgment-call variance.

### Bar 3 — Protocol integrity
Arm L byte-fidelity (Bar 0 discipline); determinism across arms; leakage audit clean; scores-before-logs verified from git order.

VALIDATED = Bars 1–3 pass and the null test yields a clean verdict either way. PARTIAL = mixed. Criteria unchanged post-lock.

---

## Observational Measures

Fact delivery matrix per arm × probe (the 17-fact analysis, carried); digest composition per rebuild and per-turn realized cost; containment drops from the digest; context sizes per arm (S should be the leanest arm the program has run since 002); per-question S-vs-L differences with delivered-fact explanations; determinism evidence.

---

## Limitations

One seed, one script, one rater; n = 1 per arm. The null test is scoped to 120 turns — an S ≥ L result retires LTM *at this scale only*; the scale hypothesis is Study 010's. The digest inherits formation's selection quality (six plants remain unformed; the digest cannot contain what density never surfaces — G1 measures the practical impact). Density remains a surrogate under standing audit. Source weighting remains script-correlated. The digest's scaling with topic count (linear in topics) is untested beyond four; Study 010 will stress it if carried.

---

## Open Decisions Before Lock

1. **`d` and `B_digest`** — no sufficient setting through `d = 50`, 50,000 chars; registered contingency invoked and S+D dropped. [LOCKED]
2. **Digest placement** — after `<pinned_rules>`, before `<recent_context>`; implemented and gate-tested, but not carried to the live run after G1. [LOCKED]
3. **Arm S composition review** — minimal composition accepted; G3 import closure and N + K fixture pass. [LOCKED]
4. **Rater availability for the remaining 28 blinded scorings.** Not yet confirmed; scoring must wait. [LOCKED CONSTRAINT]

---

## Appendix

Study 008 report + postmortem: `experiments/study_008/`. Study 007 preserved store (replay input): `experiments/study_007/runs/study_007_full_001/`. Rubric: `experiments/study_002/rubric_filled.md`; Q14: `experiments/study_004/q14_criteria.md`; plant key (measurement only): `experiments/study_009/q_facts_key.md`. Pre-registration path: `experiments/study_009/pre_registration.md`.
