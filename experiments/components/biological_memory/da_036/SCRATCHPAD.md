# DA-036 Scratchpad

## 2026-08-30 - Registration

- Audit the exact 28 LongMem reachable misses remaining after DA-033.
- Replay the immutable DA-031 sequence and all DA-033 atomic attempts before
  using evidence to classify the remaining dependency boundary.
- No intervention, model, embedding or cache calls.
- A successor may only add protected evidence-blind material after the frozen
  DA-033 order; it may not displace or reorder protected evidence.

## 2026-08-30 - Result

- All 28 residuals classify with zero unaccounted cases and byte-identical
  replay.
- Initial atomic size dominates: 18/28 (64.3%). Nine are prior atomic
  consumption and one is a multi-carrier conjunction.
- No required member fits after the complete DA-033 pack. Final slack is only
  23 chars median, while the finite missing-member cost is 253 chars median.
- The next justified operation is a stronger exact representation under the
  same protected order, followed by the same evidence-blind atomic tail.
