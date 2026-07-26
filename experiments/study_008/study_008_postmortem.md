# Study 008 Post-Mortem - Answers From the Gated STOP

**Date:** July 26, 2026
**Study status:** COMPLETE - STOPPED AT PRE-RUN GATES
**Registration commit:** `0a20ef0`
**Binding STOP commit:** `4a29540`
**Live inference runs:** none

## Bottom line

Study 008 did not establish which retrieval arm produces better answers. It
established something earlier and more useful: the registered intervention did
not have a feasible operating point under its fixed 32,000-character budget.

The central design error was a unit mismatch. Factor F limited fill in
**records per topic**, while Gate 3 protected targeted retrieval in **rendered
characters**. Factor R then changed what one record meant:

- an episode record carried thousands of characters and surrounding facts;
- a span record carried a small fragment plus repeated provenance markup;
- the same numeric `c_fill` therefore imposed very different character
  allocations in the two rendering conditions.

At `c_fill = 1`, Arm B bought four-domain breadth by giving each topic a small
number of episode-sized opportunities, but its worst targeted query delivered
only 3,313 own-domain characters out of 28,855 (11.48%). At `c_fill = 5`, Arm B
restored targeted majority (minimum 54.65%), but its Q11 block no longer
contained a locked monetary fact. Bare-span arms preserved targeted majority
when uncapped, but did not retrieve a locked art fact at either breadth probe
after exact serialization cost was enforced.

This was a policy-design failure, not an inference failure and not a failed
implementation.

## Direct answers

### Did the study fail?

Operationally, the planned 2x2 live factorial could not run. Scientifically,
the pre-run phase succeeded: it falsified the assumption that the four cells
could be compared safely at one calibrated `c_fill`, and it prevented four
full 121-turn runs plus invalid scoring work.

The correct label is **gated STOP**, not VALIDATED, PARTIAL, or a null model
result.

### What exactly failed?

No arm passed breadth and targeted preservation at the same integer cap:

| Setting | Breadth result | Targeted result | Joint result |
|---:|---|---|---|
| `c_fill = 1` | B reached 4/4 at both probes | B minimum own-domain share 11.48% | FAIL |
| `c_fill = 5` | B lost monetary coverage at Q11 | B minimum own-domain share 54.65% | FAIL |
| `c_fill = 50` | every arm missed 4/4 at one or both probes | all arms passed Gate 3 | FAIL |

Arm A and Arm C passed the targeted fixture at every registered cap but never
passed breadth. Arm D first passed the targeted fixture at 50 and still missed
art at both breadth probes. The feasible set was empty even under the weaker
interpretation that only one arm, rather than all four arms, needed to satisfy
both gates.

### Why did the feasible set become empty?

Three constraints interacted:

1. **The locked budget was already below the corrected episode frontier.**
   Gate 1 found the first episode-rendered 4/4 point at `B_ltm = 40,000`,
   `k_min = 2`. No tested `k_min` reached 4/4 at 32,000.
2. **The cap controlled record count, not information or character share.**
   One episode per topic can consume radically different character totals.
   Raising the cap lets global similarity reclaim the budget, but can displace
   a low-ranked fact-bearing episode during variable-size packing.
3. **Bare spans changed both carriage and economics.** They removed accidental
   whole-episode fact carriage, and their repeated provenance attributes made
   per-item overhead material. After accounting was corrected, C and D selected
   roughly 79-80 spans at the decisive probes but selected none from the locked
   art fact turns 55, 56, or 60.

The result is a Pareto conflict, not merely a poorly chosen scalar cap:
aggressive topic equalization helps breadth but damages targeted allocation;
relaxing it repairs targeted allocation but does not guarantee complete facts
from every topic.

### Was 32,000 characters simply too small?

For the original episode-rendered similarity policy, yes: the corrected replay
places the first observed 4/4 point at 40,000 characters with `k_min = 2`.

For every possible retrieval policy, no. Arm B proved that 32,000 characters
can contain at least one locked fact from all four domains at both probes. What
32,000 could not support was the registered policy's conjunction of breadth
and targeted safety.

Raising the budget is therefore a legitimate next-study control, not a valid
amendment to this study.

### Did span rendering work?

It worked as implemented, but bare spans did not solve the registered coverage
problem. The post-amendment span arms:

- stayed within exact serialized candidate cost;
- avoided accidental episode carriage;
- passed targeted majority when uncapped (Arm C minimum 52.45%);
- missed art facts at both breadth probes.

That is evidence against **bare span rendering as a sufficient intervention**.
It is not evidence that all span-based rendering is ineffective. The replay
supports testing a deterministic context-bearing unit, such as a selected span
plus a bounded source neighborhood.

### Did density ranking work?

Density changed which units were delivered and made Arm B's `c_fill = 1`
breadth pass possible. It did not create a jointly safe policy, and Arm D still
missed art facts at the breadth probes.

The mechanism-level interpretation is that entity-and-number density is not a
guarantee of complete rubric-relevant facts. P5 remains formally
**NOT ADJUDICATED** because no admissible live comparison was locked. The replay
is a warning about the proxy, not a scored causal verdict.

### Was Amendment 001 legitimate?

Yes.

The blocker appeared before ablation or live inference. Content-only charging
certified a 28,498-character Arm C selection while production rendering
delivered 83,106 characters. The amendment:

- corrected the measured quantity to exact serialized span-element cost;
- used the production renderer as the single serialization authority;
- changed no gate threshold, budget, prediction, or outcome criterion;
- preserved Arm A byte-for-byte;
- made passing harder rather than selectively rescuing an arm.

That is a good-faith interface correction, not outcome-driven criterion
softening.

### Was the STOP decision correct?

Yes. Continuing would have required at least one unregistered intervention:
more budget, character-based allocation, contextual span rendering, or a
formation change. Any of those would add a policy level or factor after seeing
the gate results.

The STOP is also robust to two audit findings:

1. Gate 3's harness required every arm to pass at one shared cap, while the
   preregistration's phrase "per arm" could be read more weakly. No individual
   arm passed both breadth and targeted gates anyway.
2. The report said "no `c_fill` from 1 through 50," while the registered harness
   sampled 13 values: 1, 2, 3, 4, 5, 6, 8, 10, 15, 20, 30, 40, and 50.
   A post-study exploratory audit evaluated every omitted integer from 1 through
   50. Only Arm B at 1 passed breadth, all-arm targeted passing began at 41, and
   no value produced either a global or per-arm joint pass. This audit confirms
   the decision but is not retroactively treated as preregistered evidence.

### Did the code fail?

No demonstrated code defect explains the STOP.

- Arm A reproduced both accepted Study 007 LTM blocks byte-for-byte.
- All 271 preserved Study 007 artifacts remained hash-identical.
- Exact span serialization cost is covered by a regression test.
- The leakage audit passed and its planted transitive violation was detected.
- The full suite passed 644 tests after the amendment.

The one implementation defect found, span cost accounting, was corrected before
the binding rerun. The corrected implementation still produced the empty
feasible set.

### What did Study 008 actually answer?

It answered:

- P1 is confirmed under the fact-aware criterion.
- Study 007's floor-inertness conclusion was an artifact of a weak coverage
  surrogate.
- Rendering-unit overhead must be charged when item count changes materially.
- A record-count fill cap cannot stand in for a character-allocation guarantee
  across variable-size rendering units.
- Bare spans plus the registered floor/fill policies do not jointly satisfy the
  breadth and targeted gates at 32,000 characters.

It did not answer:

- whether C or D would score better than A or B on generated answers;
- whether Q5 would lose credit under span rendering;
- which arm would have the highest breadth score;
- whether formation quality would regress in a live arm;
- any long-horizon or 1,000-turn endurance question.

P2 through P5 and Bars 0 through 3 must not be described as failed model
hypotheses. They were not evaluated.

## What should change next

Do not carry this 2x2 directly into a live Study 009. First establish an
admissible retrieval policy offline, then register the live comparison.

### Recommended feasibility study

1. **Use a character-based allocator.** Express the cross-topic floor and the
   query-relevant remainder in rendered characters or character shares, not
   records. Log requested and realized share per topic.
2. **Test a context-bearing span unit.** Render the selected span with a
   deterministic, bounded source neighborhood and charge its exact serialized
   form. Merge overlapping neighborhoods before charging.
3. **Include the simple budget control.** Replay episode rendering at 40,000
   characters and `k_min = 2`; Gate 1 says this is the strongest low-complexity
   baseline.
4. **Require per-policy joint feasibility.** A candidate advances only if that
   same policy passes breadth, targeted majority, top-item retention, and exact
   rendered-cost bounds.
5. **Use an independent holdout gate.** Q11/Q14 and the existing targeted
   fixture have now been used for diagnosis and parameter selection. Treat them
   as development evidence. Lock new breadth and targeted queries before
   calibration, and do not expose their fact labels to retrieval code.

The next policy should be selected on a Pareto table, not a single cap:
four-domain complete-fact coverage, minimum targeted character share, exact
rendered cost, and context-window count should all be reported.

## Practices to retain

- fact-aware coverage rather than planted-term coverage;
- exact rendered-unit accounting;
- read-only replay against preserved stores;
- byte-fidelity checks for carried baselines;
- structural leakage audits with planted violations;
- binding pre-run STOP rules;
- explicit separation between replay findings and live answer outcomes.

The most important result of Study 008 is methodological: the system now catches
a retrieval design that can look balanced in record counts while being
unbalanced in the characters and facts the model actually receives.
