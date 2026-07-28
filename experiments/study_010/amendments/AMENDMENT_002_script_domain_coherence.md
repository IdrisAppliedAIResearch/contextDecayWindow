# Study 010 Amendment 002: Script Domain-Coherence Correction

**Timing:** after the first offline G2 replay, before rehearsal or live inference
**Artifact lock superseded:** `52f05e7`

## Finding

The first generated script reused eight generic filler questions verbatim in
all 12 domains. G2 showed that embeddings clustered those turns by prompt
template rather than subject: the carried 0.45 thresholds produced two
cross-domain topics, while higher thresholds fragmented to 19-104 topics.
No swept setting recovered the intended domain structure.

## Correction

Each filler turn now names a domain-specific, non-scored analytical facet and
explicitly stays within that subject thread. This removes cross-domain
duplicate templates and marks sequential thread boundaries without repeating
any locked project, person, value, specification, or threshold. The following
remain unchanged:

- 1,000 turns and all probe positions;
- 12 domains and all 36 plant turns;
- every planted fact and rubric criterion;
- S/L architecture, runtime, seed, and retrieval policies;
- gate acceptance criteria.

The script hash is replaced and the artifact triple is re-locked. The failed
G2 result is retained as `gates/attempt_001/`; all gates rerun against the new
hash. This correction addresses structural script coherence and does not tune
which planted fact a retrieval query should select.
