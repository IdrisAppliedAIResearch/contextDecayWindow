# contextDecayWindow Research Context

## Current state

Study 010 is complete as **STOPPED BEFORE LOCK**. Its source documents are
committed at `ead2f66`. Branch resolution carries no digest and retains the
Study 007 LTM treatment, but the draft requires a Study 009 verdict that does
not exist and repeats the structurally absent Arm S / byte-identical S-L prefix
contradiction already falsified in Study 009. No 1,000-turn script, calibration,
checkpoint implementation, rehearsal, live run, or scoring occurred. A new
author-approved registration must resolve the prefix parity unit and replace
the missing-verdict lock condition before work resumes.

Study 009 is complete as **STOPPED AT THE 35-TURN ARM S ABLATION**.
Registration is `37fff74`; the implementation and offline gates are `f901bda`.
The topic digest failed fact-aware G1 even through `d = 50` and
`B_digest = 50,000`, so the registered contingency dropped S+D. G2 reproduced
Study 007's probe LTM blocks byte-for-byte and G3 proved the pure-STM
composition structurally clean.

Arm S then completed its 35-turn ablation with healthy speed, context, logs,
and leakage checks. The binding STOP was a registration contradiction:
structural Arm S must omit `<retrieved_ltm>`, while cross-arm prompts were also
required to be byte-identical through the empty-store prefix. Raw prompts
differed at turn 1 and seeded responses at turn 3. No full run, human scoring,
null-test verdict, or mechanism analysis occurred.

Study 010 inputs from 009: digest carry is false; Study 007 remains the last
accepted LTM configuration, but Study 009 supplied no STM-versus-LTM verdict.

Study 008 is complete as **STOPPED AT PRE-RUN GATES**. The registered 2x2
retrieval factorial was not run because no `c_fill` from 1 through 50 passed
fact-aware breadth replay and targeted-retrieval preservation jointly at
`B_ltm = 32,000`, `k_min = 1`. Registration is `0a20ef0`; the binding gate STOP
is `4a29540`.

Gate 1 confirmed P1: no episode-rendered `k_min` from 0 through 4 reaches
fact-aware four-domain coverage at 32,000 characters. Arm A's replay reproduced
Study 007's Q11 and Q14 LTM blocks byte-for-byte. No ablation, live inference
run, scoring, or Bars 0–3 evaluation occurred.

## Architecture after Study 008

- Iterative STM retrieval with soft N cap and K similarity retrieval
- User-message embeddings for topic assignment and centroids
- Topic consolidation at 0.45 every 10 episodes, with a probe-bridge guard
- Pinned rule store with deterministic UUIDv5 model-visible rule identifiers
- Permissive append-only raw conversation store; every user/assistant turn is
  retained and marked for dreaming
- Extractive span dreaming at topic transitions and the turn-111 flush
- Shared density score `(named_entities + 2 * numeric_tokens) / word_count`,
  source weighting in formation, cosine dedup at 0.95, and per-topic cap 50
- Verbatim distilled spans with source IDs/turns, role, offsets, density,
  event, and collapsed-source provenance
- Study 007 character-budgeted LTM retrieval with protected per-topic floor,
  containment dedup, and XML-tagged context tiers
- Study 008 factor implementation available behind explicit configuration:
  density or similarity floor, optional per-topic fill cap, episode or span
  rendering, rendering-aware identity/cost/containment, and expanded logs
- Exact serialized span-element charging under Study 008 Amendment 001
- Structural leakage audit over literal references and retrieval import closure
- Fixed seed 5005, single-slot llama.cpp serving, deterministic IDs, and no
  speculative decoding
- Formation, faithfulness, non-content, conditional breadth, and comparative
  non-regression evaluators

## Study 004 result

- V4 scored 7.0/13.0 and Q14 0.0; same-settings v3 control scored 11.0/13.0
- Active LTM contributed on every eligible turn but promotion omitted all
  later-domain rubric plants
- Consolidation purity passed with five final topics and no cross-domain merges
- Binding failure was selective promotion, which motivated Study 005 dreaming

## Study 005 result

- Both arms completed 121 turns on Qwen3.6 27B UD-Q6_K_XL at 50k context,
  2,048 response tokens, and seed 5005
- Same-seed prefix: 30/30 prompts and 30/30 responses byte-identical
- Treatment rubric: Cat 1 3.0, Cat 2 2.5, Cat 3 1.5, Cat 4 2.0, Cat 5 2.0;
  total 11.0/13.0; Q14 0.5
- Control rubric: Cat 1 3.0, Cat 2 3.0, Cat 3 2.0, Cat 4 2.0, Cat 5 2.0;
  total 12.0/13.0; Q14 0.0
- Dreaming wrote 12 content records from turns 4/17/20, 31/40/41,
  61/69/84, and 92/105/108
- Faithfulness was 12/12; non-content, marker, inference-call, and dedup counts
  were all zero
- Locked formation coverage was 2/4 domains: civil and monetary present; art
  and marine absent
- Art plant ranks were 18, 28, and 19; marine plant ranks were 11, 16, and 17
  under the top-three policy
- Q11 and Q14 each received five distilled records, but Bar 2 was not evaluable
  because the store-content precondition failed
- Final topics: 5; no cross-domain purity event; full-run bridge guard not
  exercised
- Active LTM retrieval remains mechanically sound but not functionally
  validated

## Study 006 result

- Span formation reached 4/4 domains with 200 offset-verbatim records, zero
  non-content, and zero formation inference calls
- Breadth probes remained 0.0/0.0 because fixed-count retrieval delivered
  insufficient domain breadth
- Targeted score was 10.5 versus Study 005's 11.0; overall PARTIAL

## Study 007 result and binding correction

- Formation remained 4/4; targeted recall passed at 12.0 versus 10.5
- Breadth scored Q11 0.0 and Q14 0.5
- The original report's context-use diagnosis is void
- Binding correction `fd78018`: Q11 used all 10 of 10 delivered atomic facts,
  invented none, and lacked seven of 17 required items
- Retrieval picked art/monetary overviews and assigned all fill to civil;
  the bottleneck remained retrieval

## Study 008 result

- Gate 1: P1 confirmed; first swept episode-rendering 4/4 point was 40,000
  characters with `k_min = 2`
- Gate 2: Arm A probe blocks reproduced Study 007 byte-for-byte
- Amendment 001: content-only charging admitted an 83,106-character span block
  under a nominal 32,000 budget; span arms now charge exact serialized elements
- Joint gates: B reached breadth only at `c_fill = 1`, where targeted allocation
  failed; targeted preservation began at 5, where breadth failed
- At `c_fill = 50`, all targeted fixtures passed but no arm reached fact-aware
  4/4 at both probes
- Binding outcome: STOP before ablation; P2–P5 and Bars 0–3 not evaluated

## Next research target

- Register a new retrieval design that can pass both fact-aware breadth and
  targeted-allocation gates before spending inference
- Leading option: selected span plus minimal surrounding context, with exact
  serialized-unit charging
- Alternative: query-adaptive fill allocation with a pre-registered targeted
  lower bound
- Escalate to formation-side per-domain fact guarantees only if corrected
  rendering/allocation still cannot expose the locked facts
- Preserve fixed-seed, single-slot, deterministic-ID, score-before-log protocol
- Preserve fact-aware complete-row gates and the structural leakage audit
- Keep the 1,000-turn endurance study deferred until breadth recovery passes

## Key files

- Study 008 report: `experiments/study_008/study_008_report.md`
- Gate 1: `experiments/study_008/replay/gate1_rederivation_report.md`
- Joint gates: `experiments/study_008/replay/gate2_report.md`
- Targeted fixture: `experiments/study_008/tests/targeted_fixture_report.md`
- Gate STOP: `experiments/study_008/decisions/DECISION_gate_stop_study008.md`
- Amendment 001:
  `experiments/study_008/amendments/AMENDMENT_001_span_rendered_cost.md`
- Study 007 correction:
  `experiments/study_007/evaluation/position_and_grounding_analysis.md`

**Last updated:** July 26, 2026
