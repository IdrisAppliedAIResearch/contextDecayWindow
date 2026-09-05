# DA-044 Scratchpad

## 2026-08-30 - Registration

- Keep the 16k DA-038 prompt immutable.
- Materialize the fixed first 32 dependency nodes in a separate <=16k page.
- Charge and report every added character; use no score or evidence label.
- Measure exact evidence delivery only. Zero calls.

## 2026-08-30 - Result

- Blind pages are canonical and prefix-only, with p50 14,817 chars but only
  seven nodes; early payload size prevents the planned depth 32.
- Delivery rises 232->237: 5 gains, 0 losses, p=.0625. This meets only the weak
  bar; multi-session and temporal residuals gain nothing.
- Population cost is 6,541,247 auxiliary chars, or 1,308,249 chars per gain.
- This is inefficient token flooding. Close fixed pages and test node-wise
  replacement: bounded peak capacity with explicit cumulative traversal cost.
