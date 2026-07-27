# Protocol - Scoring Integrity

**Status:** Standing from adoption forward.

1. Only content outside reasoning blocks is scoreable. No final content means
   `NO_ANSWER`, mechanically scored 0.
2. Completeness is checked before scoring. Truncation is a protocol deviation.
3. Every score is accompanied by committed mechanical fact-presence evidence.
4. A score is blocked when its rationale conflicts with completeness, fact
   presence, domain coverage, rubric thresholds, or is missing.
5. The AI rater must pass a synthetic calibration gate, including a substantive
   reasoning-only `NO_ANSWER` scored 0, before seeing real answers.
6. Three blind passes are required. Disagreement is measured and adjudicated.
7. H1-H5 triggers follow the locked audit pre-registration. H4 is never waived.
8. Arm identity is masked; mapping is sealed before scoring and opened afterward.
9. Scores are committed before mechanism logs are opened.
10. Guidance may interpret locked criteria but may not change rubric bytes.
11. Confirmatory bars must state whether their target is architecturally reachable.
12. Corrections are additive, bidirectional, and indexed in root `ERRATA.md`.
13. Every cross-study score reference cites the source artifact commit SHA and is
    recomputed when the referenced score changes.
14. Plant keys and rubrics may inform evaluation only. Retrieval, formation,
    ranking, and runtime context assembly may never read them.

The scoring harness must reject score-above-zero for `NO_ANSWER`, missing
rationales, and rationale/evidence contradictions.

