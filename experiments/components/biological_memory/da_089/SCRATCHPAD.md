# DA-089 Scratchpad

## 2026-08-31 - Registration

- Blind population: all 8,055 sealed DA-042 frontier targets.
- Prompt membership: sealed DA-078; first frozen baseline parent edge.
- Fixed DA-088 routes and renderers; no child fallback or in-study repair.
- Exact <=2,048 replaceable frames; zero DA-078 mutation.
- No evidence labels, scores, thresholds, model, embedder, or cache calls.

## 2026-08-31 - Pre-analysis Clarification

- Exact members already present in stronger DA-078 use `PROMPT_MEMBER` with
  zero frames; this closes an otherwise undefined control-overlap case.

## 2026-08-31 - Result

- Complete: 4,556/8,055 (56.56%); zero DA-078 mutation.
- Failures: 2,701 full-child overflow, 798 anchored-slice overflow.
- Assistant members dominate: 2,672 and 732 failures respectively.
- Overflow deficits p50: 488 full-child, 1,454 anchored.
- Next signal: exact fixed packet fallback for overflowing source components.
- Byte-identical replay; zero calls.
