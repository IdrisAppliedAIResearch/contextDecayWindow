# Study E current status

Updated2026-09-06. **Authorized cap-repair preflight running.** Amendment004 is committed at1019f3e2. The output allowance is16384tokens; model context, thinking behavior and other reader settings remain unchanged. The original452EOSmeasurement responses are preserved. Two new calibration responses match each other and the originals; the single capped-response repair is running.

The remaining3052calls can resume only after the repair reachesEOS and matches the original capped response's exact prefix. Any new cap or identity failure stops this bounded repair. No confirmation correctness or mechanism comparison has been opened.

The requested read-onlyGPU sample showed97%median utilization andabout19.9GiB VRAMallocated. SpareVRAM warrants a controlledbatchingbenchmark; no batching was applied to this scoredrun. SeeGPU_UTILIZATION_NOTE.md.
