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
| 2026-08-18 | 2.5 — integrity review | RUNNING | Seven-mode blocking checklist via the principal-investigator subagent |
| 2026-08-18 | 1 — positioning | RUNNING | Published competitor results with citation verification |
| 2026-08-18 | 5 — figures | RUNNING | `generate_paper_002_figures.py` under the PAPER-001 provenance contract |

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
