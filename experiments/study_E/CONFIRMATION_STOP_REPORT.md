# Study E confirmation: registered completeness stop

2026-09-06. Registration: **2e047c41c80748b16f0e6df15dcc70ac54145598**.

**INSTRUMENT STOP — no reader or mechanism verdict.** The456th physical call ended at the8192-token cap with `stop_type=limit`. The API's `truncated` field was false, but the non-EOS stop and predicted-token count triggered the registered cap rule. All455 prior calls reached EOS, including three calibration calls. The original schedule has3508 physical calls for3840 logical answers;3052 physical calls remain unissued.

All456 returned responses were persisted and preserved in a lossless gzip archive, with raw and archive hashes in [stop_audit.json](artifacts/confirmation/reader/stop_audit.json). There is no uncertain pending call. The dedicated server was stopped after executable/port verification. No inference was retried, cap changed, correctness scored, or confirmation mechanism comparison opened.

This stop says the output-completion instrument did not finish the registered population. It says nothing about whether the ordering policy improves answers. The amended development findings remain unchanged and cannot substitute for the unfinished confirmation result.

The same-study [Amendment004 draft](amendments/AMENDMENT_004_output_cap_continuation_DRAFT.md) proposes one bounded common-cap continuation with exact calibration and capped-response prefix checks. It is awaiting authorization; no continuation code or calls have been made. The locked registration specifically disallows automatic cap increases.

Raw stop artifacts committed at98bf6e14. README, AGENTS, memory and PR95 record the stop. ERRATA is unchanged because no prior published result changed. No merge, adoption or deployment.
