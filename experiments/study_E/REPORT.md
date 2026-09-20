# Study E: before-event ordering development

Date: 2026-09-06. Status: **PART 1 COMPLETE; CONFIRMATION DESIGN RETURNED FOR REVISION.**

Pre-registration SHA: **none for confirmation**. The development plan and draft were committed before implementation at `5693e6b0dba579ab059f5b5abe8398f3c4b5916e`. This report closes the bounded development stage, not a registered confirmatory experiment. No adoption.

## What the reader answered

Both ordering policies produced correct final answers on **11/12 before questions (91.7%)**. There was one gain, one loss and ten ties. These are 12 paired questions from three synthetic sessions at one reader seed, not 12 independent histories. No hypothesis test or confirmation disposition is assigned.

| Condition | C0: Study D temporal | C1: nearest-prior ordering |
|---|---:|---:|
| Straight revision | 3/3 | 3/3 |
| Later irrelevant mention | 3/3 | 2/3 |
| Future-effective announcement | 3/3 | 3/3 |
| Unaccepted proposal | 2/3 | 3/3 |
| Primary total | **11/12** | **11/12** |
| Latest guard | Not run | 4/4 |
| Absent-field guard | Not run | 4/4 |

The C1 loss was Orchard-324: expected laboratory, answered office. The C0 loss was Riverside-893: expected office, answered workshop; C1 ultimately answered office. Both arms had the sufficient evidence on both questions. The guard results cannot establish a paired absence-harm effect because the development schedule generated only C1 guard answers.

The 35 calls comprise three preflight/calibration calls and 32 measurement calls. All completed, the maximum-prompt repeat was byte-identical, and the original Study D model, generation settings and HH-001 prompt were retained. The prompt did not ask for explanations. This is not a verified Mem0-paper system prompt comparison.

## Scoring and response quality

Fifteen responses were resolved mechanically. Seventeen needed judgment because they contained explanations, corrections or a misspelled abstention. The user authorized agent adjudication after inference. [Amendment 001](amendments/AMENDMENT_001_development_agent_adjudication.md) records the substitution for human review; all 17 received credit for their explicit final commitment. There was one agent reviewer, no independent three-pass rating and no human audit. Do not describe these as independently validated scores.

Seven correct final answers began with an incorrect assertion and then explicitly corrected it: three C0 and four C1. Thus 91.7% final-answer correctness does not mean consistently correct prose. A descriptive sensitivity that also rejects these initially wrong responses gives C0 8/12 and C1 7/12; this is not the primary rubric or a new verdict. One absence response was `I don know.`: semantically abstaining but not exact-format compliant. The other three absence answers passed the frozen grammar.

Commit order: raw completeness `acc6a07c`; mechanical scores `2a237b0c`; pending packet `f3bb2883`; authorization amendment `27974103`; resolved blind scores `3928e6ea`; only then arm-level analysis. Original pending artifacts and the frozen parser remain unchanged. The explanatory text was not used to supply an answer absent an explicit final commitment.

## What the implementation established

C0 is Study D's temporal treatment, not its plain CC80 baseline. C1 preserves the same accepted before-anchor query, anchor and eligible set, but orders prior subject records newest-first. The anchor stays first. Temporal allowance remains 8,000 serialized characters within the same 32,000-character retrieval block, plus unchanged latest-32 continuity. Full-record packing, renderer, embeddings and other routes are unchanged. No DA packing or compression was added.

The isolated control reproduced **224/224 frozen Study D prompts** exactly and repeated identically. On the exposed Study D before population, this ordering raised complete evidence from **16/32 to 32/32**. That replay used no new reader calls and supports only an availability claim on already exposed data.

The new development generator did not reproduce that availability contrast. Both the initial corpus and the single authorized density extension delivered **20/20 answerable sufficient sets in each arm**. The dense version changed all 16 before prompts and all four active absence prompts; eight of these 20 queries changed selected membership. Latest prompts were identical. Therefore the intervention was active, and the reader comparison was meaningful for behavior with complete evidence, but the development corpus did not exercise retrieval rescue from missing evidence.

Four mechanism/source contract tests pass. They cover independent source-state reconstruction, before-only changes, repeat identity, ambiguous/fallback queries, recent-only and oversize cases, and a deliberately failing measurement-import sentinel. The source check verifies required records occur before turn 109, outside continuity. Existing product modules were not changed. Runtime and artifact checks are in [closeout verification](artifacts/part1/closeout_verification.json).

## Design decision and its limits

The bounded Part 1 schedule and one density extension are complete. Confirmation seeds 94001–94032 remain unopened, and no final registration exists. **Return the generator and proposed confirmation design for revision.** This is a design-readiness decision: the development corpus saturates availability and does not exercise the motivating missing-evidence contrast.

The reader was near ceiling, not at an exact zero-error ceiling: both arms made one error on different questions. Consequently this is **not** the literal zero-gap ceiling stop described as an example in PART1_READER_GATE.md, and not a registered REGRESSES or NO_DEMONSTRATED_BENEFIT verdict. Do not invent a gate that fired. The observations neither establish ordering benefit nor establish equivalence or ineffectiveness. A different, explicitly framed complete-evidence organization study could use such a population, but that would answer a narrower question.

Before confirmation, a revised development plan should specify source competition that can leave required evidence outside the control budget, independently of reader outcomes, while retaining irrelevant-mention, future-effective and proposal hazards. It must also freeze final-commitment versus response-consistency measurement and reviewer responsibility before new inference. Do not select future sessions because C0 fails or C1 wins, enlarge this finished pilot, or tune density repeatedly until a favorable contrast appears. See [design review](DESIGN_REVIEW.md).

## Artifact index and closeout

- [Frozen design draft](DESIGN_DRAFT.md), [Part 1 plan](PART1_PLAN.md), [density extension](PART1_DENSITY_EXTENSION.md), [reader gate](PART1_READER_GATE.md).
- [Prior prompt replay](artifacts/part1/replay.json); initial and dense source/vector/label/prompt artifacts under `artifacts/part1/development*`.
- [Runtime input gate](artifacts/part1/reader/input_gate.json), [prefix gate](artifacts/part1/reader/prefix_gate.json), [completion](artifacts/part1/reader/complete.json), full raw responses and final server logs in the same directory.
- [Blind review packet](artifacts/part1/reader/REVIEW_PACKET.md), [agent judgments](artifacts/part1/reader/agent_adjudications.json), [resolved scores](artifacts/part1/reader/scores_resolved.json), [descriptive result](artifacts/part1/reader/descriptive_result_resolved.json).

Reader server stopped after process identity verification; completion automation paused. README, AGENTS digest and memory updated. No prior published number changed, so ERRATA is unchanged. Separate PR closes development only; no merge, deployment, or confirmation inference.
