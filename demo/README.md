# Memory Observatory

Memory Observatory is the interactive demonstration surface for
`contextDecayWindow`. It replays the accepted Study 003 run as a familiar chat
while exposing the bounded context, topic state, pinned rules, consolidation
events, and STM-to-LTM writes that were otherwise visible only in logs and CSVs.

The autoplay holds each turn for five seconds: one second for the user prompt
and four seconds for the recorded response. Presenters can pause, scrub, or use
the key-moment bookmarks when showing only part of the run. It requires no model
server, API key, database, or user account.

## What the demo shows

- all 120 recorded user prompts and Qwen3.6 27B responses from the accepted run;
- the per-turn K similarity retrieval and N decay retrieval composition;
- the constructed prompt token estimate and model-performance telemetry;
- topic creation and ten-episode consolidation checkpoints;
- persistent rules outside episodic retrieval;
- the three write-only LTM events at turns 31, 61, and 91;
- the final 12/13 result, including the broad-query coverage failure rather than
  hiding it.

## Run locally

Prerequisite: Node.js 22.13 or newer.

```powershell
cd demo
npm install
npm run dev
```

Open the local URL printed by the development server. Useful verification:

```powershell
npm test
npm run lint
```

The replay is keyboard-operable: Space pauses or resumes playback, and the left
and right arrow keys move one turn at a time when focus is not inside a control.

## Real-data provenance

The demo consumes [`app/data/study-003-replay.json`](app/data/study-003-replay.json).
It is a deterministic derivative of the accepted `study_003_full_002` execution,
not synthetic UI fixture data.

The original heavy transcript remains intentionally ignored under the repository
artifact policy. On the research workstation it is located at:

```text
experiments/study_003/runs/study_003_full_002/iterative/logs/turns.jsonl
```

The exporter verifies that every raw metric and LTM CSV is byte-identical to its
tracked canonical counterpart under `experiments/study_003/runs/run_001/`, then:

1. compares all raw prompts against the locked Study 003 script;
2. copies the accepted assistant responses without summarizing or rewriting them;
3. copies active-context membership from the raw turn log;
4. sources displayed aggregate values from the tracked canonical CSVs; and
5. embeds SHA-256 checksums and a transformation record in the output.

Regenerate or verify the artifact from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\export_build_week_demo.py
.\.venv\Scripts\python.exe scripts\export_build_week_demo.py --check
```

On a fresh clone without the ignored transcript, `--check` still verifies the
committed replay prompts, canonical checksums, turn order, and LTM event totals.

## Architecture represented

The center conversation is the recorded model interaction. The top context strip
shows the bounded N+K prompt assembled for the selected turn. The left rail shows
the scripted domains and pinned behavioral memory. The right rail shows STM and
write-only LTM stores, the exact retrieved episodes, and architecture events.

LTM was observational in Study 003: promoted episodes were written but never read
back into generation. The UI labels this limitation explicitly.

## Build Week extension boundary

The research implementation and Study 003 artifacts predate the OpenAI Build Week
submission period. Memory Observatory—the replay exporter, curated web artifact,
interactive product surface, responsive design, and web tests—is the new Codex-
built extension. Commit history should be used to distinguish this work from the
pre-existing research code.

Codex accelerated four material parts of the extension: locating and auditing the
ignored accepted transcript, designing the compact evidence schema, implementing
the autoplay/inspection experience, and adding deterministic provenance and test
coverage. Product decisions retained by the researcher include the honest recorded
replay (rather than a fake live model), the approximately 80-second default pace,
and visible treatment of the failed final probe.

### GPT-5.6 eligibility checkpoint

The Build Week rules require meaningful GPT-5.6 use. The replay remains faithful
to the original Qwen experiment and must not be relabeled as a GPT-5.6 run. Before
submission, complete and document a material GPT-5.6 contribution to this new demo
surface in the primary Codex thread—for example, the final demo-director narrative
and evidence-grounded presentation script. Until that pass is committed, this
repository should not claim GPT-5.6 eligibility.

## Presentation path

1. Start on the idle screen and state the problem: long context is not the same as
   reliable memory.
2. Press **Replay Study 003** and point out the bounded active window.
3. Hold on turns 31, 61, and 91 to show selective STM-to-LTM writes.
4. Jump to turn 112 to demonstrate recall of early planted bridge facts.
5. Finish on the outcome screen: 12/13, two of three bars, and one honest coverage
   failure that motivates the LTM read path planned for Study 004.
