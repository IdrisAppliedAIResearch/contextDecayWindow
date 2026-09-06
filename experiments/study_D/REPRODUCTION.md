# Study D reproduction and artifact map

The authoritative design is `PRE_REGISTRATION.md`, introduced alone with its input hash manifest at commit `7b7506d2aa64c86a50ec88181b72137c66b44f02`. `DESIGN_REV2.md` is a preserved draft, not the executed protocol. Part 1 plans and extensions document development choices before each exploratory stage; no development result is a confirmatory result.

## Read-only verification

On the registered Windows checkout, run:

```powershell
.venv\Scripts\python.exe experiments/study_D/verify_artifacts.py
.venv\Scripts\python.exe -m pytest experiments/study_D/test_development_contract.py experiments/study_D/test_confirmatory_gates.py -q
```

The tests require the frozen baseline worktree at sibling path `contextDecayWindow-study-D-control`, checked out at `5ebda1ef4510c1806709039aeb66e6d79cedbbd8`. Its ignored LoCoMo embedding cache must be restored from the hash-verified original cache if replaying the prior CC-007 parity; no replacement vectors may be generated for that equality claim. The test environment and all local model/runtime paths are recorded in Part 1 and confirmation runtime manifests. These instructions do not claim cross-platform byte reproduction.

`verify_artifacts.py` checks registered input/code hashes, sealed preparation files, rank-provenance supplement, blind surface and score hashes when present, and the lossless response archive. It makes zero model calls and changes no artifacts. Study-local attributes preserve registered code LF and generated JSON CRLF conventions.

## Raw outputs

`artifacts/confirmation/responses.jsonl.gz` is a gzip copy of every persisted physical reader response, including the server's raw fields. `response_archive.json` gives both compressed and decompressed SHA-256 and byte counts. The local uncompressed JSONL is retained but ignored by Git to avoid repeating large echoed prompts. Decompressing the archive reproduces the exact raw JSONL used by the reader gate; it is not a summary or replacement answer surface.

`mapping.json` maps all 4,480 logical query/arm/seed cells to physical call keys. `score_aliases.json`, when produced, separates physical response aliases from score aliases: the same empty-context response can be compared with different session references. `blind_surface.json` omits arm and retrieval identities. `blind_scores.json` preserves each mechanical parse and rationale; ambiguous surfaces remain in `adjudication_packet.json` rather than receiving automatic zeroes.

## Execution order

The command stages are `confirmatory.py prepare`, the supplemental `instrument_gate.py`, commit of both preparation gates, `confirmatory.py prefix`, commit of the prefix gate, then `confirmatory.py run`. After a successful reader completeness gate, archive outputs and commit the reader gate before invoking `score_blind.py`. Commit all blind scores before invoking `analyze_locked.py`. The analysis refuses a pending-adjudication scoring gate.

These commands are not instructions to repeat a completed registered run. Existing seals and response files deliberately prevent overwriting completed stages. An uncertain request leaves `pending_call.json`; do not erase it to obtain an extra sample. Any authorized continuation must account for its persisted response and follow the locked stop/retry policy or a standalone amendment.

## Measurement boundaries

The immutable baseline is imported from the prior-code worktree. `temporal.py` receives only source records, a query and vectors; it imports no corpus-authoring or scoring code. `corpus*.py` create source and measurement manifests. The confirmation driver uses labels only for oracle construction and separated measurement. `score_blind.py` reads only the sealed blind surface and completeness gate. Outcome analysis opens the mapping and mechanism traces only after committed scoring.

The implemented study uses the shipped 32,000-character retrieval allowance and identical additive continuity, while recording exact prompt tokens. It is not a matched-token-spend experiment. All seven query types share a restricted synthetic generator, and only T1/T2 constitute the primary reader contrast. Five seed outputs do not create five independent sessions.
