# NF-003 Three-Arm Finding - Rank Coarse, Pack Fine

**Status:** `CHARACTERIZED ON EXHAUSTED LONGMEMEVAL`
**Disposition:** descriptive synthesis; no posthoc registered verdict
**Artifact:** `artifacts/three_arm_summary.json`
**Artifact SHA-256:** `4473c8c5c4ed5337f912b6de665bb131d7cb3a00bc38cd67502be5572a16c1b6`
**Source artifacts:** immutable NF-002/003 records only
**Model calls:** 0
**Embedding calls:** 0
**Date:** August 13, 2026

## 1. Result

The strict audit contains three arms on the same 465 turn-labelled items, with
the same 32,000-character budget and skip-on-overflow policy:

| Ranking unit | Packing unit | Strict answer-episode delivery |
|---|---|---:|
| Session | Whole session | 375/465 |
| **Session** | **Episode** | **388/465** |
| Episode | Episode | 351/465 |

Moving one lever at a time gives opposite signs. Finer packing at the fixed
session ranking gains 17 and loses 4, a net **+13**. Finer ranking at the fixed
episode packing gains 26 and loses 63, a net **-37**. The best observed corner
is the middle one: **rank coarse, pack fine**, which is also the configuration
already deployed.

This is a posthoc synthesis of already published arm outputs, not a registered
factorial experiment. LongMemEval is exhausted, so the result is characterized
rather than confirmed.

## 2. Mechanism

Session ranking pools query evidence across the surrounding session, while
episode packing charges only the small unit ultimately delivered. That
combination can carry a weakly matching answer episode because another episode
in its session provides the retrieval cue, without paying for the whole
session.

The discordant sets show exactly that pattern. The 63 items delivered under
session ranking but lost under episode ranking have answer episodes at median
own-cosine rank **46** and p90 **135**. The 26 items gained by episode ranking
are much shallower: median rank **10**, p90 **21**. Both arms choose from about
229 episode candidates per item under a heavily binding 32,000-character
budget. Own-episode ranking helps the shallow minority but removes the pooled
context that rescues a larger deep-rank group.

Part 1's earlier hard-tail statistic is consistent with this mechanism: items
missed by the deployed session-rank/episode-pack arm had median evidence rank
41. What was previously called an unexplained H2 residual is therefore visible
as an active benefit of contextual score pooling for many items, not merely a
limit waiting for a new similarity function.

## 3. Design rule and boundary

The measured rule is:

> **Use a broader unit to score context and a narrower unit to spend context.**

Here that means rank sessions and pack episodes. It is deterministic and
mechanistically identified by two one-factor contrasts, but its scope is this
corpus, embedding, packing policy, and binding ratio. It does not establish
that coarse ranking wins when a budget admits most candidates; the LoCoMo and
LongMemEval development budget sweeps test that moderator separately.

## 4. Preflight and provenance

This synthesis introduces no new mechanism run. PF1 is answered by the two
hash-bound input artifacts; PF2 by their exact arm definitions; PF3 is not
applicable because no gate is executed; PF4 is descriptive and assigns no bar;
PF5 joins by stable `question_id`; PF6 requires exact reproduction of all three
published totals; PF7 is inapplicable because there is no feedback; PF8 has no
ablation claim; PF9 records that strict episode delivery is availability, not
answer correctness; PF10 retains the live-evaluation requirement.

`src/analysis/nf003_three_arm_summary.py` refuses changed inputs, reproduces the
three totals and both paired contrasts, and emits the rank distributions above.
A byte-identical replay is required before commit.
