# SR-001 Amendment 001 - Serialized Score Anchor

**Date:** August 11, 2026
**Design commit:** `baa317db41cb45b90087f4ec1cb1d4bd558cf55a`
**Authorization commit:** `f99b86a4`
**Trigger artifact commit:** `b8ed96e0`
**Status:** AUTHORIZED BLOCKER REPAIR

## Trigger and evidence

The first label-blind Part 1 execution stopped because three of 24 historical
M2 payload SHA-256 reproductions failed. In all 24 queries, selected episode
identities and delivered character counts reproduced exactly. The three byte
differences are score-attribute rounding boundaries caused by recomputing
cosines from the committed read-only cache:

| Query | Episode | Committed score/render | Replay score/render |
|---|---|---:|---:|
| `h121_l03` | `761e828b-48bb-4424-9d65-e17ab7e6b813` | 0.324259490 / `0.324259` | 0.324259520 / `0.324260` |
| `h121_c04` | `14047a25-628c-41ed-818b-341135abd99b` | 0.491080493 / `0.491080` | 0.491080523 / `0.491081` |
| `h121_e02` | `761e828b-48bb-4424-9d65-e17ab7e6b813` | 0.380358458 / `0.380358` | 0.380358517 / `0.380359` |

The maximum observed difference is below `6e-8`. It does not change rank,
selection, packing decisions, or payload length, but it prevents the registered
byte-identical reproduction anchor from passing.

## Change

For the 24 holdout queries only, after the complete source order is computed,
replace a source's display score with the score recorded in that query's
committed Tier 2 M2 `selected` row when such a row exists. Apply the resulting
same ordered source-and-score sequence to C0 and T1. Sources absent from the
committed selected rows retain the recomputed cached-vector cosine.

The committed score is used only in the serialized `score` attribute and as the
value inherited by that source's spans. It must not reorder sources. Runtime
assertions require source identity order before and after anchoring to be
identical and require every anchored source to occupy the same historical M2
selected position.

Q11 is unchanged because it already uses its committed full-rank score
inventory.

## Rationale

The registration requires byte-identical C0 reproduction. The historical full
rank score vector was not retained, but the committed selected rows contain the
exact scores that affect the historical payload bytes. Anchoring those display
values is narrower than weakening exact reproduction and preserves the causal
contrast: both arms still receive the identical full source order and identical
source scores, and only the packable representation differs.

## Exclusions and unchanged bars

This amendment does not change source identities, source order, selected
identities, span extraction, span order, packer, renderer, budget, labels,
facts, domains, G1-G5, stopping rules, ablation authorization, or outcome
ceiling. It does not introduce span vectors or span reranking. The failed Part
1 artifact remains committed and is not overwritten; the corrected run uses
new `part1_process_2` and `part1_process_3` directories.

The author's August 11 instruction authorizes full execution of the stated
study. This amendment repairs a discovered reproduction-unit mismatch without
making any criterion easier after outcomes; measurement labels have not been
opened.
