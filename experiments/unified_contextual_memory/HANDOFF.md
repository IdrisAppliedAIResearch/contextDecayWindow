# Unified contextual memory implementation and evaluation

User authorized end-to-end implementation after accepting design8927134a. Work is on `study/unified-contextual-memory`, not the old LoCoMo timeline branch. Do not restart architecture discussion or ask for the same authorization.

Implementation and development are complete; paired experimental registration20d75b5a plus scoring Amendment001143237b6 govern. Amended preflight6484d67a passed all fourteen focused tests, all1,986 paired identity/termination checks, and exact prompt capacity. Original preflight preserved as `artifacts/preflight_initial.json`. No source/threshold/reader setting may be changed during evaluation.

The owned evaluation runner was launched hidden as PID11496 using `.venv/Scripts/python.exe -X utf8 experiments/unified_contextual_memory/run.py`. Consult durable `artifacts/evaluation/status.json` and `failure.json`, plus `artifacts/runner.err`, for actual state; this note does not certify later progress. The runner goes calibration -> all reader responses -> committed complete raw -> blinded judges/adjudication -> committed raw -> committed scores -> paired results -> evidence diagnostics and REPORT.md. It commits stages automatically. It never retries a pending request or overwrites raw output.

Automation `unified-memory-evaluation-completion-and-failures` is ACTIVE on this thread at30-minute intervals. Its role is deferred continuation/closeout, not intensive model polling. The local health thread watches every15seconds, emits slowdown after120seconds, HTTP fails at600seconds, and stops only its owned server on sustained low VRAM/process exit. If running with fresh status, leave it alone. On terminal failure inspect once and preserve data; on completion verify closeout, push results/update PR and pause the automation.

## Frozen work

- Core `src/unified_memory/`: caption-faithful source adapter, independent cosine control, contextual token encoder/cache, exact extractive references, finite max-product reference/support agenda, explicit exclusion interface.
- Source-only mechanism: zero generative calls, no answer feedback, fixed cues, no hard retrieval item/character/depth caps, direct cosine>=.48 protected, chronological sources. Natural links unresolved; LoCoMo supplies no explicit conflicts. Do not claim automatic event identity or contradiction resolution.
- Independent clean C0 worktree `C:/Users/muzaf/contextDecayWindow-unified-control` at946c373d5edfe9d954391bdbafaed6646607659e. It supplies real separately computed C0 selections. Historical old-adapter1,986 scores/IDs/payloads replay exactly.
- All10conversations/1,986occurrences;1,540primarycats1–4;446adversarialseparate. This is exposed-data development validation, not new transfer. Shared caption repair means old scores are not the causal control.
- Qwen3-Embedding-0.6B Q8_0 frozen vectors. Last-token contextual pooling, greedy whole-pair8192 encoder windows. Complete-context cache keys; equal token prefix append was not bit-invariant.1920historicalpair vectors reused,1091captionpairs newly captured;9257reference sentences.
- Mismatch99thpercentile thresholds: contextual.4999267833352672/support.5593376334306865/reference.5278224842431918. Multiplicative pathfloor.48 locked before v2 replay.
- v1 degenerate:1232fullconversations/1979>=90%sourcechars/median1.0. Preserved. v2:zero full/70>=90%chars/median.37596 versusC0.20829. These were known development diagnostics, not reader results.
- Native thinkingOFF, serialslot1, sameHH001prompt, seed5005, sameQwen3.8-27B/runtimepins. Exact maximuminput40417; commonctx45056/output4096. MedianC07554.5/C113820.5tokens;pairedfull.21356/.38323. Startupcapacityhad12764MiBfree. No reader reasoning upgrade.
- Unique native-prompt reuse explicitly mapped, including identical arm interventions; not replicates. Initial20questions fixed byfirst2stablekeys/conversation; then remainder, alternatingarmfirst.
- Calibration20calls:2arithmetic+6fixtures×3judgeseeds. Amendment001 adds reasoning-onlyNO_ANSWER and a separate blinded seed9200 adjudication to every real judgeitem. Same-model—not human or independent-model—adjudication supplies primary;3passmajority sensitivity retained. Allgold restricted to measurement after readersealing.
- Primarybars:>=2pp/lower95%conversationclusterCI>0/categoryregressionnot>3pp/selectivityguard forWORKS;>=1pp/sameguardrails forWEAK.20kclusterbootstrapseed70107. Allprespecified. Guardmedianpairedfull<.75 and<10%>=.9 was knowingly chosen using development diagnostics. It is not independent evidence.

## Remaining closeout

Verify terminal state and stage commits. On success, independently recompute primary counts, majority sensitivity, strata and availability×correctness from committed raw/mappings. Inspect missed retrievals only after scored outcomes are sealed. Distinguish annotation availability from sufficiency and reader value. Report limitations and exact questions/gold/answers as useful; no adoption/causal component claim. Update AGENTS/README study ledger and report; push branch/artifacts and reviewable draft PR. A failed gate is an instrument/mechanism-specific finding, not a blanket deterministic-memory failure. Any repair must follow the existing amendment procedure before affected measurement.

Draft PR98: https://github.com/IdrisAppliedAIResearch/contextDecayWindow/pull/98 . Implementation, registration, preflight and calibration were pushed through4f59c540. Update this PR at closeout; do not create a duplicate. Live benchmark outputs remain local until their automatic stage commits and subsequent push.
