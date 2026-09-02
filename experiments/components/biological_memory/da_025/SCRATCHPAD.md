# DA-025 Scratchpad

## 2026-08-30 - Result

- Blind preflight: 465 questions, 5,939 second-member attempts, 1,483
  second-member admissions, exact replay, zero calls.
- Complete delivery: DA-023 202 -> DA-025 211; 17 gains, 8 losses, p=.108.
- Registered disposition is `NO_LONGMEM_ATOMIC_ADDITION_SIGNAL`: zero-loss and
  every-type-nonnegative bars fail.
- The operation is useful: 15/20 wrong-member residuals are rescued. The order
  is unsafe: temporal reasoning is +1/-5.
- Preserve DA-023 exactly in the successor. Alternate members may consume only
  residual capacity after every DA-023 admission has been replayed.

