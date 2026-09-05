# DA-032 Scratchpad

## 2026-08-30 - Registration

- Audit exact 3 NF and 39 LongMem residuals after DA-031.
- Recompute class at varint initial/arrival state and separately record whether
  required evidence fits after the complete protected pack.
- Dominance >=60%; shared successor requires same dominant class.
- Zero model, embedding and cache calls. Diagnostic only.

## 2026-08-30 - Result

- All 3 NF and 39 LongMem residuals classify with zero unaccounted cases.
- NF: 3/3 wrong frozen member, but 0/3 required members fit after the complete
  protected pack. Median postpack slack 9 chars vs median cost 108.
- LongMem: wrong member 21, prior varint consumption 12, conjunction 5,
  initial varint size 1; 17/39 required materializations fit postpack.
- No shared successor. LongMem supports protected atomic completion after
  varint. NF requires at least roughly another 100 chars of exact representation
  capacity before the same operation can be protected.

