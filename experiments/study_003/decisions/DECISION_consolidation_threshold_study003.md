# Decision: Study 003 Consolidation Threshold

**Status:** Accepted for Study 003; revisit in Study 004

**Date:** July 2026

## Decision

Study 003 uses a cosine-similarity threshold of **0.45** for topic consolidation. Topic assignment also uses 0.45 with user-message embeddings.

## Basis

Study 002's 0.60 consolidation threshold produced no merges and ended with 52 topics. Study 003's amended 35-turn ablation produced one stable civil-engineering topic across turns 1–30 and one Renaissance-art topic from turn 31. In the accepted 120-turn run, topic count tracked the four scripted domains through turn 110 and finished at 1, passing the pre-registered `<= 20` bar.

## Observed trade-off

At turn 120, the comprehensive four-domain query caused four merges at similarities from 0.45 to 0.54, collapsing five topics into one. The threshold solved fragmentation but permits cross-domain over-consolidation when a query spans multiple domains.

## Consequence

The 0.45 threshold is retained as the value tested in Study 003. It is not adopted as a general default. Study 004 should pair topic-count measurement with cluster-purity or cross-domain merge checks and should test whether comprehensive multi-domain probes require a separate mixed-topic representation.
