# LV-004 — deterministic completion repair and live reader verdict

**Status:** `REGRESSES`  
**Registration commit:** `00ec348c`  
**Preflight commit:** `c6d00c6b`  
**Answer seal commit:** `3858352f`  
**Blind judgment seal commit:** `05ab2c9d`  
**Date:** 2026-08-26

## Result

TC-014 opportunity admission did not convert its offline availability advantage
into a live reader gain on the registered 16-question discordant population.
Full CC80 and opportunity each answered 5/16 items correctly. There was one
opportunity gain and one loss, for net zero.

The gain was targeted: opportunity recovered “What state did Nate visit?”
(`Florida`). The loss was breadth: full CC80 retained “How many screenplays has
Joanna written?” (`three`) while opportunity did not. Targeted therefore netted
`+1`, breadth `-1`, and other `0`. The locked breadth non-regression guardrail
makes the disposition `REGRESSES` despite the combined tie.

| Primary stratum | n | Gains | Losses | Net |
|---|---:|---:|---:|---:|
| Combined | 16 | 1 | 1 | 0 |
| Targeted | 9 | 1 | 0 | +1 |
| Breadth | 5 | 0 | 1 | -1 |
| Other | 2 | 0 | 0 | 0 |
| Offline opportunity gains | 11 | 1 | 1 | 0 |
| Offline opportunity losses | 5 | 0 | 0 | 0 |

The descriptive exact paired p-value is 1.0. Gold-string containment moved
`+2` with no losses, but it is only a cross-check and did not reverse sign
against semantic correctness. Both arms refused the category-5 adversarial
item in 5/5 replicates. Judges disagreed on 11/160 answers.

## Instrument validity

LV-002 stopped because the raw reader exposed thinking text and then because
its 192-token batch was not persisted before validation. LV-003 corrected
persistence and generated all 170 scheduled answers, but its registered gate
stopped on two balanced 512-token truncations.

LV-004 retained the 168 naturally stopped answers and regenerated only those
two exact prompt/seed records at 2,048 tokens. Both completed naturally and
reproduced their preserved 512-token response prefixes byte-for-byte. The
merged batch has 170/170 unique responses, zero truncations, and an unchanged
168-row complement. All 480 blind judgments completed with three judgments per
answer and zero truncations.

The breadth loss is the repaired question. Its arm majorities were 3/5 for full
CC80 and 2/5 for opportunity; each repaired response received unanimous blind
judge votes in that same direction. This makes continuation-length sensitivity
visible, but does not permit removing the registered loss or changing the bar.

## Interpretation boundary

The offline count improved because opportunity admission delivered required
evidence more often. Live, that extra availability changed only two item-level
reader outcomes and traded one targeted success for one breadth failure. On
this selected LoCoMo development subset, availability was not a reliable proxy
for answer improvement.

This is not an overall LoCoMo score, fresh-corpus confirmation, transfer result
or deployment test. It does not authorize replacing full CC80, enabling the
TC-014 opportunity arm in `episodic-chat`, or tuning against these answers.

## Sealed artifacts

- Repaired answers SHA-256:
  `639f789396807c89f3242bf9d4e2c05cbf5f349e444d5c1e38b54164c658aebe`
- Repairs SHA-256:
  `ec7c2b1c39b2e6260c8db8716725b5ab39529d78f2f79b7d4655be883be973dc`
- Blind judgments SHA-256:
  `011f07da14d4d026202abe4afed0c57c0149327cf4c6c66a69fa6096b201707e`
- Frozen prompts SHA-256:
  `c01cf11a5e2750c2ed8c03e90c813af7263de8a7fd2c4b78bacb72aa1207d5d8`
