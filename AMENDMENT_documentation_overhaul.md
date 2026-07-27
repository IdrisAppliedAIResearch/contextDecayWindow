# Amendment - Documentation Overhaul

## contextDecayWindow | Idris Applied AI Research

**Date:** July 26, 2026

**Type:** Repository documentation amendment. This is not a study amendment; it changes no pre-registration, criterion, score, or run artifact.

**Authorized by:** Muzaffer Ozen, authorized in the Study 009 closeout request on July 26, 2026

## Trigger

The root README was stale, agents repeatedly began work without the program's accumulated constraints, and the 2026-07-26 scoring-integrity audit invalidated numbers in user-facing documentation.

## Scope

This amendment:

- Replaces the root `README.md` with a concise, corrected program overview and study ledger.
- Adds root `AGENTS.md` as the operating manual for coding agents and contributors.
- Leaves all pre-registrations, sprint plans, decisions, study amendments, reports, runs, scores, `ERRATA.md`, and files under `experiments/` unchanged.

## Design Constraints

1. Keep the root README under roughly 130 lines.
2. Treat its one-row-per-study table as the current public state.
3. State failures plainly.
4. Publish only corrected, traceable metrics.
5. Explain where and in what order to read study artifacts.

## Standing Obligations

**O1 - Update the front door at study close.** A study is not closed and its PR must not merge until the same PR updates the README status and study table plus the AGENTS digest.

**O2 - Cap the digest.** Each study entry in AGENTS is at most 400 characters. Rewrite entries rather than increasing the cap.

**O3 - Propagate corrections.** Any score or verdict correction recorded in `ERRATA.md` must update README and AGENTS in the same commit.

**O4 - Use one PR per study.** Each study has its own branch and closes through a pull request carrying the outcome.

## Numbers

Figures come from `experiments/audits/scoring_integrity/audit_report.md` and `cascade_verdict_table.md`. The corrected treatment series for Studies 002 C, 003, 004, 005, 006, 007, and 009 L is 8.5, 11.5, 6.5, 11.0, 9.0, 12.0, and 12.0. Cross-study runtime and response-budget changes remain a confound; Study 009's same-seed S 9.0 versus L 12.0 comparison is the clean architectural contrast.

## Non-Claim

This amendment changes no result or verdict. It makes the existing record visible and establishes maintenance obligations.

## Verification

- [ ] README remains under roughly 130 lines and its numbers are traceable.
- [ ] AGENTS has one digest entry per study, each at most 400 characters.
- [ ] AGENTS makes O1 a blocking close requirement.
- [ ] This commit modifies no file under `experiments/`.
- [ ] Study 010 artifacts remain untouched.
- [x] Author authorization is recorded.
