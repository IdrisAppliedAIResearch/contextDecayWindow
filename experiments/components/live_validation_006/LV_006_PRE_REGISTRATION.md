# LV-006 — parse-safe completion of LV-005 blind judging

**Type:** registered instrument-repair continuation  
**Status:** pre-registered; not yet runnable  
**Date:** 2026-08-26

## 1. Purpose and boundary

LV-005 produced and sealed all 340 reader answers, then stopped before
unblinding when one judge response omitted its verdict. LV-006 repairs only the
judge-output instrument and completes the already registered LV-005 analysis.
It does not change or regenerate any reader answer, prompt, arm, population,
endpoint, comparison, disposition or claim boundary.

## 2. Frozen inputs

- Part 1 artifact SHA-256:
  `34f4ee1c7e5fddad90709071a84a41740c377db3a1631e62fb9bf70b96068f72`;
  commit `a8796191`.
- LV-005 prompt SHA-256:
  `d0a3ac38e15c1738387c9d3216de532195959dd4c8ac7515a03209bbfebe8b80`.
- LV-005 answer SHA-256:
  `a3e9fbef31f1d6ffca2b4af1484982951447b98ec41a4c370a2f00d35de8a53f`.
- LV-005 blind surface SHA-256:
  `97aaf2def7ff3f5c843fba4c98fd0afed3921ccbe44a43d44319f7c7b2c45205`.
- LV-005 sealed mapping SHA-256:
  `edf20068b2c923478760ba462f51c47508bd3bb21d8994d69b100fc0d2924737`.
- LV-005 stopped partial judgment SHA-256:
  `775fc2e2f0e86da9568f7f78bb775da5e9a881e09329357e775a0e088774ad1b`.
  It is a stop/reproduction anchor only and contributes zero verdicts to the
  repaired result.

The surface remains 320 primary answers, three judge passes each, for 960
judgments. Stable keys are the existing blind content ids plus judge pass.

## 3. Exact repair

For every blind surface row and each original judge seed `9005`, `9006`, and
`9007`, construct the exact frozen HH-001 judge prompt plus the exact frozen
closed-think suffix, then append the seven ASCII characters `VERDICT:` with no
leading or trailing whitespace.

Regenerate all 960 judgments under this one repaired prompt. Do not reuse or
mix any of LV-005's 136 original-instrument verdicts. Runtime remains the same
Ollama `0.33.0`, `qwen-custom:latest`, GPU-only, temperature `.2`, top-p `.9`,
top-k `20`, `num_ctx=65536`, `num_predict=128`, one request at a time.

Every response is parsed before it is appended. It must naturally stop and
contain an unambiguous HH-001 verdict. Each valid record is append-flushed and
fsynced before the next call. An unparseable, truncated, missing or duplicate
response stops LV-006 without analysis; no further prompt repair is authorized.

## 4. Analysis

Only after all 960 repaired judgments are committed may the sealed LV-005 arm
mapping open. Apply the unchanged LV-005 majority rules, five comparisons,
strata, containment cross-check, adversarial refusal check and dispositions:
`PROMISING`, `WEAK_SIGNAL`, `NO_SIGNAL`, `REGRESSES`, or
`NOT_INTERPRETABLE`. The `+3` bar and targeted/breadth non-regression guards are
unchanged. No arm selection, tuning, rerun or deployment is authorized.

## 5. Preflight

- **PF1:** hash and count this registration, Part 1 and every frozen LV-005
  input above; assert the stopped partial schedule is exactly 136 valid rows.
- **PF2:** reproduce Part 1's exact original failure twice and repaired success
  twice by response digest; verify the repair is only the appended `VERDICT:`.
- **PF3:** registration precedes implementation; repaired judgments commit
  before mapping access. Planted mapping access before completion must fail.
- **PF4:** carry LV-005's reachable dispositions and require the real Part 1
  exact-failure and 36/36 parseable positive control.
- **PF5:** reject duplicate/missing blind ids, judge passes and seeds.
- **PF6:** reproduce the 320-row surface and exact 960 repaired prompt digests
  twice without reading the arm mapping.
- **PF7:** repeat the repaired failed prompt at seed 9006; require byte identity,
  parseability, natural stop and full GPU residency. No feedback state exists.
- **PF8:** this repair changes no power: five reader replicates and 16 selected
  primary items still cannot estimate small effects, overall accuracy or
  transfer.
- **PF9:** a parse-safe cue can alter judge wording or verdicts; regenerating all
  960 avoids mixed instruments but does not eliminate same-model judge bias.
- **PF10:** live reader answers are already sealed; judgment is measurement,
  not a retrieval or rendering surrogate.

Additional gates require 960 unique naturally stopped parseable verdicts,
exactly three per blind id, and an unchanged 340-answer reader batch. Any gate
failure yields no result.
