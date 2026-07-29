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

**010 - Endurance.** Confirmatory STOPPED AT G2. Post-stop L beat S 14-12 on breadth only; targeted tied. Bar 3 NOT EVALUABLE due unplanted probe facts. TopicManager and rule persistence both failed at scale. LTM is retained exploratorily, but breadth may be compact-store dependent; T1.2 must stress fixed-budget retrieval.

**Scoring integrity audit (2026-07-26).** Re-scored 222 items across 001-009 after a truncated Study 002 reasoning block had been credited as complete. Nineteen scores changed; Study 002 C fell 13.0 to 8.5 and Study 001 lost VALIDATED. Corrected arc: 8.5, 11.5, 6.5, 11.0, 9.0, 12.0, 12.0. See `ERRATA.md`.

**Retrieval bakeoff (2026-07-29).** MIXED. Widened STM delivered 6/6 formation-blind facts, used 5. S/W/L: 9/11/12; Q4 is gap. Turn-55 ranked N=27/32; corrected K=.120<.48. Compact rendering still excludes it through 64k. LTM's observed edge is primacy under N-first packing. No other function beats matched raw volume. T6 6.5 invalid; no 1,000-turn run.

**DR-001 rendering fix (2026-07-29).** PASS. G-R1 reproduced Q13/Q14 exactly and found actual LTM blocks were 53,726/53,839 chars, not charged 31,991/31,847. Compact tags preserve identity/order/content and reduce them to 37,619/37,545. Exact block cost is now authoritative. B_ltm=32k, N=32, k_min=1, and containment retained.

**AS-001 Q4 packing (2026-07-29).** Branch D. Compact N-first packing fits 9/32 candidates at 32k and 16/32 at 64k; rank-27 turn 55 never enters. Historical 15/59,708 replayed exactly. Q4 is a late-rank packing exclusion, not tag expansion; primacy remains live. Cosine corrected .1661->.1204, still below K=.48. The sealed DB was never committed; logs reconstruct the inputs.

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
```
