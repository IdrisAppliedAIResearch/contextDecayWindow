# Study E current status

Updated 2026-09-06. **Thinking-off restart authorized under Amendment 005 (6603aca3).** Amendment 004's repair exhausted the doubled 16,384-token cap. Both stopped attempts are preserved and will contribute no answers to the new run.

The native thinking-off template passed calibration. Serial/two/four-slot tests completed 48 development calls; each 16-call workload took 65.18/67.21/67.67 seconds. Batching changed one response and was slower, so serial was selected under runtime lock36e2347c. Fresh confirmation is running after input lock59e7cc8c: 3,508 physical calls, 3,840 logical answers. Both longest-prompt calibration responses match. The original confirmation population, retrieval and efficacy criteria are unchanged. No confirmation correctness or mechanism comparison has been opened.

The previous GPU sample showed 97% median utilization and about 19.9 GiB allocated VRAM. The bounded batching benchmark now tests whether the memory headroom produces faster reproducible execution. Its artifacts live in `artifacts/amendment005`.
