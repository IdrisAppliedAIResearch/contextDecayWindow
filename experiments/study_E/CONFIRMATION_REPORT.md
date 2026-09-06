# Study E confirmation: newest-first before-anchor ordering

2026-09-06. Registration **2e047c41c80748b16f0e6df15dcc70ac54145598**; runtime amendment **6603aca3**, runtime lock **36e2347c**, fresh input lock **59e7cc8c**. Disposition: **READER D1_WORKS**. Same Study E and PR95; no adoption or merge.

Newest-first ordering improved the reader's final answers on the registered synthetic competing-update population. C0 answered **177/640 (27.66%)** primary instances correctly; C1 answered **302/640 (47.19%)**. The gain was **19.53 percentage points**, with a group-bootstrap 95% interval of **13.91–25.16 points** and one-sided paired group sign-flip **p = 0.0000099999**. This clears the prospectively fixed D1 bar of at least 10 points and p ≤ .05. All observed-harm guardrails passed.

This is a generated-answer result. Evidence delivery also improved, but delivery alone does not establish success: C1 still gave **243 wrong answers with complete required evidence**. Its overall primary accuracy remains below half.

## What was compared

C0 is frozen Study D temporal retrieval. C1 retains its unique anchor and exact-quoted-subject eligible set, changing accepted before-anchor candidates to descending source-turn order. Both use the same 8,000-character temporal allowance, 32,000-character retrieval allowance, full episodes, CC80 fill, renderer, deduplication and additive latest-32 continuity. Thus 32,000 characters is the retrieval budget, not the full reader prompt. Membership and presentation order can both change; their separate contributions were not identified.

The confirmation has 32 new groups, each containing six independent 140-record histories: 192 histories, 26,880 records and 192 questions. The four before conditions supply 128 primary questions, each read at five seeds per arm. Four arms produce 3,840 logical answers, captured through 3,505 unique prompt-and-seed measurement calls plus three calibration calls. Exact prompt/seed aliases retain all logical score identities. Statistical inference uses **32 groups**, averaging the five seeds and four before conditions within each group; 640 answers are not 640 independent samples.

## Final-answer results

Each condition below has 32 questions × five seeds = 160 answers per arm. Reference arms are descriptive and do not determine inclusion or disposition.

| Condition | C0 | C1 | C1−C0, points | ORACLE | NULL |
|---|---:|---:|---:|---:|---:|
| Straight before | 41/160 | 61/160 | +12.50 | 104/160 | 0/160 |
| Irrelevant intervening change | 49/160 | 64/160 | +9.38 | 131/160 | 0/160 |
| Future-effective update | 48/160 | 105/160 | +35.63 | 129/160 | 0/160 |
| Unaccepted proposal | 39/160 | 72/160 | +20.63 | 160/160 | 0/160 |
| **Primary: four before conditions** | **177/640** | **302/640** | **+19.53** | **524/640** | **0/640** |
| Latest guard | 102/160 | 102/160 | 0 | 160/160 | 0/160 |
| Absent-field guard | 160/160 | 160/160 | 0 | 160/160 | 160/160 |

There were 184 paired primary gains, 59 losses and 397 ties. At the inferential group level, 28 groups improved, three declined and one tied. Per-condition effects are descriptive; no separate condition-success tests were added. The irrelevant, future and proposal contrasts all exceed the −5-point observed-harm boundary; absence ties. Latest C0/C1 prompts and seedwise answers are identical by the registered alias invariant. The reverse-direction descriptive sign-flip p is 1.0.

ORACLE scored 524/640 (81.88%) on before questions: **116 wrong answers even when only the prospectively sufficient records were supplied**. ORACLE therefore does not show perfect interpretation. It changes the context contents and length, so the gap to C1 does not isolate a single source of reader error. NULL's primary 0/640 and absence 160/160 are consistent with abstaining without evidence, not evidence that the memory layer detects absence.

Latest accuracy here is 63.75%, not Study D's 100%. The generator and reader interface changed between studies. That difference cannot be attributed to thinking, retrieval regression, or model variability in isolation. Study D's published result remains unchanged.

## Evidence, ranks and costs: descriptive diagnostics

The evidence unit is the exact required source identity, verified against its complete episode in the actual rendered prompt. An older occurrence of the same answer value is insufficient. All 128 primary questions had their required records in the same eligible candidate set in both arms.

| Stage, primary questions | C0 | C1 |
|---|---:|---:|
| Eligible candidate set contains all required sources | 128/128 | 128/128 |
| Temporal admissions contain all required sources | 19/128 | 85/128 |
| Final pack and rendered prompt contain all required sources | 64/128 | 109/128 |

Complete-evidence delivery gained 47 questions, lost two and tied on 79 (62 complete in both, 17 incomplete in both). By condition, final complete-evidence counts were straight 20→27, irrelevant 22→28, future 22→28 and proposal 0→26, each out of 32. Latest remained 21/32 in both. Absence has no positive required evidence and is excluded from this metric.

| Primary answers | Complete + correct | Complete + wrong | Incomplete + correct | Incomplete + wrong |
|---|---:|---:|---:|---:|
| C0 | 133 | 187 | 44 | 276 |
| C1 | 302 | 243 | 0 | 95 |

These cells use the same 640 logical observations per arm. C1 had complete evidence for 545/640 answers (85.16%); it answered 302/545 (55.41%) of those correctly. C0 answered 133/320 (41.56%) of its complete-evidence instances correctly. These conditional populations differ, so this is not a causal estimate of reader improvement given fixed evidence. C0's 44 correct answers without the designated carriers cannot be called sufficient retrieval; repeated values permit correct answers without the required provenance. Of C1's 338 total primary errors, 243 occurred with complete evidence and 95 with incomplete evidence. Availability and interpretation both remain constraints.

Both arms admitted ten temporal records per primary question. Across all 320 required carrier occurrences (including anchors and qualifiers), the temporal candidate-rank p95 fell from 77.1 to 13; raw CC80 ranks were unchanged. Final packing retained 243/320 required carrier occurrences in C0 and 301/320 in C1. The admitted-only rank summaries are selection-conditioned; see the per-carrier rows for missing values.

C1 added a median eight source identities and removed a median eight per primary question (added range 4–9; removed 4–10). Across questions it added 61 required carrier occurrences and removed three. Median final retrieval length was 31,933.5 characters for C0 versus 31,345.5 for C1; every block respected 32,000. Median full native reader prompt length was 58,051 versus 57,471.5 characters, including additive continuity and instructions. C0 packed 40–41 records (median 41), C1 40–41 (median 40). These are realized costs under matched caps, not equal-length contexts.

## Runtime amendments and exclusions

The first confirmation attempt stopped at its 8,192-token cap after 456 calls. Amendment 004's single repair also stopped at 16,384 after two successful calibration calls. Both attempts are preserved, unscored and excluded; neither produced a mechanism verdict.

Amendment 005 authorized native thinking-off verification, a bounded batching benchmark and a full restart. The old trailing empty-think suffix was removed; the remaining carried instruction, evidence and query were wrapped as one user message in the native template. Native reasoning was disabled, context set to 32,768, output cap retained at 16,384 and prompt cache reuse disabled. The same runtime was used for every arm and seed. This is an amended reader interface, **not an unchanged prompt relative to Study D or an isolated experiment on thinking**. Ordinary explanatory text remains possible with thinking disabled.

The 48-call development benchmark tested one, two and four slots. Each 16-call workload took 65.18, 67.21 and 67.67 seconds respectively. Each repeated itself exactly, but both batched settings changed one response relative to serial and failed the speed requirement. Serial was selected before confirmation outcomes were opened. This small short-answer workload does not establish that batching is generally unhelpful.

The fresh run completed all 3,508 calls, nonempty at EOS, with no truncations or old-response reuse. Output length was median four tokens, p95 six, maximum 2,155. Summed request time was 7,060.4 seconds (117.67 minutes); this excludes preparation and scoring. Median request latency was 3.46 seconds, p95 4.02, maximum 33.29. These measurements combine calibration and different reference contexts and are not a deployed latency claim. The dedicated server was verified and stopped after completion.

## Scoring, integrity and closeout

The frozen exact-answer grammar handled 3,692 logical answers. After calibration on the locked no-answer/contradiction examples, one blinded agent reviewed 114 unique noncanonical responses representing 148 logical answers. It scored 72 unique exceptions correct and 42 wrong. This is the prospectively registered single-agent protocol, **not human review or an independent three-pass audit**.

There were 64 noncanonical misspelled abstentions, all semantically correct (C0 29, C1 35). Twelve responses revised incorrect openings: C0 nine (seven ultimately correct, two still wrong), C1 three (one ultimately correct, two still wrong). The final commitments determine correctness; revisions between two wrong values remain wrong and are explicitly distinguished from successful corrections.

The preserved git order is: complete raw captures **efc72ce9** → blind mechanical scores **e2ea9523** → all exception judgments **cfee7468** → all resolved scores **ad97703a** → unsealed result and verified diagnostics **e48fe4e8**. No mechanism traces or arm comparison were opened before score lock. Checks verified exact rendered-source survival, stage counts, budget bounds, full score coverage, latest identity and registered statistics. Candidate diagnostics for the unchanged latest route were corrected before verification; preliminary files are nonauthoritative, as recorded in `DIAGNOSTIC_VALIDATION_NOTE.md`.

The result supports this ordering policy under this restricted quoted-entity grammar, synthetic competing-update generator, frozen local model and amended reader interface. It does not establish general multihop reasoning, field-aware state inference, naturalistic transfer, DA fusion, evolving-conversation endurance or deployment readiness. Earlier development guided the corpus, and that selection limits scope. The next scientific question is how to resolve the remaining complete-evidence errors without losing the measured retrieval gain; no new study or tuning is authorized by this closeout.

Report, source/vector manifests, runtime gates, raw logs, scores, diagnostic artifacts, README, AGENTS digest and memory are preserved on the study branch. PR95 is the closeout vehicle. No prior published score changed, so no ERRATA entry is required. No product adoption, merge or deployment was performed.

## Artifact index

- [Registration](PRE_REGISTRATION.md), [runtime amendment](amendments/AMENDMENT_005_thinking_off_restart.md), [runtime lock](amendments/AMENDMENT_005_RUNTIME_LOCK.md).
- [Completion gate](artifacts/confirmation/restart005/complete.json), [arrival archive](artifacts/confirmation/restart005/arrival.jsonl.gz), [ordered response archive](artifacts/confirmation/restart005/responses.jsonl.gz).
- [Resolved scores](artifacts/confirmation/restart005/scores_resolved.json), [scoring gate](artifacts/confirmation/restart005/scoring_gate_resolved.json), [registered result](artifacts/confirmation/restart005/result.json).
- [Verified diagnostic summary](artifacts/confirmation/restart005/diagnostics_verified.json), [per-question carrier/rank/cost rows](artifacts/confirmation/restart005/diagnostics_rows_verified.json), [diagnostic validation note](DIAGNOSTIC_VALIDATION_NOTE.md).
- [Original stopped run](CONFIRMATION_STOP_REPORT.md), [Amendment 003 development report](AMENDMENT_003_REPORT.md).
