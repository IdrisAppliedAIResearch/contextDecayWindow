# DA-024 Scratchpad

## 2026-08-30 - Registration

- DA-023 reaches NF 976/986 and LongMem 202/250 one-hop ceilings.
- Audit exactly 10 NF and 48 LongMem reachable residual misses.
- Locked classes: multi-pair conjunction, wrong frozen member, initial
  backreference size, prior additive consumption, unaccounted.
- Initial/arrival costs replay DA-023 exactly; evidence-aware member alternatives
  are diagnostics only. Dominance requires >=60% within corpus.
- Zero model, embedding and cache calls. No intervention/adoption authority.

## 2026-08-30 - Result

- All 58 residuals classified; no unaccounted class.
- NF: prior consumption 7, wrong member 2, conjunction 1. Prior consumption
  dominates at 70%. Initial/arrival slack p50 1,015/88 vs required cost 123.
- LongMem: wrong member 20, prior consumption 17, initial size 6, conjunction 5.
  Mixed by locked 60% rule. Initial/arrival slack p50 611/247 vs cost 272.
- No shared successor. Follow LongMem wrong-member with additive atomic fallback;
  NF needs whole-additive-pack allocation while preserving baseline.
- Artifact SHA `22225c9563bf82b12a9a9804d75e227722242148f9f7454420afc0619046d771`.

