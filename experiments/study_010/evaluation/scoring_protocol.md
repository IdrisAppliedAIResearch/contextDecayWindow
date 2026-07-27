# Study 010 Blinded Scoring Protocol

The two files under `arm_A/` and `arm_B/` contain only the 23 registered
probe exchanges. Anonymous assignment is hash-derived and recorded in
`sealed_mapping.json`.

The rater receives only these anonymous files, the locked rubric, and the
scoring-integrity protocol. It must produce primary and strict scores plus a
rationale for every arm-question pair. The sealed mapping and full-run
mechanism logs remain unopened until the score artifact is committed.
