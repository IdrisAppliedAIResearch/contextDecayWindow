# NF-003 Part 1 — Is the Evidence Ranked Badly, or Not Similar At All?

**Status:** `PART 1 COMPLETE — H1 CONFIRMED AS DOMINANT, H2 RESIDUAL`
**Predecessor:** `../nf_002/NF_002_REPORT.md`
**Artifact:** `artifacts/part1_record.json`
**Corpus:** LongMemEval · 470 answerable items, 465 with turn-level flags
**Cache:** 106,877 hits, **0 misses** · **Model calls: 0**
**Date:** August 12, 2026

Nothing here is registered. `AGENTS.md` §9.4 applies: this exists to justify a
registration, not to be read as a result.

## 1. The two hypotheses

NF-002 changed the packing unit and left the ranking unit alone — episodes still
inherited their session's rank. 74 of 90 baseline misses survived every unit and
packing change, so the ranking was what remained.

- **H1, dilution.** A 13–23k character session holds one relevant episode; the
  session score flattens it against ~95% unrelated conversation.
- **H2, similarity failure.** The evidence episode never resembled the query, so
  no unit change helps and the metric is the limit.

The discriminator was fixed in advance and is not "try it and see": the **cosine
rank of the true evidence episode**, identified by LongMemEval's own
`has_answer` turn flag.

## 2. Discriminator result

| set | n | best evidence episode rank (median) | p90 | episodes/item |
|---|---|---|---|---|
| NF-002 A1 already delivers | 396 | **2** | 44 | ~229 |
| **NF-002 A1 misses** | **69** | **41** | **155** | ~228 |

On items the previous arm already reached, the evidence episode ranks **2nd of
~229**. On the misses it ranks **41st**, and only 30% are in the top 20.

Both hypotheses are live, in that order:

- **H1 dominates.** Evidence that session-level ranking buried sits near the top
  of an episode-level ranking. The dilution was real and large.
- **H2 is a genuine residual.** On the hard tail the evidence is deep even at
  episode granularity, so a third of the misses are not a unit problem.

## 3. What the change is worth, measured like-for-like

Same 32,000-character budget, same skip-on-overflow packing, same session-level
evidence definition. Only the **ranking unit** differs.

| arm | ranking | any-evidence |
|---|---|---|
| A1 (NF-002) | session-inherited | 396/470 (84.3%) |
| **B1** | **episode cosine** | **445/470 (94.7%)** |
| paired | | **49 gains, 0 losses**, p < 0.00001 |

**Zero losses.** TA-001 died at 2 gains against 6 losses and SR-001 at 0 against
2; NF-002 carried 6 losses. This arm has none, and NF-002's single harmed
stratum disappears with it.

## 4. A measurement error, caught and recorded

The first pass reported this comparison as **351 against 396 — a large
regression** — and it was wrong. `has_answer` marks evidence *episodes*;
NF-002's measure counts evidence *sessions*. Comparing one against the other
made a 49-item gain look like a 45-item loss.

This is the unit-mismatch failure the program has recorded repeatedly, and it
appeared here inside the study whose whole subject is units. `pack()` now
returns both measures and the report states which is which.

## 5. The loss sub-hypothesis is refuted

NF-002's six losses were all in `single-session-assistant`. The proposed
explanation was that its evidence episodes are long and get skipped on cost.

| stratum | median evidence-episode chars | median evidence rank |
|---|---|---|
| **single-session-assistant** | **1,358 — the shortest** | **1 — the shallowest** |
| knowledge-update | 2,769 | 2 |
| multi-session | 2,862 | 3 |
| temporal-reasoning | 2,764 | 6 |
| single-session-user | 2,340 | 8 |
| single-session-preference | 2,640 | 7 |

Exactly backwards: that stratum's evidence is the shortest and the best-ranked
in the corpus. The proposed mechanism is wrong, and under B1 the losses vanish
anyway, so the question it was asked about no longer exists.

## 6. What remains

25 of 470 items are still missed with episode-level ranking. Their evidence sits
deep in an episode-level cosine ordering, which is H2's territory and is not
reachable by any unit or packing change. That is where a similarity or
composition mechanism would have to earn its place.

## 7. Standing, and the constraint

This is **unregistered exploration** on a corpus that can no longer confirm
anything. Every LongMemEval item has now been used by this program, and NF-002
already recorded a deviation for exactly this. A registration written now
inherits that ceiling: it can characterize, not confirm.

The effect is large enough — 49 gains, 0 losses, p < 1e-5, zero model calls —
that characterization is still worth having. But the honest next step is two
tracks in parallel: register and run this properly for the record, and acquire
a corpus this program has never touched so something in this line can finally be
confirmed.
