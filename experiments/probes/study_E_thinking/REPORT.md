# Thinking-on probe of Study E complete-evidence errors

2026-09-06. Plan anchor **c6b955d3**, native-template characterization **72417c2b**. **Exploratory: 12/12 previously wrong answers became correct; zero remaining wrong finals in this sample.** Study E's registered scores are unchanged.

The 243 complete-evidence wrong C1 answers represent 97 distinct questions across five seeds. This small probe selected three distinct questions per before condition, taking the lowest content identities and the lowest originally failed seed for each. It reran twelve cases, not all243. Each retained its original evidence, question, reference, sampler and failed seed, using the native thinking-on configuration. No retrieval or source-generation call was made.

| Case | Condition | Thinking off | Gold / thinking on |
|---|---|---|---|
| Harbor-292 | Straight | depot | hangar |
| Harbor-113 | Straight | annex | studio |
| Harbor-170 | Straight | warehouse | office |
| Orchard-186 | Irrelevant change | depot | hangar |
| Orchard-657 | Irrelevant change | depot | hangar |
| Orchard-219 | Irrelevant change | office | hangar |
| Meadow-637 | Future update | hangar | depot |
| Meadow-792 | Future update | depot | annex |
| Meadow-455 | Future update | depot | hangar |
| Riverside-755 | Unaccepted proposal | workshop | annex |
| Riverside-544 | Unaccepted proposal | workshop | studio |
| Riverside-152 | Unaccepted proposal | annex | depot |

## What the emitted thinking shows

The traces consistently identify the review's source turn, search for the latest effective location change before it, and retain that location across no-change events. Future announcements and unaccepted proposals are explicitly rejected as effective changes. These are observations of the emitted trace, not proof of its causal faithfulness.

Three examples, with the relevant records verified in the unchanged delivered context:

- **Harbor-170:** turn50 says warehouse, turn51 replaces it with office, turns52–58 make no change, review59 follows. The old answer was warehouse. Thinking-on explicitly locates the office update and retains it through the intervening reviews; final answer office.
- **Meadow-792:** turn73 says depot, turn74 replaces it with annex, turn78 announces office for next month and explicitly says it is not effective, review81 follows. The trace says, “This is a future change not effective now.” It then selects annex rather than the old depot answer or future office.
- **Riverside-152:** turn58 says annex, turn59 replaces it with depot, turn62 proposes annex but says no change takes effect, review64 follows. The trace says, “Turns 60-63 no change. Thus immediately before review at 64, location was depot.” The prior answer was annex; the new final is depot.

For the twelve final decisions, the identified update, anchor and relevant qualifiers agree with the supplied records. There are no residual wrong finals to locate a failure step for. This is not a claim that every intermediate sentence or enumeration was independently audited; the case analysis records the decision-relevant reasoning. Original short wrong answers do not expose why they were wrong, so we cannot claim the thinking-off reader definitely skipped a record or used a particular faulty rule.

The narrower implication is useful: **these twelve failures were recoverable by the same model with the same evidence under the native thinking-on configuration**. They do not demonstrate a persistent inability to use that evidence. The frequent choice of an earlier location in the old answers suggests a state-selection problem worth investigating, but its precise cause is unidentified.

## Runtime and measurement limits

Native thinking-on adds a system message asking for careful reasoning and opens the thinking segment. The original boundary-only assumption failed during preparation; no answers were generated in that attempt. The exact native prefix was recorded before proceeding. Off rendering reproduced all twelve prior prompts byte-for-byte, and each required source fragment survived in the on prompt. Consequently this tests the **native thinking-on configuration**, including its system prefix; it does not isolate extra computation from prompting.

All twelve case calls and two unscored calibration calls completed. The two arithmetic calibrations produced byte-identical thinking and final answers. Case generation totaled **149.96 seconds**, with **335–740 output tokens** and **9.59–16.28 seconds per case**. Full thinking and finals are preserved. Context32768, outputcap16384, cachefalse, one slot, same pinned model/executable/libraries. No cap changes, uncertain calls, retries or incomplete answers. Dedicated server24108 was verified and stopped.

Completeness/raw captures were committed at **f8e98aab** before scoring. All twelve finals matched the frozen Study E canonical grammar; no semantic judgment exceptions were needed. Final scores were committed at **cf3bc6ef** before thinking inspection. Single-agent diagnostic interpretation is not human or independent multipass audit.

Selection conditioned on prior failure, with one matched seed per question and no fresh thinking-off rerun. Thus 12/12 is a recovery count for this selected sample, not an unbiased causal effect, a population accuracy estimate, or evidence that all243 errors will disappear. The remaining85 distinct failed questions were not probed. Study E's registered reader verdict stays specific to its thinking-off configuration. No adoption, merge or new retrieval design follows automatically.

Preflight evidence: committed [input gate](artifacts_v2/input_gate.json), [gate-order fixture](artifacts_v2/gate_order_fixture.json), [parser fixtures](artifacts_v2/parser_fixtures.json), [calibration gate](artifacts_v2/calibration_gate.json) and [completion gate](artifacts_v2/complete.json). See [all twelve cases with full emitted thinking](CASES.md), [machine-readable case analysis](artifacts_v2/case_analysis.json), [final scores](artifacts_v2/final_scores_mechanical.json) and [result](artifacts_v2/result.json). The earlier `artifacts` directory preserves the pre-answer template stop; `artifacts_v2` owns the completed probe.
