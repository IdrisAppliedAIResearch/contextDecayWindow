# LV-006 — TC-014 context-organization live report

**Status:** `WEAK_SIGNAL`; no adoption  
**LV-005 registration commit:** `771eb828`  
**LV-006 repair registration commit:** `8cba6830`  
**Reader-answer seal:** `e703adb0`  
**Repaired-judgment seal:** `6782e4bc`  
**Date:** 2026-08-26

## Result

Organizing the exact same frozen TC-014 opportunity evidence produced one live
reader gain, but the component attribution is not clean enough to ship.

| Renderer | Correct / 16 | Semantic change vs flat | Registered status |
|---|---:|---:|---|
| Flat TC-014 opportunity | 5 | control | — |
| Related parent–child groups | 6 | 2 gains / 1 loss | `NOT_INTERPRETABLE` |
| Groups, chronological within group | 6 | 1 gain / 0 losses | `NOT_INTERPRETABLE` |
| Groups, chronology, temporal guidance | **6** | **1 gain / 0 losses** | **`WEAK_SIGNAL`** |

The full guided bundle gains one breadth question and loses none. Targeted and
other questions tie flat, and containment is net zero, so it clears the locked
`WEAK_SIGNAL` rule. Its exact paired p-value is 1.0; the 16 selected items are
not powered for a small effect.

Grouping alone is not valid evidence of improvement. It gains two breadth
items but loses one targeted item, and its semantic direction opposes the
containment cross-check. Chronological grouping removes that targeted loss but
also removes one breadth gain; semantic correctness is +1 while containment is
-1, triggering the endpoint-sign guard.

Chronology versus grouping has one targeted gain and one breadth loss, so its
registered status is `REGRESSES`. Explicit temporal guidance versus chronology
changes no semantic item-majority verdict at all: 0 gains, 0 losses,
`NO_SIGNAL`. Therefore the result supports only the full organization bundle
descriptively. It does not isolate the guidance text as the cause.

## What changed

Only three questions change semantic item-majority across any arm:

- **Breadth gain:** “Where has Maria made friends?” Flat usually omitted the
  gym. All three organized arms recover the homeless shelter, church and gym;
  grouped is 5/5 correct, chronology and guidance 4/5, versus flat 1/5.
- **Unstable breadth enumeration:** “How many screenplays has Joanna written?”
  Grouping reaches 3/5 correct, but chronology falls to 1/5 and guidance to
  2/5. Responses often mention “at least three” and then enumerate additional
  scripts or refuse an exact total. The LV-004 failure is not robustly solved.
- **Targeted instability:** “What state did Nate visit?” Flat is 4/5, grouping
  falls to 1/5, and chronology/guidance recover to 3/5. The evidence points to
  Tampa; responses oscillate between inferring Florida and refusing because
  the state is not written explicitly.

The net guided gain is entirely the Maria breadth question. The result is
consistent with adjacency making a distributed three-item set easier to
assemble, but one item cannot establish that mechanism.

## Cost and deployment boundary

The intervention preserves all 1,686 selected episode identities and every
episode element byte-for-byte, but readable markup costs substantial context:

| Renderer | Block characters min / median / max | Prompt tokens min / median / max |
|---|---:|---:|
| Flat | 31,891 / 31,983 / 31,998 | 8,024 / 8,487 / 8,789 |
| Grouped | 37,438 / 38,617 / 39,920 | 10,025 / 10,663 / 11,519 |
| Grouped + chronology | 37,467 / 38,646 / 39,949 | 10,029 / 10,667 / 11,523 |
| Temporal guidance | 40,973 / 42,542 / 44,397 | 10,807 / 11,545 / 12,545 |

This probe intentionally holds evidence identities fixed, so the structural
overhead sits above TC-014's original 32k selection. The guided arm uses about
33% more block characters at the median. It is not a deployable fixed-32k
renderer. A future test would need a compact schema charged inside the budget;
that would become a joint organization–displacement comparison.

No arm labels natural LoCoMo statements current or superseded. The corpus has
conversation order but no explicit update key, so only earlier/later ordering
is justified.

## Instrument repair and integrity

LV-005 sealed 340/340 naturally stopped reader answers, then stopped after 136
blind judgments when one deterministic response omitted the required verdict.
No arm mapping was opened. Part 1 reproduced that failure twice and found that
appending the literal `VERDICT:` cue parsed the exact failure twice
byte-identically and 36/36 blinded sample calls.

LV-006 pre-registered the repair, discarded all 136 partial-instrument verdicts
from outcome measurement, and regenerated all 960 judgments under the single
repaired prompt. The repaired batch has 320 blind ids, exactly three judgments
each, zero duplicates, zero omissions and zero truncations. All four arms
refused the adversarial item 5/5. Judges disagreed on 4/320 answers.

Artifacts:

- Answers SHA-256:
  `a3e9fbef31f1d6ffca2b4af1484982951447b98ec41a4c370a2f00d35de8a53f`
- Repaired judgments SHA-256:
  `d37bdc091d4c19b7a5e722f3a8b5f4ff97a743dd5a806e1ab11e0894874d6fa4`
- Result SHA-256 before documentation:
  `011d0a3cf49d781f99a14327c3189b5260c1eec3e44e206ff84be8ce783f76ee`

This remains a selected LoCoMo development rendering probe. It does not
establish overall accuracy, transfer, inferred supersession, an optimal schema,
or permission to change `episodic-chat`.
