# LV-009 Result

Date: 2026-08-27

Registered disposition: `PAIRWISE_RETAINED`

## Validity

All registered live surfaces completed:

- 7,944 nonempty reader answers, with 11 accepted length stops;
- 18,480 parseable blind judgments, exactly three for each of 6,160 primary arm-answers, with 19 parseable judge length stops;
- 1,784 category-5 exact-refusal outcomes;
- zero missing, extra or duplicate rows; and
- the registered Qwen3.8 model remained fully resident on the RTX 5090 through both live phases.

The answers were committed before blind-surface creation, and all judgments were committed before the sealed arm mapping opened. Eighty-one of 6,160 primary arm-answers had judge-pass disagreement; majority-of-three is the registered endpoint.

## Primary result

| Arm | Correct | Percent |
|---|---:|---:|
| `PAIRWISE` | 907/1,540 | 58.90% |
| `COMMUNITY` | 876/1,540 | 56.88% |
| `COMMUNITY_QB` | 914/1,540 | 59.35% |
| `COMMUNITY_QEACH` | 920/1,540 | 59.74% |

`FULL_vs_PAIRWISE` (`COMMUNITY_QB` versus `PAIRWISE`) had 82 gains, 75 losses and net `+7` (`+0.45` percentage points; one-sided p=`.3161`). Its transfer net was `-1`, and category 4 reached the registered raw guard at net `-10`. It neither works nor carries signal.

`QUESTION_EACH_INCREMENT` (`COMMUNITY_QEACH` versus `COMMUNITY_QB`) had 44 gains, 38 losses and net `+6` (`+0.39` points; p=`.2906`). Its transfer net was `+4`, with no regression guard, but it missed both practical and statistical bars. It neither works nor carries signal.

Neither co-primary treatment-direction test survived Holm at familywise `.01`. T3 versus pairwise was descriptively `+13` (81 gains, 68 losses; `+0.84` points; p=`.1628`) and cleared no registered selection bar.

## Interpretation

Compact communities alone regressed against pairwise: 49 gains, 80 losses, net `-31` (`-2.01` points). Repeating the question at the top and bottom then improved QB over community-only by net `+38` (`+2.47` points; p=`.000770`) in a secondary comparison. That recovery did not become a reliable improvement over the registered pairwise control. Repeating the question after every community added only six net correct answers beyond QB.

The LV-008 selected-item signal therefore did not transfer as a registered full-population renderer improvement. Pairwise remains the retained renderer, and no `episodic-chat` port is authorized by LV-009.

Category-5 exact refusals were 318/446 pairwise, 351/446 community, 367/446 QB and 387/446 QEACH. These are reported separately and do not enter the primary endpoint.

## Claim boundary

This is an internal full-LoCoMO comparison using one frozen Qwen3.8 reader sample per question-arm and same-model blind judges. It is not an official benchmark score, a reader-model generality result, a deployment claim or a retrieval-adoption result. It does not estimate per-question stochastic stability.
