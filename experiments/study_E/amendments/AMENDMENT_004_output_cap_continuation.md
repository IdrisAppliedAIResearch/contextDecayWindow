# Amendment 004: authorized bounded output-cap continuation

2026-09-06. **AUTHORIZED.** The user approved the proposed output allowance increase: "Sure, you can extend context." In the preceding exchange this refers to the common 16,384-token output cap, retaining the 65,536-token model context and thinking behavior. Same Study E, same population and PR. Do not alter the locked registration or original capture.

## Trigger

Registered confirmation stopped at physical call456/3508: one response ended with `stop_type=limit` at8192 predicted tokens. The preceding455 calls reached EOS (three calibration and452 measurement). The capped response was persisted; no uncertain pending journal remains. No correctness or confirmation mechanism comparison has been opened. Stop audit and lossless raw archive were committed at98bf6e14. There are3052 unissued original physical calls.

The registration explicitly prohibits automatic cap increases and requires a separately authorized continuation amendment. This amendment authorizes that repair; it does not claim that a larger cap will make the model finish.

## Authorized change

Use a **common16384-token output cap** for the confirmation population. Keep the model, prompt, source corpus, query/arm/seed schedule, aliases, sampler settings, retrieval budgets, scorer and numerical decision bars unchanged. Preserve the original completed responses; do not selectively rerun an incorrect answer or change a source. All scored logical observations remain included.

Reuse the452 measurement responses already completed at EOS. The only changed stopping condition is the maximum output allowance; these responses stopped naturally below the old allowance. Disclose reuse across cap settings as an instrumentation amendment. Do not describe this as a wholly fresh run at16384.

Before further measurement, verify all frozen input/runtime hashes and that every prompt plus16384 fits65536 context. Start the identical one-slot runtime with new process/log records. Repeat the original maximum-prompt calibration twice at the new cap: require the two responses to match each other and the original maximum-prompt calibration by exact final-response bytes. Keep calibration unscored.

Make **one** request for the previously capped physical identity, with identical full prompt and seed and the new common cap. Require its returned content to begin with the exact UTF-8 content bytes of the original capped response. Require nonempty EOS completion with no new truncation or unfinished tagged reasoning. Preserve both responses. If prefix identity fails or it again hits the cap, stop the instrument; no further retry, cap escalation or population verdict under this amendment.

If the capped response completes and prefix identity passes, continue the3052 previously unissued physical calls in the original order at the same new common cap. No repeats of completed measurement calls. Any new cap, non-EOS, timeout, empty or unfinished response stops under the original completeness rule. Preserve uncertain journals; do not retry.

## Records and gates

Commit the authorized amendment in a design-only commit before implementing this continuation. Use a new continuation directory; original artifacts remain immutable. Freeze an additive schedule manifest listing the452 reused EOS measurements, the single prefix-checked repaired identity, the3052 unissued identities, and all3840 original logical aliases. No change to logical membership or reference values.

Commit new runtime/tokenizer/prefix gates before accepting the repaired population. Persist every returned response immediately and archive exact bytes. On full completion, create an auditable combined physical-response index with one selected completed response per original measurement identity and explicit provenance to original/repaired/new captures. Commit combined completeness before scoring; all resolved blind scores before any mapping or mechanism comparison. Calibration and the original capped prefix are never separately scored.

PF1: frozen hashes and all original identities preserved. PF2: same retrieval/model/prompt, only output stopping allowance changes. PF3: authorization/design commit before code/calls; prefix/completeness before scoring. PF4: new cap fits the largest12042-token input; feasibility is not a guarantee of EOS. PF5: original physical/logical content identities retained. PF6: exact calibration and capped-response prefix checks. PF7: no feedback or response writeback. PF8: same140-record inputs. PF9: no correctness-based selection or cap tuning; disclose cross-cap EOS reuse. PF10: no verdict until the entire logical population is complete and scored.

This is one bounded repair within Study E. If it fails, preserve the instrument stop and return for a new decision rather than silently trying another allowance.
