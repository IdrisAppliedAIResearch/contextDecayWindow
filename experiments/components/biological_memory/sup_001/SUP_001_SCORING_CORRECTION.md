# SUP-001 Scoring Interpretation Correction

**Date:** August 11, 2026
**Authority:** Program-author direction
**Scope:** Interpretation only
**Status:** `FACTUAL PASS - BYTE-IDENTITY CRITERION WITHDRAWN`

## Correction

The donation answer `$35.00` is factually equal to the expected `$35`. It is a
correct unchanged value. Integer and decimal renderings of one numeric value do
not become different facts merely because redundant zeroes are present.

The unchanged raw answers therefore support these factual totals:

| Arm | Correct total | Current | Unchanged | History | Regressions |
|---|---:|---:|---:|---:|---:|
| C0 | 8/9 | 3/4 | 4/4 | 1/1 | - |
| T1 | 9/9 | 4/4 | 4/4 | 1/1 | 0 |

C0's other nonmatching row adds terminal punctuation to a nonnumeric answer.
It is unaffected by this correction. T1 has no other nonmatching row.

## Integrity Treatment

This record does not edit the locked pre-registration, run lock, raw reader
outputs, historical scorer, tests, or committed score artifact. Those files
remain the provenance of the original byte-identity measurement. The
byte-identity result is not authoritative for factual correctness.

Because the result was already visible, this correction does not claim that a
different rule was preregistered. It withdraws an invalid factual surrogate and
records the successful value-level result transparently.

## Future Scoring Contract

Every future pre-registration containing quantitative answers must lock a
deterministic value comparator before any result is opened. At minimum:

1. Exact text remains accepted.
2. Integer and finite decimal forms are equivalent when their mathematical
   values are equal.
3. Sign, unit or currency marker, and surrounding factual text must agree.
4. The comparator does not infer unit conversions, percentages, dates, times,
   ranges, or semantic paraphrases unless separately preregistered.
5. Ambiguous expressions fail closed and require the registered adjudication
   path.

This is a specification requirement. No executable comparator is implemented
by this correction.

## Preserved Inputs

- Raw C0 SHA-256:
  `d99b0f72708801a56689ac05e56b773f23dd805068dcfac783b97f686c0f832c`
- Raw T1 SHA-256:
  `9b0f28cc6ad700e9c563eae0fd80051134da768840dcef287e3f8c9a4b931589`
- Sealed key SHA-256:
  `23bf2df2fddcc115091cf0f69a23b724b7d250c425513615f8c84ae634cb64d2`
- Historical score SHA-256:
  `611fffe348ce8ac4061104ef452d033f6eb0c87075ea04ab466189a6a96499bf`
