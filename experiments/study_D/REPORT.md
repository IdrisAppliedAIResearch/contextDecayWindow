# Study D report: temporal retrieval in synthetic revision histories

Registration SHA: `7b7506d2aa64c86a50ec88181b72137c66b44f02`  
Status: COMPLETE, D1_WORKS under registered numerical bars, with an authorized scoring-procedure deviation. No production adoption. Date: 2026-09-05.

## Finding

The deterministic temporal allocation raised primary reader correctness from 63/320 (19.6875%) to 203/320 (63.4375%): +43.75 percentage points. The session bootstrap 95% interval is +33.4375 to +53.75 points; the one-sided 100,000-draw session sign-flip p is 0.0000099999 (Monte Carlo resolution, not an exact p). Reverse-direction descriptive p is 1. There are 32 independent randomized sessions, not 320 independent trials. Session differences are positive in 28, negative in one, and zero in three.

This clears the fixed +10-point practical and p<=.05 D1 bars, with primary complete evidence increasing from 20/64 to 48/64 and observed diagnostic guard differences zero. The weaker D2 bar was +2.5 points and p<=.10. No bar or population changed after inference.

## Reader and delivery results

Each type has 32 questions and five seed replicates: 160 logical answers per arm. Evidence denominators are questions, not replicates.

| Type | Baseline correct /160 | Temporal correct /160 | Baseline complete evidence /32 | Temporal complete evidence /32 |
|---|---:|---:|---:|---:|
| T1 immediately before | 15 | 43 | 4 | 16 |
| T2 latest setting | 48 | 160 | 16 | 32 |
| T3 supersession | 160 | 160 | 32 | 32 |
| T4 duration | 153 | 153 | 32 | 32 |
| M1 badge chain | 160 | 160 | 32 | 32 |
| M2 locker chain | 160 | 160 | 32 | 32 |
| N1 absent fact | 160 | 160 | not applicable | not applicable |

ORACLE scores 160/160 on every type. NULL scores 0/160 on each answerable type and 160/160 on N1. The short gold-only context is a diagnostic reference, not a matched-length reasoning ceiling.

Latest-setting accuracy rises 30%->100%. Immediately-before rises 9.375%->26.875% and remains substantially unresolved: C1 delivers the complete registered support on only 16/32 questions. T1's reader-difference interval is +4.375 to +30.625 points; T2's is +56.25 to +83.125. These type intervals are descriptive.

On C0's 148 complete-evidence answerable questions, C0 scores 94.054% versus same-item ORACLE 100%. On C1's 176 complete-evidence questions, C1 scores 95% versus same-item ORACLE 100%. On the common 148-question subset, C0/C1/ORACLE are 94.054%/97.568%/100%. Different selected subsets are not a causal decomposition. These observations leave both evidence-delivery and context-sensitive reader limitations; they do not identify a particular reasoning defect.

## Scope and mandatory limitations

This is a restricted synthetic quoted-name grammar, one generator family, 32 randomized instances of 140 source episodes, and one local Qwen3.8 reader. It is not naturalistic transfer, organic conversation, endurance, or a general temporal-reasoning result. The matched allowance is 32,000 serialized retrieval characters with identical additive last-32 continuity, not a matched token expenditure.

N1 uses C0 fallback and identical shared responses: its difference is mechanically zero. Baseline abstention is observed, but fabrication harm from temporal additions is NOT TESTED. M1/M2 also fall back and have unique substantive badge/locker carriers, permitting shortcuts; their perfect scores do not demonstrate robust multi-hop reasoning. These limitations were committed before score unsealing in PRE_UNSEAL_LIMITS.md.

## Scoring deviation and chronology

The original protocol required human review for nonstandard ambiguous surfaces (or three calibrated AI passes plus human audit for judgment-based scoring). Mechanical scoring produced 3,675 distinct reference-specific score surfaces, eight pending. The full blinded packet was shown to the user. The user directed the agent to score it and then explicitly instructed unsealing after seeing the agent's judgments. Amendment 001 records acceptance of those eight single-agent judgments without the original human/three-pass validation. This is a post-inference procedure deviation, not human adjudication or full compliance with the original confirmatory protocol. The original pending score set and gate remain unchanged. No reference or mechanical score changed.

Reader outputs were sealed at `00ab7475`, original mechanical scores at `fe184bbf`, authorization amendment at `abf43c65`, and additive resolved scores at `3bc6b952`, before outcome analysis. The eight adjudicated scores are 0,1,1,1,0,0,0,1. The primary result is therefore reported with this explicit qualification rather than as an undeviated confirmation.

## Execution, costs, and verification

All 3,355 physical responses passed completion for 4,480 logical cells. Identical prompt/seed outputs were shared with explicit aliases; different references retain distinct score aliases. Raw responses comprise 92,216,018 bytes, losslessly archived to 7,196,049 bytes. Registered single-slot inference ran about 38m46s; embedding preparation used eight independent deterministic workers. No new inference was used for scoring or analysis.

Mean full prompt tokens are 13,639.38 for C0 and 13,646.22 for C1; maxima 13,752 and 13,738. ORACLE mean/max are 385.58/631 and NULL 87.29/95. Both tested contexts fit the common 65,536-token slot with the locked 8,192-token output reservation. The dedicated study server was stopped after capture; its complete log is preserved separately from the original preflight snapshot.

All 15 study tests pass. Read-only verification passes 21 registered/prepared artifact checks, response archive identity for all 3,355 rows, original score hash, additive resolved-score/adjudication hashes, unchanged mechanical entries, and exact pending-ID coverage. The frozen control and shipped product code remain unchanged. Prior 4,355-group parity, prefix and instrument gates are retained. No prior published number changed; ERRATA requires no edit.

## Artifacts and next step

- [Machine-readable result](artifacts/confirmation/result.json): statistics, per-session and per-seed outcomes, conditional subsets, costs.
- [Paired descriptive counts](artifacts/confirmation/paired_descriptive.json): replicate-level gains/losses/ties, not independent units.
- [Registration](PRE_REGISTRATION.md), [amendment](amendments/AMENDMENT_001_agent_adjudication.md), [pre-unseal limitations](PRE_UNSEAL_LIMITS.md).
- [Reproduction](REPRODUCTION.md), [resolved scores](artifacts/confirmation/resolved_scores.json), [original pending scores](artifacts/confirmation/blind_scores.json).
- [Lossless response archive](artifacts/confirmation/responses.jsonl.gz), [archive hashes](artifacts/confirmation/response_archive.json).

The supported finding is a substantial instance-family gain from deterministic temporal allocation, especially latest-setting retrieval. Any successor needs separate authorization and registration; priorities are immediately-before delivery, naturalistic transfer, and an absence-harm instrument that actually activates treatment. This study authorizes no tuning or adoption.
