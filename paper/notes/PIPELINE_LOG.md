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

---

## Stage notes

### Stage 0 — setup

The ARS repository stores `skills/*` as symlinks to top-level directories; symlinks
do not resolve on this Windows checkout, so the four skill directories were copied
from the clone's top level instead. `evals/heldout/` fails to check out under
Windows path limits and is not needed.
