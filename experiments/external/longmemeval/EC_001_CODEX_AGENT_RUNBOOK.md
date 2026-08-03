# EC-001 manual model-switch runbook

This is the authoritative compact-session procedure under Amendment 009 as
superseded by Amendment 010.

## Files to read after compaction

Read, in order:

1. root `AGENTS.md`;
2. `amendments/AMENDMENT_009_codex_agent_evaluators.md`;
3. `amendments/AMENDMENT_010_two_hosted_replacements.md`;
4. `EC_001_CODEX_AGENT_RUNTIME_RECORD.json`;
5. `EC_001_CODEX_AGENT_CHECKPOINT.json`;
6. this runbook.

Do not reconstruct earlier chat history. The checkpoint is the current state.

## Resume gate

The user's message must exactly equal the checkpoint's
`expected_resume_phrase`. Treat that phrase as the user's attestation that the
desktop parent task is now using the checkpoint's `display_model`.

If it does not match, do not spawn or score. State the expected phrase and
stop. The product does not expose an immutable inherited-model identifier, so
this manual attestation is the registered identity boundary.

Before spawning, require:

- current branch `ec/001-longmemeval`;
- clean worktree;
- checkpoint status `WAITING_FOR_MANUAL_MODEL_SWITCH`;
- named stage output paths do not exist;
- identity map remains sealed.

## Spawn step

Spawn exactly one child:

- task name: checkpoint `spawn_policy.child_task_name`;
- `fork_turns`: `"none"`;
- omit `model`;
- omit `reasoning_effort`.

The child message must contain:

- the stage, display model, role, and user's exact resume phrase;
- every path in checkpoint `allowed_child_inputs`;
- every path in checkpoint `stage_outputs`;
- the exact calibration validator command below;
- an instruction to follow `EC_001_CODEX_AGENT_CHILD_CONTRACT.md`.

Rater-stage calibration command:

```text
.\.venv\Scripts\python.exe scripts\validate_ec001_codex_calibration.py
  --stage <STAGE>
  --display-model "<DISPLAY MODEL>"
  --observations <CALIBRATION OBSERVATIONS>
  --output <CALIBRATION GATE>
```

Do not pass an explicit model override even when one is available. The child
must inherit the manually selected parent model.

## Parent validation and commit

After the child returns, run:

```text
.\.venv\Scripts\python.exe scripts\validate_ec001_codex_rater_output.py
  --stage <STAGE>
  --display-model "<DISPLAY MODEL>"
  --resume-phrase "<RESUME PHRASE>"
  --child-task "<CANONICAL CHILD TASK>"
  --calibration-gate <CALIBRATION GATE>
  --rater-output <RATER OUTPUT>
  --output <VALIDATION REPORT>
```

If validation fails:

1. do not edit or accept partial labels;
2. record and commit the failed attempt;
3. restore the checkpoint to the same stage;
4. stop for an explicit same-model retry.

If validation passes:

1. commit the four stage artifacts together;
2. combine C1 with the committed Phi and Mistral outputs using
   `prepare_ec001_adjudication.py`;
3. commit the trigger packets and summary without opening the identity map;
4. update the checkpoint to C2 with both commit ids;
5. commit the checkpoint separately;
6. stop and tell the user to select GPT-5.5 and send
   `EC001 RESUME C2 GPT-5.5 SWITCHED`.

Never start the next stage in the same parent-model session.

## C2 adjudicator stage

After the parent has committed the trigger directory and advanced the
checkpoint, the user selects GPT-5.5 and sends the exact C2 resume phrase.
Apply the same clean-tree, phrase, and inheritance gates, then spawn one child
with `fork_turns="none"` and no model or reasoning override.

The C2 child reads only
`EC_001_CODEX_ADJUDICATOR_CHILD_CONTRACT.md` and the two committed trigger
packet files. After it writes the adjudication JSONL, validate it with:

```text
.\.venv\Scripts\python.exe scripts\validate_ec001_codex_adjudicator_output.py
  --h1-h2-packets <H1/H2 PACKETS>
  --h5-packets <H5 PACKETS>
  --adjudications <C2 ADJUDICATIONS>
  --resume-phrase "EC001 RESUME C2 GPT-5.5 SWITCHED"
  --child-task "<CANONICAL CHILD TASK>"
  --output <C2 VALIDATION REPORT>
```

Commit the adjudications and validation report before opening the identity map
or running finalization.

Do not run `finalize_ec001_scores.py` unchanged. It requires a
`benchmark_protocol` GPT-4o pass and emits a benchmark-protocol score, both of
which Amendment 010 forbids. Implement and test the Codex-substituted
finalization path before using the committed adjudications, without changing
the registered consensus or H1-H5 rules.

## Fixed stage sequence

| Stage | Display model | Role | Next |
|---|---|---|---|
| C1 | GPT-5.4 | third rater | trigger preparation |
| C2 | GPT-5.5 | adjudicator | finalization |

C2 begins only after the Phi, Mistral, and GPT-5.4 rater commits and a
separately committed trigger registration. GPT-5.5 is never a rater.
