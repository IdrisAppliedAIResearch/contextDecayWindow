# Study 010 Amendment 004: Authorized Exploratory Restart

**Date:** July 27, 2026
**Authorized by:** Muzaffer Ozen
**Authorization:** "We're good to go to continue study 10. You can make the
amendment files necessary to get the study going from the STOP condition. I
want you to run the study end to end."
**Applies after:** the binding G2 stop and Amendment 003
**Supersedes for future execution:** Amendment 003's prohibition on reopening
gates, rehearsal, or live inference
**Does not supersede:** the historical G2 result or the original confirmatory
verdict

## Trigger and Evidence

Study 010 stopped before inference because no registered TopicManager threshold
pair recovered 10-18 unmixed topics on the locked 12-domain script. The failed
attempts, final gate report, and binding decision remain committed. Completed
Study 009 audits subsequently corrected the program's expectations but did not
repair G2.

The author now explicitly requests completion of the 1,000-turn endurance
experiment. The failed gate cannot honestly be converted into a pass after its
result is known. Replacing TopicManager, adding supervised domain labels, or
choosing a new threshold using the failed replay would introduce a
post-outcome architectural change.

## Change

Study 010 is reopened as a **post-stop exploratory continuation**:

1. G2 remains **FAIL** and is non-waived historical evidence.
2. The carried TopicManager implementation and its registered 0.45 assignment
   and 0.45 consolidation thresholds remain unchanged in both arms.
3. G1, G4, and leakage checks must be rerun against the execution commit. Their
   original criteria remain binding for this continuation.
4. The registered 200-turn timed rehearsal remains required before either full
   arm. It must exercise each arm and all normal guards. A failed rehearsal
   stops the continuation.
5. After a passing rehearsal, Arm L and Arm S each run all 1,000 locked turns
   with the registered seed, model, sampling, context, checkpoint, and
   observability settings.
6. The original scoring rubric and Bar 1 thresholds are computed unchanged,
   but their post-stop results are explicitly labeled exploratory. They cannot
   convert the original stopped confirmatory study into a pass.
7. Arm order is fixed before rehearsal as L then S. No outcome may be inspected
   to change the second arm.

## Monitoring Cadence

For each 1,000-turn arm, process health and artifact growth are checked after
the first two completed turns, then at checkpoint milestones 100, 200, 300,
400, 500, 600, 700, 800, 900, and 1,000. Additional checks occur only on
process exit, missing progress, context-ceiling warnings, checkpoint failure,
or other recorded fault. The runner is not continuously polled.

## Rationale

This design answers the author's endurance question while preserving the
registered gate's meaning. It avoids selecting a TopicManager repair after
seeing G2, keeps the two-arm mechanism contrast intact, and makes the
confirmatory/exploratory boundary visible in every downstream artifact.

The continuation may reveal whether the known topic failure is operationally
fatal, benign, or arm-asymmetric. That evidence can motivate a future
pre-registered construction study, but it cannot validate the failed
consolidation subsystem.

## Exclusions

This amendment does not:

- edit the locked pre-registration, script, rubric, plant key, or artifact lock;
- change G2's threshold sweep, criterion, result, or decision record;
- add supervised domain IDs, adaptive thresholds, a new clustering algorithm,
  or another memory component;
- change either arm's retrieval, formation, rendering, or budget policy;
- permit inference before the amendment is committed;
- permit confirmatory language for evidence produced after the stop.

## Reporting Requirements

All new manifests, gate reports, rehearsal artifacts, run logs, scores, and
the final report must identify themselves as produced under Amendment 004.
The final report must present the original stopped result first and the
exploratory continuation separately. Root documentation may move Study 010
from `STOPPED AT G2` only to a wording that preserves both facts, such as
`STOPPED AT G2; exploratory continuation complete`.
