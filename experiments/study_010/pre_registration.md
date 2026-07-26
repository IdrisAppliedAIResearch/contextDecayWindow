# Study 010 — Pre-Registration (DRAFT v1)
## contextDecayWindow
**Idris Applied AI Research**
**Date:** July 2026
**Status:** STOPPED AT G2 UNDER AMENDMENTS 001-002
**Deferred since:** Study 003 ("stress-test the study where retrieval is active"), re-deferred at 004, 005, 008.

**Pre-lock review:** the original STOP is superseded by author-authorized
`amendments/AMENDMENT_001_executable_endurance_protocol.md`. Study 009 now
supplies a decisive verdict, digest carry is false, and architecture-aware
parity replaces the impossible byte-identical prefix rule.

---

## Summary

Study 010 is the endurance study: **1,000 turns**, the scale at which LTM's actual hypothesis lives. Every prior study ran at 120 turns — a scale where the raw store never outgrows K retrieval's reach and recency never fully decays, so the LTM tier can only duplicate or displace what STM already finds. Study 009 measures that null directly. Study 010 changes the environment instead of the architecture: at ~1,000 turns the raw store is ~8× larger, similarity search runs over a far bigger and more confusable candidate set, and early content is genuinely beyond any recency window. **This is the first environment in which STM-vs-LTM is a fair fight**, and the study is designed so that either verdict — LTM earns its place, or LTM is cut from the architecture — is a strong, publishable finding.

Two arms, same seed, same 1,000-turn script:

| Arm | Architecture |
|---|---|
| **S** | Pure STM (N + K) — Study 009's Arm S composition |
| **L** | STM + LTM — the accepted Study 007 treatment configuration |

Both arms carry the topic digest **iff** Study 009 validated it (Branch 1). This is deliberately a two-arm study, not a factorial: 008's lesson is that cells are expensive and the scoring load at 1,000-turn scale is already the design's binding cost.

**No new component.** Study 010 is a scale test of the assembled architecture — the study type the program has always kept separate from construction studies. The one new *artifact* is the 1,000-turn script, which is the long pole and is specified below as a first-class deliverable with its own integrity requirements.

---

## Pre-Registered Branches (resolved by Study 009 before lock)

**Branch 1 — digest carry.** If Study 009 Bars 1–2 pass (digest recovers breadth without taxing targeted recall), **both arms carry the digest** — it is then settled infrastructure, and carrying it in both arms keeps the S-vs-L contrast clean. If either bar failed, neither arm carries it, and breadth at 1,000 turns is measured as-is (expected weak in both arms; recorded, not bar-gated).

**Branch 2 — LTM configuration.** Arm L fields the accepted Study 007 treatment configuration regardless of the 009 null-test verdict (a 120-turn retirement explicitly does not bind at this scale — that transfer is the retirement rule's own text). If 009 produced an S < L surprise, its mechanism analysis may motivate an amendment to Arm L's config **before lock only**, recorded as a decision.

No other element of this document depends on Study 009.

---

## Research Questions

**Primary (confirmatory):** At 1,000 turns, does the LTM tier improve recall over pure STM — on early-planted facts beyond recency, on mid-conversation plants under a large store, and on breadth?

**Primary (confirmatory, degradation):** How does each arm's recall degrade with plant age and store size? Interim probes give each arm a degradation curve, not just an endpoint.

**Observational:** K-retrieval precision as the store grows (the confusability hypothesis); context sizes and wall-clock; consolidation behavior at ~25 topics; digest scaling (if carried); dream-cadence behavior over ~30 events.

---

## The 1,000-Turn Script (new artifact — first-class deliverable)

The 120-turn script cannot be stretched; a new script is authored under these binding requirements:

1. **Structure:** ~1,000 turns, **12 domains** of ~80 turns each in sequence (plus transitions), preserving the established pattern (distinct technical domains, scripted user turns, deterministic).
2. **Plants:** per domain, planted facts at early/middle/late positions within the domain's block — same plant grammar as the 120-turn script (compact, entity-and-number-dense, user-authored*). Full plant key authored with the script (`q_facts_key_1000.md`), before any run, sealed from the retrieval path by the standing leakage audit. (*The source-weighting script-correlation limitation is carried and now explicitly acknowledged as a *design choice* of the script family, documented, unresolved.)
3. **Probes:** a terminal probe block modeled on Q1–Q14 (targeted per era + two breadth probes), **plus interim probe checkpoints at ≈ turns 250, 500, 750** — three questions each (one early-era targeted, one recent targeted, one breadth) — giving the degradation curves. Interim probes are excluded from dreaming/promotion emission (the carried probe-guard discipline, extended).
4. **Rubric:** authored with the script, locked before lock of this pre-registration, criteria per question in the established 0/0.5/1.0 grammar. This is the study's largest authoring task and its quality ceiling.
5. **Integrity:** script SHA-256 asserted post-decode at startup (carried); the script is committed and hash-locked **before** any calibration or replay activity so that no gate can tune the script.

**Honest note on comparability:** a new script breaks the 002–009 comparison chain by necessity. Study 010's comparisons are internal (S vs L, same script, same seed) and longitudinal (degradation curves). No cross-study score comparison to the 120-turn chain will be made.

---

## Method

**Runtime.** Carried: UD-Q6_K_XL, single slot, no speculative decoding, fixed seed, 2,048 response budget, exact-serialized-cost accounting throughout. **`--ctx-size` re-derived for this study** per the stage-interface contract: peak context is projected from 009's per-turn measurements scaled to 12-topic digests and ~1,000-episode stores, with the ceiling set to ≥ 2× projected peak and the 80% monitor carried. KV cache q8_0, identical across arms.

**Feasibility (pre-registered projections, verified at gate):** ~121 turns ran ≈ 45 minutes; 1,000 turns projects to **6–8 hours per arm** plus dream passes (~30 events) and ~1,000 embedding calls. Both arms run under the carried monitoring rules with one addition: a **checkpoint/resume protocol** — full state snapshot (stores, logs, RNG state) every 100 turns, so a crash resumes from the last checkpoint rather than discarding a 7-hour run; resume correctness is a gated pre-run test, and any resume event is logged as a protocol note in the report.

**Scale-shift gates (offline, pre-run):**
- **G1 — Retrieval-at-scale replay.** Synthesize a ~1,000-episode store (from the script's own turns, embedded); verify K retrieval's behavior: latency, and precision on planted-fact queries vs the 120-turn store (the confusability measurement, taken before the run so the live result has a prediction to meet).
- **G2 — Consolidation-at-scale.** ~12 canonical domains against thresholds tuned at 4: replay topic assignment/consolidation over the script's embedded turns; the purity instrumentation must show the domain structure recoverable (no mass cross-domain merging, no fragmentation explosion). If thresholds fail at 12 domains, recalibrate **before lock** with a decision record — this is exactly the class of silent scale break the gate exists to catch.
- **G3 — Digest-at-scale** (if Branch 1 carries it): 12 topics × `d` spans within a re-derived `B_digest` (the 009 value is 4-topic-sized; per the stage-interface contract it is re-derived, not assumed).
- **G4 — Checkpoint/resume correctness:** kill and resume a seeded prefix run at a checkpoint; the resumed run must be turn-identical to an unkilled reference.
- **G5 — Wall-clock rehearsal:** a 200-turn timed run per arm validating the 6–8 hour projection and the monitoring protocol.

**Evaluation.** Blinded agent rater across two arms on the new locked rubric
(terminal + interim probes; 46 arm-question scores), dual scoring carried,
**scores before any mechanism log** (git-verified). Fact-delivery matrices per
probe checkpoint per arm, carried method. See Amendment 001.

---

## Success Criteria

This is a scale test with a decision, not a construction study with a component bar.

### Bar 1 — The verdict (pre-registered decision rule)
Evaluated on the terminal probe block, with the interim curves as supporting evidence:
- **L > S by ≥ 1.5 overall, or L > S by ≥ 1.0 on early-era targeted questions specifically:** LTM demonstrates value at scale. It is retained in the architecture, and the report states the mechanism from the fact matrices (which delivered facts L had that S lacked).
- **S ≥ L:** LTM is **cut from the architecture** — the 120-turn retirement (if 009 issued it) extends to full retirement. The pipeline's long-term memory story becomes: permissive raw store + K retrieval (+ digest if carried), with dreaming retained only as the digest's index builder (or retired too, if the digest was not carried). This consequence is accepted now, in writing, before the run.
- **Intermediate (L > S by < 1.5 overall and < 1.0 early-era):** reported as inconclusive-lean-null; LTM is suspended (not fielded in future studies) pending a stronger design, which must be justified against this study's fact matrices.

### Bar 2 — Endurance integrity (both arms)
**Both arms complete 1,000 turns** (checkpoint-resume permitted, logged); determinism spot-checks pass; context stays under the ceiling monitor; formation/store integrity checks (offset-verbatim, zero non-content, zero inference calls in dreaming where applicable) hold at every dream event. A crash-loop that checkpointing cannot recover is a stop-and-diagnose, not a scored result.

### Bar 3 — Degradation measurement delivered
The interim probes yield complete per-arm degradation curves (all checkpoints scored). This is a bar because the curves are half the study's value: an endpoint tie with divergent curves is a finding.

VALIDATED = Bars 2–3 clean and Bar 1 yields its verdict either way. The Bar 1 verdict itself is never a "failure" in either direction.

---

## Observational Measures

Per-checkpoint fact matrices; K precision/latency vs store size against G1's prediction; per-arm context and wall-clock curves; consolidation topic-count trajectory at 12 domains; dream-event behavior over ~30 events (store growth, compression trajectory); digest cost and composition at 12 topics (if carried); checkpoint/resume events; seed determinism evidence.

---

## Limitations

One seed, one (new) script, one rater; n = 1 per arm at a scale where a run costs a working day — repeated-seed variance is explicitly out of budget and acknowledged. The new script breaks cross-study score comparability by design. Twelve sequential domains is one shape of long conversation; interleaved or revisited topics are untested (and are the natural follow-up if LTM survives). The plant grammar remains user-authored (script-correlation carried). Scripted-conversation ceiling carried: these results characterize this architecture on deterministic scripted interaction, not open dialogue.

---

## Open Decisions Before Lock

1. **Branch 1 / Branch 2 resolutions** from Study 009 (mechanical once 009 reports). [DECISION]
2. **Script + rubric + plant key authorship** — the long pole; can begin immediately since it has no 009 dependency. Author, review, hash-lock. [DECISION]
3. **`--ctx-size` re-derivation** from 009 measurements + G1–G3 projections. [DECISION]
4. **Interim checkpoint positions** (proposed 250/500/750) and their 3-question composition. [DECISION]
5. **Rater availability** (~46 blinded scorings). [DECISION]

---

## Appendix

Study 009 (branch inputs): `experiments/study_009/`. Study 007 treatment (Arm L source): `experiments/study_007/runs/study_007_full_001/`. New artifacts: `experiments/study_010/script_1000.json`, `q_facts_key_1000.md`, `rubric_1000.md`. Pre-registration path: `experiments/study_010/pre_registration.md`.
