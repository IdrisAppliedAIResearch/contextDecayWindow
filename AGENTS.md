# AGENTS.md - Operating Manual

Read this file before doing anything in this repository. It carries the program's history, standing rules, and workflow in a form that is cheap to load.

**If this file and a study's pre-registration disagree, the pre-registration governs. Stop and flag the conflict rather than reconciling it silently.**

## 1. Program

This repository contains ten pre-registered studies testing whether a language model can sustain a long conversation by rebuilding a small, relevant context each turn rather than carrying the whole transcript. Each study adds one component and addresses the previous study's documented failures.

The coding agent implements the registered design. Do not design studies, choose parameters, reinterpret criteria, or silently repair conflicts.

**This program is building something that does not exist yet.** Read §9 before reporting any result. Discipline is what makes a finding trustworthy; it is not a licence to report every stop as a dead end.

## 2. Study Digest

**Cap: 400 characters per entry.** Rewrite entries to stay below the cap; never expand the cap. Scores below are post-audit corrected values.

**001 - Retrieval baseline.** Recency (N) plus similarity (K), 32 turns. PARTIAL (2/3); iterative 8.0/10. K fired once at 0.70. Thirty topics formed for 32 episodes, so the topic layer compressed nothing. Iterative context exceeded full context.

**002 - Scale and consolidation.** 120 turns, four domains, topic consolidation, rule pinning. PARTIAL (3/4); C 8.5/13. K recovered buried middle-domain facts. Consolidation failed with 52 topics. Context stayed about 10:1 smaller than full context. Last Q6_K run.

**003 - LTM write path.** STM-to-LTM promotion with four filters. PARTIAL (2/3); 11.5/13. The weighted route was unreachable because novelty and association were complementary values from one centroid, capped below threshold. All promotion used the bypass, making it a novelty-spike detector.

**004 - LTM read path.** Parallel STM/LTM retrieval, arbitration, dedup, tagged blocks. PARTIAL (1/3); 6.5/13. LTM retrieval ran on all 90 eligible turns with zero displacement but the store lacked later-domain planted facts. Formation, not retrieval, was the constraint.

**005 - The inversion.** Permissive raw storage with extractive dreaming. PARTIAL; 11.0/13. Formation was faithful and junk-free, but absolute entity and number counts selected long responses. The salience metric was a verbosity detector; only 2/4 domains formed.

**006 - Span selection.** Sentence spans, density-normalized salience, source weighting. PARTIAL (1/3); 9.0/13. Formation reached 4/4 domains with faithful, junk-free records. Records shrank about 28x while retrieval remained count-budgeted, so delivery collapsed.

**007 - Retrieval budget.** Character budget, domain diversity floor, containment dedup. PARTIAL (2/3); 12.0/13. It delivered all four domains at the breadth probe but scored 0 there. Post-run review found the model used all 10 available facts without invention; seven required facts were absent.

**008 - Rendering by floor factorial.** Registered 2x2 over rendering unit and floor policy. STOPPED AT PRE-RUN GATES. No fill cap from 1-50 passed breadth and targeted-retrieval gates jointly. The gates prevented four invalid 121-turn runs. Count caps cannot substitute for character allocation.

**009 - Null test.** Pure STM versus best LTM at one seed, plus topic digest. PARTIAL; null decisive. S 9.0 versus L 12.0: the memory tier beat plain retrieval by 3.0 at 120 turns. The digest failed every offline setting through d=50/50,000 chars and was dropped pre-run.

**010 - Endurance.** Confirmatory STOPPED AT G2. Post-stop L beat S 14-12 on breadth only; targeted tied; scores unaudited. L's Q13/Q14 blocks violated 32k by 67.9%/68.2%, so the compact-store conclusion is withdrawn. Bar 3 NOT EVALUABLE. TopicManager and rule persistence failed at scale.

**Scoring integrity audit (2026-07-26).** Re-scored 222 items across 001-009; 19 changed. Study 002 A fell 8.0->5.5, C 13.0->8.5; Study 001 lost VALIDATED. The residual 16.5/about-20 figure extrapolates 3/26 control disagreements over 143 unreviewed items. Study 010 is unaudited. See `ERRATA.md`.

**Retrieval bakeoff (2026-07-29).** MIXED. Widened STM delivered 6/6 formation-blind facts, used 5. S/W/L: 9/11/12; Q4 is gap. Turn-55 ranked N=27/32; K=.120<.48. Exact compact packing needs 108,432 chars to reach it. This is a joint rank/packing/budget boundary, not a distinct primacy result. T6 6.5 invalid; no 1,000-turn run.

**DR-001 rendering fix (2026-07-29).** PASS. Q13/Q14 were 53,726/53,839 chars: 67.9%/68.2% over 32k, not saturated. Compact, content-identical tags reduce them to 37,619/37,545; exact cost is now authoritative. All 2,000 context estimates match serialized prompts; L peak 27,154 survives as chars/4. AS-001 owns Q4.

**AS-001 Q4 packing (2026-07-29).** DIAGNOSTIC. Branch D's primacy verdict was invalidated post-result: its null could not fire, and no branch interpreted exact charging reducing 15 fitted episodes to 9. Rank 27 enters only at 108,432 chars under N-first packing. This identifies a joint rank/packing/budget boundary; no pinned-tier study is authorized.

**E005 diversity selection (2026-08-01).** PROMOTION_ELIGIBLE offline. Set-level selection beats A0 6/17 in all 146 configs; best gate-passing 12/17 at 4/4 domains, 16/16 targeted, 4/5 oracle episodes. Facility location led on count (13/17) but gave monetary 0/4 and passed nothing. Escalations: r not inert (greedy fills budget); deployed pool yields 0 four-domain configs. No live run.

**DX-001 turn-90 miss (2026-08-01).** NO CHANGE. E005's whole remaining oracle gap is one in-pool episode at cosine rank 112 with 4 monetary items; 0/146 configs take it. Cluster collision refuted: its cluster is never entered, so diversity paid in full and it still lost by .169. Needed cosine .225, has .056. 12/17 ships with the miss characterized; objective escalates to unauthorized E006.

**RD-001 rarity diagnostic (2026-08-03).** STOP: measurement not identifiable. Full 119-rank replay passes; rarity covers 6/76 episodes across 3 non-primary variants. Mean IDF is worse than density on 5/5 eligible plants, but max improves 2 and sum/word 1, so the IDF-family claim is withdrawn. No coefficient; Part 2 unauthorized.

**E006 Part 2 chained retrieval (2026-08-10).** Rev5 COMPLETE offline, CHARACTERIZED. Corrected Gram recurrence passes PF11 12/12 at 9.5e-15; PF1-PF10 and PF7 48/48 pass. Chaining raises single-shot top-m 3/17 and X0 6/17 to 9/17 at D2/D3, but uses 15-20 candidates, selects 12, misses art 0/4, and trails E005 12/17. No targeted traces; no promotion or live run.

**E006 Part 3 associative frontier (2026-08-10).** COMPLETE offline, NO_DIFFERENTIATED_CUE; CHARACTERIZED. At D2,m5 all arms admit 15 candidates, but A2 has 5/17 candidate and packed facts in civil only, versus A0 9 candidate/7 packed and A1 9/9. Best A2 is 6/17; art 0 throughout. PF1-PF10 pass; no targeted/live run, promotion, or adoption.

**E006 Part 3 Rev4 autoassociation (2026-08-10).** STOP at Part 1, PATTERNS_NOT_STORED; CHARACTERIZED. Hebbian 1024-bit recurrence passes synthetic reachability but stores 0/119 real episode codes as fixed points. All converge into 6 spurious attractors; G4 and Q11 not entered. Balanced marginals did not provide pattern separation. Original P3 result unchanged.

**BA-001 benchmark causal audit (2026-08-11).** COMPLETE, CHARACTERIZED. At matched 15 candidates, fixed query and chain contain identical 9/17 facts; the chain's 7->9 gain is packing only. Radius-1 adjacency reaches turn 55 and all 4 art facts (oracle only). Span vs whole episode gives 10 gains/0 losses. Art was stored/directly recalled; prior-conflict cause unidentified. No live run.

**TA-001 temporal adjacency (2026-08-11).** G5 FAIL; TARGETED_REGRESSION, CHARACTERIZED. Matched 15 candidates/32k: Q11 candidate 9->10, packed 7->9, art 0/4->4/4. Across 24 targeted queries: 2 gains, 6 losses, 16 ties; enumeration .3125->.125. The bridge trades semantic seeds for neighbours. No ablation, live run, promotion or adoption.

**SR-001 extractive spans (2026-08-11).** G3 FAIL; NO_BROAD_GAIN, CHARACTERIZED. With identical full source ranks/32k, source-grouped spans reduce Q11 8/17->4/17 and targeted facts 19->17: 0 gains, 2 losses, 22 ties; enumeration stays .0625. BA's 10-gain signal required span reranking, not representation alone. No ablation/live run.

**SAL-001 surprisal proximity (2026-08-11).** G2 FAIL; NO_INDEPENDENT_PROXIMITY. On 92 held-out sessions, adjusted neighbor AUC=.416 (95% .351-.484; p=.991), raw=.300; prior=.399, next=.477, 5/6 strata below .50. Posthoc self AUC=.621: surprise stays local, not transferred. P1-P4 capture killed; no accessibility/ablation/live.

**SUP-001 explicit supersession (2026-08-11).** FACTUAL PASS; byte-identity criterion withdrawn. Binary accessibility makes current-only 0/64->64/64, unchanged 32/32, histories 64/64, zero stale natural selections. Value interpretation gives C0 8/9, T1 9/9; `$35`=`$35.00`. Zero regressions. No 120-turn run or adoption is automatic.

**DMR deterministic multi-route arc (2026-08-12).** BLOCKED AT DMR-001. Six staged specs separate event formation, typed completion, encoding-context recurrence, query obligations, route control, and one-reader validation. DMR-001 ran and stopped, so there is no validated event substrate; DMR-002-006 require a new upstream design, not a retune.

**DMR-001 event-context formation (2026-08-12).** G3 FAIL; DEGENERATE_FORMATION. On the 2,000-episode holdout 52/74 events close on the size cap (.703 vs bar .35). All 20 drift boundaries match an annotation, precision 1.000; the 52 forced ones match none. Threshold .70 is above holdout drift's p95 but fires on 18.5% of dev: no transferable scale. G1/G2, PF1-PF10 pass.

**Study 010 corpus composition (2026-08-12).** Found by DMR-001. The 1,000-turn endurance script holds only 156 distinct user/assistant pairs: about 11 substantive turns per topical block plus ~70 exact repeats of a stay-on-thread filler. 844/1,000 episodes are exact duplicates. No published number changes; DX-002's saturation reading is qualified.

**DMR-001B adaptive drift formation (2026-08-12).** PASS, CHARACTERIZED; does NOT unblock DMR-002. A percentile-of-recent-drift bar holds fire-rate swing at 1.42-1.65x across all five grid cells where the fixed rule swung 9x-inf. Cap 128 never bound; 0 capped closures in 3,724 episodes. Worst family .419->.487, but the 1,000-turn family fell .733->.583. No sealed holdout; DEVIATION_001 recorded.

**DMR-001C sealed holdout (2026-08-12).** G5 FAIL; NO_BOUNDARY_EVIDENCE, but G4 CONFIRMS transfer. On 50 unread LongMemEval haystacks, 11,453 episodes, 2,128 real seams, the frozen relative rule holds fire-rate p95/p05 at 1.67x. Precision .837 vs .186 base rate, but recall .253 (min_event_size 5 vs 6-exchange sessions), so F1 .387 loses to C_PERIODIC_4's .606. F1 on a dense corpus rewards firing.

**DMR-004 query obligations (2026-08-12).** STOP; NO_MECHANICAL_SUFFICIENCY_SIGNAL. 180 sealed queries, two blind raters (finite kappa .770). Youden J .320 vs .50 and false-finite .188 vs .15 fail; LOOKUP recall .800, spans 1.000, 0/48 internal-only markers pass. Always-OPEN accuracy .650 vs .706. 12/31 misses are "which happened first, A or B", flagged pre-lock, not patched.

**NF-002 candidate granularity (2026-08-12).** CARRIES_SIGNAL; CHARACTERIZED. Registered session-touch rose 380->396/470; holdout 14 gains/6 losses, p=.058. Posthoc strict audit on 465 labelled items retains a smaller 375->388, 17 gains/4 losses. Formal disposition unchanged. Novelty null: 0/90.

**NF-003 ranking granularity (2026-08-13).** PREFLIGHT SURROGATE FAIL; UNREGISTERED. Session-touch said 396->445 (49/0), but 94 treatment hits carried no `has_answer` episode. Strict delivery fell 388->351: 26 gains/63 losses. Five unflagged items were never ranked. Proposed registration closed; LoCoMo successor stays sealed.

**NF-003 three-arm synthesis (2026-08-13).** CHARACTERIZED. Same 465 items/32k/strict measure: session-rank/session-pack 375, session-rank/episode-pack 388, episode-rank/episode-pack 351. Fine packing +13; fine ranking -37. The 63 coarse-rank rescues have median own-cosine rank 46 vs 10 for 26 fine-rank gains. Rule: rank coarse, pack fine.

**LoCoMo ranking development (2026-08-13).** DEVELOPMENT ONLY. On 871 unique questions, strict evidence delivery rose 820->855, 44 gains/9 losses, p=1.22e-6; complete evidence 773->826, 71/18. All four conversations were positive. Session-touch hid all 9 losses. Six holdout conversations remain sealed; no bars, registration, disposition or holdout run.

**PS-001 pattern-separated engram formation (2026-08-11).** CHARACTERIZED. Nine deterministic sparse cells on 119 episodes; only D=4096,K=41 passed G3-G5: 119/119 fixed points and exact 1/10/30/50% swap recovery. Six of seven degenerates reached stored codes; the union-biased cue cycled. Code-space result only; no natural cue, retrieval, live run, promotion, or adoption.

**PS-002 natural-language cue binding (2026-08-11).** STOP AT PART 1; NATURAL_CUES_NOT_BOUND, CHARACTERIZED. Nine label-blind cells ran 24 sealed queries x8 rounds. Best M=4,tau=.025 reached stored codes 190/192 but one cue cycled and one reached a spurious fixed point; no cell emitted 8 clean ids/query. Labels, PF1-PF10, answers, live run, promotion and adoption not entered.

**PS-003 ambiguous cue resolution (2026-08-11).** G3 FAIL; LOOKUP_BINDING_INSUFFICIENT, CHARACTERIZED. Five-probe/four-swap consensus emits 8 safe ids for all 24 queries after rejecting 3 cyclic, 1 spurious and 1 disagreeing family. Lookup stays 7/12 vs cosine and PS-002; monetary 1/3. G4/G5, stress, answers, live run, promotion and adoption not reached.

**CC-002 library extraction (2026-08-01).** The deployable component now lives in the installable `episodic` package; the harness imports it. T1-T7 pass: clean-venv import, leakage grep + import-graph, byte-identical reproduction of 132 committed A3 payloads and 3 rendered blocks, call-shape sentinel fails loudly, 804 tests green, two-process purity. H1/H2 ship as config-pinned gates, not docs.

**DX-002 context growth (2026-08-02).** BRANCH B. LTM saturates ~52-54k from turn 500 (H-A confirmed); retrieved_stm never does: p95 +23,238 L / +28,701 S over the last five buckets, still setting records at turn 1,000. Rule pinning added 0 but was disabled, not cleared. Blocks CC-003. A slope-CI-only rule first said Branch A; the interval measured power, not flatness.

**CC-003/004/005 closeout (2026-08-02).** CLOSED. G-E0 clears DX-002's block: episodic's block is bounded, +18 chars p95/1,000 turns, so the leak is the runner's. The ceiling no longer raises at tiny budgets; truncated carries dropped ids; drop order named (amendment 001); E6 inert at 132/132 SHAs. CC-004 kills real processes. CC-005: 190 ms at 1,000 candidates, no eviction. Suite 1,007.

**CC-006 vector cache (2026-08-05).** PASS. Exact solo-call float32 vectors are persisted and bound by file plus canonical text-to-vector SHA-256; read-only misses fail. C1-C9 pass. EC-002 adopts 96,585 entries with 0 model calls. Protection begins with retained caches; EC-001 remains permanently non-bit-replayable. Suite 1,028.

**LV-001 (2026-08-02).** RUN. B1 WEAK, B2 FAIL, **promotion killed on its own pre-registered bar**. The 6-item offline availability gap became +1 correctly attributed item live; targeted fell 3.5->1.5 against a 0.5 tolerance. A3 dropped turns 1-2 and could not state the formatting rules; offline it preserved 16/16. Availability is not the answer. Both arms fabricated the unretrieved art domain.

**EC-001 LongMemEval (2026-08-03).** COMPLETE, Codex-substituted only. On 470 answerable items, top-4 held no evidence for 14.7%; exact-turn availability was 16.8%. Tier 2: 28/140 raw, 12.22% post-stratified; gap -2.54 pp. Multi-session and temporal 0/20; abstention 17/20 despite 0 component signals. Not an official benchmark score.

**EC-002 K-first packing (2026-08-05).** COMPLETE offline. Same-store K-first raises any-session recall 109/470->261/470: 152 gains, 0 losses. Exact-turn-any 79->196: 119 gains, 2 losses. K deliveries 26->476; all blocks still truncated. Confirms recency-first budget exhaustion as a causal gate. No production/Tier 2 promotion authorized.

**IC-001 internal packing (2026-08-06).** BRANCH A. K-first replay from frozen candidate identities; 0 model calls. B0 reproduces the deployed 6/17 at 31,946 chars exactly. Under the deployed order K delivered 0 episodes at 8/8 probes; K-first gives 9. Q11 6/17->7/17, targeted 14/21->18/21, zero losses. No CC-006 cache here; Amendment 001 authorized, enforced as a gate.

**011 - Tier isolation.** RUN; B1 FAILS. Four live 121-turn arms behind the first binding pre-test (G1-G7, T=6/13). Deployed arm 8.0 = STM-only 8.0 on all 13 questions: the LTM tier is inert as shipped. K-first delivers 13 K episodes vs 1, raises Q11 to 10/17 and targeted to 10/21, scores 7.0. Not adopted. Same prompt, same seed, different answer: -1.0 sits in unmeasured noise.

**N-tier mislabel (2026-08-08).** The tier the arc calls a recency window is a least-recently-delivered rotation over the whole store; replay matches the live ranking 120/120 turns per arm. Overlap with a real window 0.29, 36% of deliveries older than the cap, reaches all 120 episodes. Three rules carry the name; the only real window is in `episodic`, which no scored live study ran. B1 unchanged.

**Carried N rule was a locked prefix (2026-08-08).** Every live run through Study 010 ranked freshest-delivery-first and refreshed what it delivered, so the block re-selected itself: from turn 11 it held source turns 1-9 plus turn t-1, for 111 turns in Study 009 and 999 in Study 010. Replay exact on 17 runs, 12 lock. Overlap with a real window 0.205. Read the key AND what touches it.

**Instrument band is 3.0 (2026-08-09).** Amendment 001 run. Five arm-D replicates, identical everything: four score 8.0, one 11.0. Not a spread but a switch - four are byte-identical across 121 turns; the one meeting an empty server slot diverges at turn 1. Study 009's 3.0, LV-001's -2.0 and 011's -1.0 are NOT DEMONSTRATED. Offline counts untouched. B1 stays fired.

**PAPER-001 (2026-08-07).** DRAFT, revised through Study 011. The pool/objective/floor decomposition stands, but Â§5's 6/17 is packing-conditioned: new Â§5.2.2 records that the internal K path delivered nothing at 8/8 probes. Naturalistic ranking lacks the dominant internal inversion. Corpus-artifact cause unresolved. Source is `paper/PAPER_001.md`; figures/PDF are generated.

**Retrieval mechanism ledger (2026-08-03).** CLOSED. E002 KILL but exact-32k segmentation improved 6/17->10/17. AR-001 proves exact 14/17 costs 5,058 chars. E001 best-found .1204->.2103; 0/714 reached K=.48. F2 closed. EC-001 measures F3 externally: 0/500 component absence signals, but reader abstention 17/20. E003 unauthorized.

## 3. Failure Pattern

The recurring failure class is a surrogate that can pass without the property it claims to certify: record count for information, novelty for importance, density for factual value, or a rubric score for a correct answer.

Before implementing any gate or criterion, ask whether it can pass while the certified property is false. Flag that possibility before writing code.

## 4. Standing Rules

### Pre-registration

- Commit the design before implementation; its SHA is the integrity anchor.
- Pre-registration commits contain no implementation files.
- Never edit a locked pre-registration. Record changes in standalone amendments.
- Parameters live in one authoritative place: the pre-registration.

### Preflight — required in every spec, before any run

**No spec is complete without a Preflight section, and no run begins before
Preflight passes.** Studies, analyses, counterfactuals, diagnostics, engineering
specs and benchmark adoptions alike. A spec without Preflight is returned, not
run. Full wording and the failing precedent behind each check: `PREFLIGHT.md`.

Two parts, in order.

**Part 1 — Exploration.** Characterize the mechanism empirically before designing
a test of it. Not by reading the code, not by trusting its name, not by citing a
prior study. Run it and record what it does; findings may change the design
before anything is locked. Minimum, for any spec touching an existing component:
behavioral identity in one falsifiable sentence; a name-to-behavior check on
every named component, block, tier and variable; the distribution rather than a
summary; and degenerate or absorbing states demonstrated on a real trace.

**Part 2 — Checklist.** Every item answered explicitly. *"Assumed" is not an
answer; "verified at `<SHA>`" is.*

| # | Check |
|---|---|
| **PF1** | Inputs exist — present, readable, hash-identified, counted |
| **PF2** | Mechanism identity verified against its name and description, on committed data |
| **PF3** | Gate ordering enforced, not assumed — proven to execute before what it gates |
| **PF4** | Thresholds achievable — every bar and kill condition checked reachable before locking |
| **PF5** | Comparison keys stable — content hashes, never generated ids, timestamps or paths |
| **PF6** | Reproduction anchor — a replay reproduces a known result by identity and digest, not by count |
| **PF7** | Absorbing-state proof for any mechanism with feedback, on a real trace of the intended length |
| **PF8** | Ablation length adequate — state what it can and cannot detect |
| **PF9** | Surrogate audit — can this pass while the property it certifies is false? Record residuals |
| **PF10** | Live-evaluation requirement stated — availability is not a verdict |

**Ticked boxes are not Preflight.** Each check names the artifact or the executed
test that answers it.

### Gates and ablation

- Offline gates are binding and run before full inference.
- Before artifact lock, mechanically verify that every rubric-required fact is planted in a scripted user turn strictly before its probe. Any unavailable fact blocks lock and inference.
- Run at least a 35-turn ablation before a 120-turn run.
- Commit calibrated settings before the ablation.
- Replay harnesses must reproduce a known result exactly before producing evidence.
- Revalidate every carried subsystem at the study's maximum planned scale. A pass at 120 turns does not make infrastructure settled at 1,000 or 10,000 turns.

### Runtime and determinism

- Use a fixed seed, `--parallel 1`, and no speculative decoding.
- Record the launch command and server build hash in every run header.
- Require a byte-identical seeded prefix rerun.
- Assert the script SHA after decoding and use explicit UTF-8 encoding.

### Controls

- Run controls from checked-out prior code in a separate worktree, never by disabling features in the current runner.
- Reject dirty worktrees, unexpected diffs, wrong script hashes, import escapes, or current-study engine leakage.
- Record module paths, server properties, command, and PID before inference.

### Leakage

- Retrieval, formation, ranking, and gating code must not read or depend on `q_facts_key.md` or rubric artifacts.
- Measurement may use the plant key; mechanism may not.
- Enforce the boundary with grep, import-graph checks, and a planted test violation.

### Scoring

Full rules are in `experiments/audits/scoring_integrity/PROTOCOL_scoring_integrity.md`.

- Only content outside reasoning blocks is scoreable. No final answer is `NO_ANSWER` and scores 0.
- Commit completeness and fact-presence checks before accepting scores.
- Every score needs a rationale; conflicts block the commit.
- Calibrate AI raters on a planted `NO_ANSWER`, then use three blind passes and registered human-adjudication triggers.
- Commit every arm's scores before anyone opens mechanism logs; git order is the evidence.
- Keep rubrics byte-identical. Resolve ambiguities from criterion text before reading affected answers.

### Scope

- Add one new component per study.
- Stop if implementation would alter a carried subsystem.
- Diff-review carried subsystems to prove they are unchanged.

## 5. Amendments

Amendments are permitted for genuine blockers. Add a standalone file at `experiments/study_NNN/amendments/AMENDMENT_NNN_short_name.md`; never edit the locked pre-registration. Include the trigger and evidence, change, rationale, exclusions, and author authorization.

Legitimate amendments correct measurement units, repair protocol contradictions, and do not make a criterion easier after results are known. Adding a factor, policy level, or budget is a new study and must be escalated.

## 6. Workflow

- Use one branch per study: `study/NNN-short-name`.
- Work sprint by sprint and commit at task granularity.
- Preserve commit order for gates, ablations, scoring, and mechanism analysis.
- Close every study with its own pull request.

The PR body must state the outcome, bars, findings, amendments, artifact links, and checklist status.

### Blocking Study Close Checklist

1. Commit the report with the pre-registration SHA in its header.
2. Update the root `README.md` (see *README structure* below).
3. Add or update the root `AGENTS.md` digest entry, keeping it at most 400 characters.
4. Update `ERRATA.md` when any published number changes.
5. Update memory files.
6. Commit all run logs, gate reports, and scoring artifacts.
7. Open the study PR.

Items 2 and 3 are mandatory. A study is not closed and its PR must not merge without them.

### README Structure

The root `README.md` has two halves and they have different readers. Everything
above the `# For LLM Context` divider is written for a person deciding whether
this work is worth their time; everything below it is written for an agent
picking the work up with no prior context.

**Above the divider — keep it short.** Paper link, executive summary, current
state of work, next steps. Closing a study means:

- Update *Current State of Work* — its date, its arc table row, its constraints.
  Replace what is stale rather than appending to it. This section describes the
  present, not the history.
- Rewrite *Next Steps* so the top item is what a reader should do next. A step
  that has been taken is deleted, not marked done.
- Touch the *Executive Summary* only when a finding changes what the program
  claims. It is four findings and a stated limit; it does not grow by one
  paragraph per study.

**Below the divider — this is where detail belongs.** Add the study's status
blockquote to the ledger and its row to *What Has Been Tested*, with numbers
and artifact paths. Density is correct here. If a result needs more than a
blockquote, give it a section, as the arcs have.

Never resolve a length problem by moving detail above the divider or by
compressing a status blockquote until its numbers are gone. The two halves fail
in opposite directions: the top becomes unreadable, the bottom becomes
unciteable.

## 7. Never

- Let implementation precede pre-registration.
- Edit locked registrations, committed scores, or run artifacts.
- Add a second new component.
- Change criteria after observing results.
- Score an answerless item above zero.
- Expose rubric artifacts to mechanism code.
- Run unseeded or use a flag-disabled control.
- Run any spec without a passing Preflight (§4, `PREFLIGHT.md`).
- start a 120-turn run without a passing 35-turn ablation.
- Reopen a stopped study or bypass a binding gate without a new, authorized design.
- Report a result that cannot be traced to a committed artifact.
- Introduce a lower disposition bar, or a "this carries signal" reading, after a number is on the table. Both tiers are registered before the run or neither exists (§9).
- Report `STOPPED` without saying whether the mechanism failed or the instrument could not test it (§9).

## 8. Repository Map

```text
README.md                                      current front door
AGENTS.md                                      this operating manual
ERRATA.md                                      corrections to published results
PREFLIGHT.md                                   mandatory preflight; §4 carries the mandate
experiments/audits/scoring_integrity/          scoring protocol and 2026 audit
experiments/study_NNN/
  pre_registration.md                          locked design and SHA anchor
  study_NNN_sprint_plan.md                     execution plan
  amendments/                                  authorized standalone changes
  decisions/                                   authorized decisions
  q_facts_key.md                               measurement only
  runs/                                        logs and analyses
  study_NNN_report.md                          result and limitations
experiments/probes/                            exploratory work outside the arc
experiments/internal/packing_priority/         IC-001 packing-order counterfactual on the internal corpus
paper/
  PAPER_001.md                                 terminal research document; the source of truth
  Selection_Not_Capacity.pdf                   typeset build of the above; generated, never authored
  CLAIM_TO_ARTIFACT.md                         every claim with its committed artifact and hash
  REPRODUCTION.md                              Appendix E; clean-environment check of one headline number
  reproduce_headline.py                        that check; reader-facing, runs against the installed library
  figures/                                     generated SVG/PNG plus figure_manifest.json
  notes/EVIDENCE_INDEX.md                      spec-versus-artifact reconciliation
  reviews/                                     two adversarial cycles, slop audit, three-reader review
experiments/components/live_validation/
  LV_001_pre_registration.md                   live validation of the shipping selector; PRE-REGISTERED, NOT RUN
experiments/components/biological_memory/deterministic_retrieval/
  DMR_ARC_IMPLEMENTATION_ROADMAP.md            design-only six-stage deterministic retrieval arc
scripts/generate_paper_001_figures.py          rebuilds paper/figures/ from committed artifacts
scripts/build_paper_pdf.py                     rebuilds the PDF from PAPER_001.md; needs `pip install typst`
```

### The paper is generated, not authored

`paper/PAPER_001.md` is the only place a claim in the paper may be edited. The
figures and the PDF are build outputs of the two scripts above.

- Edit `PAPER_001.md`, then re-run **both** scripts. Hand-editing a figure, the
  PDF, or `paper/build/` is a defect, not a shortcut.
- Figure numbering lives in the Markdown, not in the typesetter, so a renumber
  means editing the Markdown and the generator together. The build places each
  figure at the paragraph that first cites it; if citation order and figure
  order disagree, fix the numbering rather than the placement.
- Every figure caption carries its artifacts' SHA-256 prefixes. If an artifact
  changes, the caption and `figure_manifest.json` change with it.

## 9. Reading a Result

Nobody has built this. A memory layer whose formation, ranking, routing and
stopping are all deterministic does not exist in the field; the industry
comparison — Mem0 and its neighbours — spends a language-model call on exactly
this layer. So the question is rarely *does the deterministic version win*. It
is **how much of that layer survives without the call.** A mechanism that
recovers most of it and still loses head-to-head is a finding. Reporting it as
a failure throws the finding away.

Three habits follow. They are obligations, not encouragement.

### 9.1 A stop closes a design, not a question

DMR-001 stopped on an absolute drift threshold. DMR-001B replaced it with a
relative one and passed every gate. DMR-001C confirmed the operating point on a
sealed holdout. The blocking claim written the day DMR-001 stopped was carried
forward through two more stages after the evidence beneath it had changed, and
it wrongly blocked two runnable stages.

When a stage stops, write down **what exactly is closed** — this rule, this
instrument, this corpus, this parameter — and never more than that. When new
evidence lands, re-read every downstream blocking claim against it. A blocking
claim inherits no authority from age.

### 9.2 Separate an instrument failure from a mechanism failure

NF-001 stopped because `NEVER_STOP` scored zero regret on 32-candidate streams:
the rig could not make stopping cost anything, so it could not rank a stopping
rule. DMR-004's span gate was unfalsifiable because the extracted span covered
a median 0.91 of the query. In both cases **the mechanism was never tested.**

A report that says `STOPPED` without saying which of the two happened is not a
finding, it is a tombstone. Say which. If the instrument failed, name the
instrument that would work.

### 9.3 A weak signal is a result when it was registered as one

Register **two dispositions before the run**:

- the bar for *this works*, and
- a separate, lower, explicitly numbered bar for *this carries signal worth a
  successor*.

Both fixed in advance, both in the pre-registration, both reachable in each
direction under PF4. A result landing between them is reported as signal, with
its margin, its sample size, and the successor it justifies — not rounded down
to a failure and not rounded up to a pass.

Weak means weak. Say so: NF-001's novelty rule beat matched fixed depth 11 times
in 14 by under one fact on 16 streams, and "suggestive, not demonstrated" is the
honest description of that.

### 9.4 The guardrail

None of this licenses reinterpreting a result after seeing it.

The lower bar counts **only if it was registered before the run**. The moment a
"carries signal" reading is applied to a number already on the table, it stops
being research and becomes rescue — and rescue is the exact failure this
program's pre-registration discipline exists to prevent. §3's question has a
mirror image, and both must be asked:

- Can this gate **pass** while the property it certifies is false?
- Can this gate **fail** while the property it certifies is true?

§7 forbids introducing either tier late. That prohibition is what makes the
lower tier worth anything.
