# Decision 001: Post-Stop Exploratory Execution

**Date:** 2026-07-29

## Retrospective Classification

Study 010 stopped at its binding G2 gate. Its later 1,000-turn execution was
separately authorized and is exploratory-only; it does not reopen the stopped
confirmatory study.

The first Tier 6 run is not a second post-stop continuation. It was a registered
survey run later found protocol-invalid because live N ordering diverged from
the locked calibration semantics. It is preserved as a diagnostic and excluded
from architectural inference. Amendment 012 authorized a corrected rerun with
an offline/live equivalence gate.

## Standing Decision

Any future execution after a binding stop must be authorized in a standalone
decision or amendment committed before execution. That record must state:

1. The exact question the continuation can answer.
2. Its evidence class, which cannot inherit confirmatory status.
3. The stopped result and gate that remain binding.
4. The parameters, artifacts, and stopping rule.
5. The claims explicitly excluded from the continuation.

Post-stop evidence may motivate a new pre-registered study. It may not be merged
back into the stopped study's confirmatory verdict.
