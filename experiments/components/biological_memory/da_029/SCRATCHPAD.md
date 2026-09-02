# DA-029 Scratchpad

## 2026-08-30 - Registration

- Audit the exact 9 NF and 42 LongMem residuals after DA-028.
- Locked classes separate conjunction, wrong member, initial compact size and
  prior compact consumption; no category may be inferred from labels alone.
- Dominance requires >=60% within corpus. Shared successor requires the same
  dominant class in both.
- Zero model, embedding and cache calls. Diagnostic only.

## 2026-08-30 - Result

- Exact replay classifies all 9 NF and 42 LongMem residuals with zero
  unaccounted cases.
- NF: prior compact consumption 5, wrong frozen member 3, conjunction 1. No
  class reaches the locked 60% dominance threshold.
- LongMem: wrong frozen member 24, prior compact consumption 10, conjunction 5,
  initial compact size 3. No class reaches 60% (wrong member is 57.1%).
- No shared dominant successor. The strongest composable signal is protected
  atomic completion after the full DA-028 pack: it targets 27 wrong-member
  cases without altering compact codec selection or strongest order.
- Remaining prior-consumption cases require a later dependency representation,
  not another local substitution score.

