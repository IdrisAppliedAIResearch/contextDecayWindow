# Study 010 Carried Subsystems Scale Audit

Study 010 found two carried subsystems that had survived the 120-turn program
but failed when exercised against the 1,000-turn design. Calling either
"settled infrastructure" before a scale test was unwarranted.

## 1. Topic Assignment And Consolidation

The binding G2 replay found no registered threshold pair that recovered the
12-domain structure without merging or fragmentation. The unchanged live
configuration ended with two topics in both arms. This is a direct scale
failure of the carried TopicManager and remains the confirmatory stop.

## 2. Persistent Rule Store

The first complete 200-turn rehearsal exposed a second failure. The carried
rule detector classified the script's turn-local instruction, "Stay within
the [domain] thread and do not connect it to other subjects," as a persistent
cross-turn rule. By turn 200 it had:

- pinned 118 false rules;
- grown the rule block to an estimated 5,512 tokens;
- carried the first domain's scope into later domains;
- produced its first cross-domain refusal at turn 84; and
- contaminated STM and LTM with refusal responses.

The locked script contains no genuine persistent-rule plant. Amendments
005-006 made the continuation executable by preserving response-boundary
parsing while forcing the persistence decision off in both arms. The final
runs therefore persisted zero rules.

Zero final rules is not evidence that the carried rule subsystem passed at
scale. It records that false persistence was disabled after the subsystem
failed rehearsal. Because the script contains no true persistent rule, the
continuation also provides no positive 1,000-turn test of rule retention.

## Program Lesson

"Settled infrastructure" meant only that the component had not failed in the
shorter regime tested so far. From this study forward, every carried subsystem
requires an explicit gate at the new maximum planned length, including:

- false-positive accumulation for rule-like local instructions;
- true-rule retention across the full horizon;
- topic count, purity, merging, and fragmentation;
- state and context growth; and
- interaction with retrieval and formation budgets.

The standing repository rules now also require a mechanical pre-lock probe
ordering check. `scripts/check_probe_fact_order.py` verifies that every
rubric-required fact occurs in a scripted user turn strictly before its probe.
Applied retrospectively to Study 010, it fails exactly I2, I5, and I8.
