# NF-004 Report - LoCoMo Ranking Granularity Confirmation

**Status:** `WORKS - CONFIRMED AVAILABILITY DIRECTION`
**Pre-registration:** `95f0d25c8e898998dcbf0c8b95d370896c57c929`
**Rebase amendment:** `AMENDMENT_001_pr56_rebase_anchor.md`
**Corpus:** six sealed LoCoMo conversations
**Primary population:** 1,098 fully resolvable canonical QA records
**Budget:** 16,000 candidate-text characters
**Model calls:** 0
**Embedding calls during measurement:** 0
**Date:** August 13, 2026

## Result

NF-004 confirms its registered, corpus-specific availability prediction. Pair
ranking raises complete exact-evidence delivery from **843/1,098** under
session-score inheritance to **935/1,098**. The paired result is **140 gains,
48 losses, 910 ties**, net +92, gain/loss ratio 2.92, and one-sided exact
binomial p = **6.19e-12**.

The registered `WORKS` bar required gains at least twice losses and p <= .05.
Both conditions pass. This confirms the LoCoMo direction at the registered
16k operating point. It does not supersede LongMemEval's opposite
characterization, establish a universal ranking rule, or show that a reader
answers more questions correctly.

| Arm | Complete evidence | Any evidence |
|---|---:|---:|
| `S_SESSION_RANK` | 843/1,098 | 950/1,098 |
| `P_PAIR_RANK` | **935/1,098** | **1,027/1,098** |
| Source order | 258/1,098 | 352/1,098 |

The source-order control remains far below both ranked arms, so the result is
not a slack-budget artifact. At the registered 16k budget, median packed
characters are 15,986 for session ranking and 15,988 for pair ranking.

## Gates

| Gate | Result | Evidence |
|---|---|---|
| G0 registration identity | PASS | locked LF SHA-256 and first commit `95f0d25c` |
| G1 source and population | PASS | exact corpus hash; 1,104 arm inputs and 1,098 primary keys |
| G2 leakage | PASS | evidence-blind mechanism import graph; planted forbidden import rejected |
| G3 vector seal | PASS | 2,749/2,749 read-only hits, zero misses; exact model/file/content seal |
| G4 development reproduction | PASS | 16k 702/773 with 104/33; 32k 773/826 with 71/18 |
| G5 determinism | PASS | two complete development replays byte-identical |
| G6 holdout run | PASS | one sealed 1,104-row artifact; 1,098 primary rows |
| G7 result integrity | PASS | totals recomputed; holdout replay byte-identical |

The first preflight attempt stopped at G1 before G2-G5 because the
implementation compared the source manifest's raw bytes with an LF-normalized
constant. No preflight artifact or holdout outcome existed. Commit `5a4f7327`
corrected the artifact identity mode, added a regression test, and the full
ordered preflight then passed.

## Secondary Results

All six holdout conversations are net positive for pair ranking. Their nets
are +7, +6, +13, +30, +15, and +21. All five source categories are also net
positive, although these subgroup results were not registered to set the
disposition.

At 32k, complete evidence remains positive: **961/1,098** for session-score
inheritance and **1,024/1,098** for pair ranking. The primary direction is
therefore not confined to the 16k point, but no secondary budget can alter the
registered verdict.

Pair ranking moves evidence materially earlier in the order. Median best
evidence rank is 2 under pair ranking versus 9 under session-score inheritance;
p90 is 34 versus 80. This is descriptive mechanism evidence opened only after
the primary artifact and disposition were committed.

## Interpretation

LongMemEval and LoCoMo now carry opposite, correctly scoped findings. On the
exhausted LongMemEval corpus at 32k, session context rescues answer episodes
whose own cosine ranks too deeply, yielding the characterized rule `rank
coarse, pack fine`. On the prospectively registered LoCoMo holdout at 16k,
pair-level ranking instead improves complete evidence availability by 92 net
items. The development controls already rejected delivery fraction as a
portable scalar moderator, and NF-004 confirms that corpus-specific scope
rather than restoring a universal rule.

This remains an availability instrument. Complete annotated evidence can be
delivered while a reader fails, and LoCoMo's evidence annotations may be
insufficient for some answers. No live reader, production promotion, or
adoption is authorized by this result.

## Integrity Trail

| Artifact | Commit | SHA-256 |
|---|---|---|
| implementation | `cb4931c5` | source committed before vector capture |
| holdout vector manifest | `10ee75cd` | `c5436e00c44da69618c9b84abbfe882d1d6d3c42f94fd17a803414ed17f08c0a` |
| G0-G5 preflight | `0df2b9e3` | `da7e0bf87b49bf0a2cf9a45f831cd4a3265d76a6432670616512d008aac562cd` |
| G6 sealed outcomes | `131de562` | `7be2668d21163c9380ac0e6d27776e8fbfa0b80ae3342a478040e51b556e48cc` |
| G7 integrity result | `7a1f82f1` | `890b4831d530e9a7df7a7d8391badbe9c9f717676daeb5b4ff0226602b26f21b` |

The G7 replay SHA equals the committed G6 SHA exactly. The cache database is
retained locally and ignored by Git; its manifest binds file SHA-256
`96656024f79a360` and canonical content SHA-256 `2e73bff9178d054e`.
