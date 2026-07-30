# AS-001 - Q4 Packing Re-Analysis

**Type:** Offline artifact analysis. **Not a study.** No inference run, score,
or confirmatory claim.
**Repository:** `contextDecayWindow`
**Branch:** `analysis/q4-packing`
**Status:** LOCKED by the commit that first adds this file
**Date:** 2026-07-29
**Dependency:** DR-001 complete with G-R1 and G-R2 PASS

## 1. Question

The corrected retrieval bakeoff's widened-STM arm lost one point to Study 009
Arm L, entirely at Q4. The four Q4 identity facts were planted at turn 55 and
probed at turn 115. The turn-55 episode was N rank 27 of the N cap 32, but only
15 N episodes fit the historical 60,595-character payload. Its query cosine was
0.16612689197063446, below the registered K threshold 0.48.

This analysis asks whether DR-001's compact, exact-cost renderer makes the
turn-55 episode available under the unchanged N-first packing policy. It
distinguishes structural packing exclusion from a live primacy mechanism.

## 2. Locked Inputs

The analysis uses only committed artifacts:

- corrected Tier 6 turn-115 context-match row and run database;
- corrected Tier 6 Q4 exclusion trace;
- Study 009 Q4 measurement key;
- Tier 6 context-match settings;
- DR-001 compact renderer and re-derived budget sweep.

Before analysis, verify that the corrected run's canonical git blobs match its
committed mechanism seal. Checkout byte hashes may differ under Git's Windows
line-ending conversion; this is not accepted as source mutation or as a seal
pass. The committed blob content is authoritative, and parsed checkout content
must equal the canonical blob after newline normalization.

Locked constants:

| Quantity | Value |
|---|---:|
| Probe turn | 115 |
| Primary plant turn | 55 |
| Age at probe | 60 turns |
| Turn-55 N rank | 27 |
| N cap | 32 |
| Historical fitted N episodes | 15 |
| Historical payload budget | 60,595 chars |
| Turn-55 cosine | 0.16612689197063446 |
| K threshold | 0.48 |
| Point-estimate `B_ltm` | 32,000 chars |
| Sensitivity sweep | 16k, 20k, 24k, 28k, 32k, 36k, 40k, 48k, 64k |

## 3. Method

1. Load the 32 committed turn-115 N candidates in their preserved packing
   order. Record identity, rank, cosine, source turn, source user/assistant
   content, and historical serialized length.
2. Assert 32 unique candidates, rank continuity 1-32, and turn 55 at rank 27.
3. Serialize each candidate with DR-001's compact renderer. Do not alter source
   content, candidate order, N, K, floor/fill, containment, or selection.
4. Re-run the unchanged prefix-style N-first packing at 32,000 characters.
   Charge the exact enclosing block, separators, and episode elements.
5. Record fitted count `S'`, selected identities, serialized characters,
   source-content characters, whether rank 27 enters, and margin `S' - 27`.
6. Repeat exact packing over the locked sensitivity sweep and record the first
   budget at which rank 27 enters.
7. If turn 55 is delivered, verify availability of all four Q4 identity facts
   by case-insensitive string presence in the serialized payload:
   `Annunciation`, `Melozzo da Forli`, `Cardinal Giuliano della Rovere`, and
   `1483`.

Fact presence establishes availability only. It does not claim the model would
answer correctly, and no score is changed.

## 4. Binding Decision Rule

Apply the first matching branch after opening the point estimate and
sensitivity results:

| Branch | Mechanical condition | Verdict and next action |
|---|---|---|
| A | `S' >= 29` at 32k | `RENDERING NULL CONFIRMED`. Do not run a primacy study. |
| B | `S'` is 27 or 28 at 32k | `BORDERLINE`. Escalate before any inference or architecture decision. |
| C | Rank 27 is absent at 32k but enters at an achievable budget in the locked range | `BUDGET/PACKING`. The exclusion is allocation-sensitive; do not claim a primacy mechanism. |
| D | Rank 27 does not enter at any budget in the locked range | `PRIMACY MECHANISM LIVE`. A separately pre-registered CC-001 pinned-set study may be proposed. |

The branch is determined by fitted episode count and identity, not by a derived
ratio or narrative judgment.

## 5. Integrity and Surrogate Audit

- A larger fitted count can hide identity changes; require exact ordered
  candidate and selected-identity manifests.
- Rank 27 can fit while one or more facts are absent; require all four string
  checks before declaring Q4 available.
- Character reduction can remove content; report source-content and serialized
  characters jointly and require source round-trip equality.
- A single 32k result can hide budget sensitivity; the complete locked sweep is
  mandatory.
- A seal file can appear valid while checkout conversion changes bytes; verify
  canonical git blobs and normalized parsed content separately.

## 6. Prohibitions

Do not change ranking, N, K, thresholds, packing order, floor/fill policy,
containment, source content, scores, or committed run artifacts. Do not run
inference. Do not infer answer correctness from availability. Do not begin a
primacy study from Branches A-C.

## 7. Deliverables

- [ ] Canonical source-seal verification.
- [ ] Candidate manifest with pre/post serialized costs.
- [ ] Exact 32k packing result with `S'` and rank-27 margin.
- [ ] Complete 16k-64k sensitivity frontier.
- [ ] Four-fact availability check when applicable.
- [ ] Mechanical branch verdict.
- [ ] Analysis report and memory update.
- [ ] `README.md` and `AGENTS.md` updated in the same PR.
- [ ] `ERRATA.md` updated only if Branch A changes the bakeoff conclusion.
- [ ] Independent analysis PR, stacked on DR-001 until it merges.
