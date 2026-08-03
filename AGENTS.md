# AGENTS.md - Operating Manual

Read this file before doing anything in this repository. It carries the program's history, standing rules, and workflow in a form that is cheap to load.

**If this file and a study's pre-registration disagree, the pre-registration governs. Stop and flag the conflict rather than reconciling it silently.**

## 1. Program

This repository contains ten pre-registered studies testing whether a language model can sustain a long conversation by rebuilding a small, relevant context each turn rather than carrying the whole transcript. Each study adds one component and addresses the previous study's documented failures.

The coding agent implements the registered design. Do not design studies, choose parameters, reinterpret criteria, or silently repair conflicts.

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

**CC-002 library extraction (2026-08-01).** The deployable component now lives in the installable `episodic` package; the harness imports it. T1-T7 pass: clean-venv import, leakage grep + import-graph, byte-identical reproduction of 132 committed A3 payloads and 3 rendered blocks, call-shape sentinel fails loudly, 804 tests green, two-process purity. H1/H2 ship as config-pinned gates, not docs.

**DX-002 context growth (2026-08-02).** BRANCH B. LTM saturates ~52-54k from turn 500 (H-A confirmed); retrieved_stm never does: p95 +23,238 L / +28,701 S over the last five buckets, still setting records at turn 1,000. Rule pinning added 0 but was disabled, not cleared. Blocks CC-003. A slope-CI-only rule first said Branch A; the interval measured power, not flatness.

**CC-003/004/005 closeout (2026-08-02).** CLOSED. G-E0 clears DX-002's block: episodic's block is bounded, +18 chars p95/1,000 turns, so the leak is the runner's. The ceiling no longer raises at tiny budgets; truncated carries dropped ids; drop order named (amendment 001); E6 inert at 132/132 SHAs. CC-004 kills real processes. CC-005: 190 ms at 1,000 candidates, no eviction. Suite 1,007.

**CC-006 vector cache (2026-08-05).** PASS. Exact solo-call float32 vectors are persisted and bound by file plus canonical text-to-vector SHA-256; read-only misses fail. C1-C9 pass. EC-002 adopts 96,585 entries with 0 model calls. Protection begins with retained caches; EC-001 remains permanently non-bit-replayable. Suite 1,028.

**LV-001 (2026-08-02).** RUN. B1 WEAK, B2 FAIL, **promotion killed on its own pre-registered bar**. The 6-item offline availability gap became +1 correctly attributed item live; targeted fell 3.5->1.5 against a 0.5 tolerance. A3 dropped turns 1-2 and could not state the formatting rules; offline it preserved 16/16. Availability is not the answer. Both arms fabricated the unretrieved art domain.

**EC-001 LongMemEval (2026-08-03).** COMPLETE, Codex-substituted. Top-4 held evidence on 401/470 but only 96 recalled any; blocks median 16 recency/0 K/1 coverage, all truncated. Tier 2 28/140 raw, 12.22% weighted; multi-session and temporal 0/20. Abstention 17/20 with 0 component signals.

**PAPER-001 (2026-08-03).** DRAFT, revised through EC-001 path audit. The forced pool/objective/floor decomposition stands. Naturalistic ranking lacks the dominant internal inversion, but delivery is governed by recency-first packing; the corpus-artifact cause remains unresolved. Source is `paper/PAPER_001.md`; figures/PDF are generated.

**Retrieval mechanism ledger (2026-08-03).** CLOSED. E002 KILL; exact-32k segmentation 6/17->10/17. AR-001: exact 14/17 costs 5,058 chars. E001 best .1204->.2103; 0/714 reached K=.48. F2 closed. F3 retired as a component requirement: 0/500 signals, reader abstention 17/20. E003 unauthorized.

## 3. Failure Pattern

The recurring failure class is a surrogate that can pass without the property it claims to certify: record count for information, novelty for importance, density for factual value, or a rubric score for a correct answer.

Before implementing any gate or criterion, ask whether it can pass while the certified property is false. Flag that possibility before writing code.

## 4. Standing Rules

### Pre-registration

- Commit the design before implementation; its SHA is the integrity anchor.
- Pre-registration commits contain no implementation files.
- Never edit a locked pre-registration. Record changes in standalone amendments.
- Parameters live in one authoritative place: the pre-registration.

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
2. Update the root `README.md` status line and study table.
3. Add or update the root `AGENTS.md` digest entry, keeping it at most 400 characters.
4. Update `ERRATA.md` when any published number changes.
5. Update memory files.
6. Commit all run logs, gate reports, and scoring artifacts.
7. Open the study PR.

Items 2 and 3 are mandatory. A study is not closed and its PR must not merge without them.

## 7. Never

- Let implementation precede pre-registration.
- Edit locked registrations, committed scores, or run artifacts.
- Add a second new component.
- Change criteria after observing results.
- Score an answerless item above zero.
- Expose rubric artifacts to mechanism code.
- Run unseeded or use a flag-disabled control.
- start a 120-turn run without a passing 35-turn ablation.
- Reopen a stopped study or bypass a binding gate without a new, authorized design.
- Report a result that cannot be traced to a committed artifact.

## 8. Repository Map

```text
README.md                                      current front door
AGENTS.md                                      this operating manual
ERRATA.md                                      corrections to published results
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
