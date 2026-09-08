# Reader anchor capability diagnostic

Plan1b6c79ef; frozen histories/expectations b3e2ea4b; calibration c179a703; raw completeness b04da2a3. Eight constructed short histories, one call each, Qwen3.8 native thinkingOFF,serial,seed5005. Diagnostic prompt explicitly requests event resolution, citations, ambiguity and cutoff safety; it differs from HH001 answer-only. No retrieval changed. Eight calls took19.25seconds and1,117output tokens, excluding startup and two arithmetic calibration calls.

| Case | Observed response |
|---|---|
| One job thread | Linked “said yes” to acceptance, answered Bristol, cutoff safe |
| Two offers | Kept Elm/Pine ambiguous; no specific employer inferred |
| Later clarification | Located acceptance at passage3, used later passage5 to identify Elm; cutoff unsafe |
| Retrospective residence | Located acceptance at3, used later4 to establish Bristol; cutoff unsafe |
| Intention, not event | Did not convert a conditional plan into completed acceptance |
| Different people | Did not attribute Sam’s acceptance to Alex |
| Missing antecedent | Did not infer Elm—or even employment—from an unspecified offer |
| Older named thread | Connected office role to Pine despite a more recent Elm offer |

All eight status fields match the prewritten resolved/ambiguous/unresolved interpretation. Every structured citation refers to an existing passage. This is mechanical field inspection plus single-agent qualitative review, not a formal correctness score or independent human/three-rater audit.

The reader can perform these distinctions when explicitly instructed on short, constructed chronological inputs. In particular, resolving an event and deciding a source cutoff is safe are separable: both later-evidence cases were resolved while flagged unsafe to cut. This supports testing reader-assisted resolution further; it does not validate autonomous boundary selection.

## Limits and observed weaknesses

- Citation sets are not complete dependency traces. The one-thread answer cites passage1 as the connecting set, omits offer passage2, and mentions later passage4 only in its explanation. The retrospective case cites4 but omits the offer antecedent2. Correct answers and in-range citations do not certify a sufficient retained evidence set.
- The different-people response fills competing_interpretations with hypothetical futures (later acceptance, refusal, continued deliberation), rather than limiting that field to competing readings of observed passages. These are marked possibilities, not asserted events, but the schema is not a clean evidence-only interface.
- In the missing-antecedent explanation, “Congratulations” is described as confirming the event; it adds no independent evidence about the employer or offer type.
- Cutoff safety was requested directly, not measured by rerunning the reader on each proposed prefix. First-case later evidence is corroborative; the verdict is consistent with the scripted expected continuity, but not a proof of real-world state persistence.
- Instructions explicitly warn about plans and ambiguity. No unscaffolded comparator, shuffled chronology arm, natural corpus sample, retrieval omission test, or replication was run. Do not attribute performance causally to chronological ordering or claim LoCoMo generalization.
- The reader sees all supplied short histories. The hidden-competitor problem remains: a sole retrieved candidate may not be the sole source candidate. Native thought traces were not collected; brief explanations are observable outputs only.

## Next step

Test a small frozen set of natural questions using current retrieved chronological timelines, with source-based event/ambiguity annotations fixed before calls. Examine event identity, later supporting passages and omitted competing events separately. Preserve current relevance selection and do not apply a hard cutoff until evidence preservation is tested. No automatic follow-on authorized by this report; full LoCoMo remains paused for design discussion.

Inputs and prewritten expectations are in artifacts/inputs.json and expectations.json; all responses, inspection.json, completeness hashes and owned-server stop record are preserved. No jobs or hooks remain active.
