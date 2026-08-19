# Pipeline log — PAPER-002 rewrite

Auditable record of the academic-research-skills pipeline run that produced
`paper/PAPER_002.md`.

**Process.** The ARS suite (deep-research 2.12.1, academic-paper 3.3.1,
academic-paper-reviewer 1.11.1, academic-pipeline 3.21.0) gates every stage on a
human confirmation. Those checkpoints are answered here by the
`principal-investigator` subagent (`.claude/agents/principal-investigator.md`),
which reads `EVIDENCE_SPINE.md`, `DO_NOT_WRITE.md` and `AGENTS.md` before each
answer and may not approve a claim it cannot trace to a committed artifact.

**Precedence.** Where ARS and `AGENTS.md` disagree, `AGENTS.md` wins. ARS is a
writing, review and integrity process layered on top of this repository's artifact
provenance; it does not replace it. `AGENTS.md` §8 still governs: the paper is
generated, not authored, and every figure is a build output.

**Scope.** No new experiments. No pre-registration is required for a rewrite. If any
published number moves, `ERRATA.md` gets an entry.

---

## Log

| Date | Stage | Verdict | Reason |
|---|---|---|---|
| 2026-08-18 | 0 — setup | DONE | Four ARS skills installed to `~/.claude/skills/`; checkpoint subagent defined |
| 2026-08-18 | 1 — evidence spine | DONE | `EVIDENCE_SPINE.md` and `DO_NOT_WRITE.md` committed at `af3913e3`, before any prose |
| 2026-08-18 | 2 — write | DONE | `PAPER_002.md` sections 1–13 and appendices drafted |
| 2026-08-18 | 2.5 — claim gates | PASS | Number trace and withdrawn-value gates green; 33 untraced numbers found and traced |
| 2026-08-18 | 2.5 — integrity review | APPROVE WITH CHANGES | Seven findings applied; DMR-004's raters were described as human against the protocol |
| 2026-08-18 | 1 — positioning | DONE | 15 citations, 13 verified, 2 unresolvable; `COMPETITIVE_LANDSCAPE.md` |
| 2026-08-18 | 5 — figures | DONE | 7 figures, 33 hashed inputs, byte-identical across two runs |
| 2026-08-18 | 5 — finalization | DONE | PDF builds at 22 pages; PAPER-001 retired and every reference repointed |
| 2026-08-18 | 5 — regression check | PASS | 1,831 passed / 1 failed, identical to the pre-change baseline |
| 2026-08-18 | 3 — peer review (Cycle 3) | 30 OBJECTIONS, ALL ACCEPTED | Reframe crossed into overclaim in the summary and conclusion; body within evidence |
| 2026-08-18 | 4 — revision | DONE | All 30 applied |
| 2026-08-18 | 4.5 — re-review (Cycle 4) | 14 FIXED / 12 PARTIAL / 2 NOT FIXED / 0 REGRESSED | Reader test now passes; every partial fixed only at the quoted site |
| 2026-08-18 | 4.5 — value-grep pass | DONE | All partials fixed at every site; 9 new objections applied |
| 2026-08-18 | 5 — final regression | PASS | 1,831 passed / 1 failed, identical to baseline |

---

## Stage notes

### Stage 0 — setup

The ARS repository stores `skills/*` as symlinks to top-level directories; symlinks
do not resolve on this Windows checkout, so the four skill directories were copied
from the clone's top level instead. `evals/heldout/` fails to check out under
Windows path limits and is not needed.

### Stage 2.5 — the claim gate found real defects

The number-trace gate failed on first run with 33 untraced measurements. All 33
traced to committed artifacts and are now in `EVIDENCE_SPINE.md` §7; none had to be
cut. Two gate bugs were fixed in the same pass: section-heading digits were being
read as claims, and the withdrawn-value check was parsing a table's index column.

A third distinction emerged and is recorded in the spine at §7.11. A value the paper
names *while correcting it* is not a revived claim — naming the superseded figure and
then giving the corrected one is how `ERRATA.md` records a correction, and is the
opposite of restating it. The machine-checkable forbidden list therefore holds only
values with no legitimate corrective use.

### Stage 2.5 — the integrity review caught an overclaim

The checkpoint returned APPROVE WITH CHANGES with two blocking items. The first was
a real error: §5.2 described DMR-004's two annotators as human. `DMR_004_ANNOTATION_
PROTOCOL.md` records rater A as the implementing agent and rater B as the carried
local model, and §12.8 of this same paper says the raters were not human. The draft
contradicted itself in favour of the stronger reading, which is the exact direction
a confident reframe fails in.

The review also checked the opposite failure and found none: no well-evidenced
result was hedged into vagueness, and the sealed-holdout result reads as what it is.

### Stage 5 — a build defect the restructure exposed

`build_paper_pdf.py` closed the executive-summary and abstract wrapper blocks on a
heading matched by its literal title, "Reading this paper" — a section PAPER-001 had
and PAPER-002 does not. The block never closed, and Typst reported an unclosed
delimiter 670 lines from the cause. Closing is now structural.

### Stage 5 — regression check

`.venv/Scripts/python.exe -m pytest -q` returns **1,831 passed, 1 failed**, which is
the baseline exactly. The single failure is
`test_nf004_study.py::test_artifact_identity_uses_raw_bytes`, documented in
`ERRATA.md` (2026-08-18) as a constant that never matched the file it names.
Deleting `PAPER_001.md`, `generate_paper_001_figures.py` and the PAPER-001 figure set
broke nothing: no test referenced them.

### Cycles 3 and 4 — what adversarial review was worth

Cycle 3 raised thirty objections and its verdict was that the reframe crossed into
overclaim, confined to the executive summary and conclusion. The diagnostic was not
any single error but their direction: six overstatements and one omission in the
summary all ran the same way. Tuning for confidence and not re-checking each claim
against its cap produces exactly that signature.

Cycle 4 then found the repair had the same defect in miniature. Twelve of the thirty
were fixed at the site Cycle 3 quoted and nowhere else — "eleven pre-registered"
survived in the subtitle, the pruning claim survived as §7.2's own closing line
contradicting §7.2, and §8.3 kept "byte-identically replayable" fourteen lines under
§8.1's new denial of it. `PASS_6_SLOP_AUDIT.md` records the only method that works
and it was not used: grep for the superseded value rather than rereading.

Two findings justified Cycle 4 by themselves. `EVIDENCE_SPINE.md` still carried the
retired four-level taxonomy while the paper cited it as authoritative — the gate
document disagreeing with the gate — and the new REGISTERED-OFFLINE level required
"byte-identical on replay" while its own EC-002 row denied it.

**The standing bias, recorded because it is not fixable by more editing.** Across
both cycles the magnitude of the overclaim collapsed and its sign did not: the three
smallest errors Cycle 4 left open all still make the component look stronger. Any
future edit to this paper should assume that bias is present.
