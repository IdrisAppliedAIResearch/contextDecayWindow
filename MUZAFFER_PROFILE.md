# Research Profile

## Active project

- Repository: `contextDecayWindow`
- Research direction: bounded, retrieval-constructed conversational memory with STM and LTM layers
- Local inference hardware: NVIDIA RTX 5090
- Current local inference model: Qwen3.6 27B UD-Q6_K_XL served by llama.cpp
- Embedding model: Qwen3-Embedding-0.6B

## Study status

### Scoring and post-study corrections - July 29, 2026

- The scoring audit covers Studies 001-009 only. It changed 19/222 scores.
- Study 002 Arm A corrected 8.0 -> 5.5; Arm C corrected 13.0 -> 8.5.
- The residual estimate is extrapolated, not observed: 3/26 control
  disagreements applied to 143 unreviewed items gives 16.5 expected, reported
  informally as about 20.
- Study 010's exploratory 21.5/23 and 16.5/23 are unaudited and not directly
  comparable to the corrected series.
- Study 010 LTM Q13/Q14 serialized to 53,726/53,839 characters against a 32k
  budget. The compact-store conclusion is withdrawn; the separate 27,154
  context peak survives as a serialized-prompt `characters // 4` estimate.
- AS-001's Branch D primacy verdict is invalid. Rank-27 Q4 first enters at
  108,432 characters under the joint N-first ranking/packing and budget.

### Study 003 — Complete (PARTIAL)

- Accepted run: `study_003_full_002`
- Rubric: 11.5 / 13.0 (post-audit corrected)
- Success bars: 2 of 3 passed
- Middle-plant recall: 3.0 / 3.0
- Final topic count: 1 (bar passed; turn-120 over-merge caveat)
- LTM: 21 of 90 evaluated episodes promoted; 21 unique rows; 23.33% evaluation promotion rate
- Promotion events: exactly turns 31, 61, and 91
- Primary failure: full four-domain enumeration omitted Renaissance art and monetary policy

### Study 004 — Complete (PARTIAL)

- Accepted v4 run: `study_004_full_002`; same-settings v3 control: `v3_control_002`
- Rubric: v4 6.5 / 13.0 and Q14 0.0; control 10.5 / 13.0 and Q14 0.0
- Success bars: 1 of 3 passed — consolidation purity only
- Retrieval: LTM contributed on all 90 eligible turns; 450 LTM placements, one deduplication, and zero STM-displacement events
- Final LTM: 12 episodes — nine civil-engineering episodes plus one generic episode from each later domain
- Promotion events: turns 31, 61, 91, and the turn-111 final-domain flush
- Consolidation: five final topics and zero cross-domain merges
- Primary failure: promotion selectivity omitted all later-domain rubric plants, while targeted recall regressed against the control
- Next target: dream-cleaning/factual-salience and domain-diversity promotion, plus a tagged/read-off ablation
- Active LTM retrieval is implemented but not validated as beneficial

### Study 005 - Complete (PARTIAL)

- Accepted treatment: `study_005_full_001`; seeded Study 004 control:
  `promotion_seeded_001`
- Rubric: treatment 11.0 / 13.0 and Q14 0.5; control 11.5 / 13.0 and
  Q14 0.0
- Bars: formation failed; breadth not evaluable; targeted non-regression
  failed
- Determinism: 30/30 treatment/control prefix prompts and responses matched
  byte-for-byte under seed 5005
- Dreaming: four events at turns 31, 61, 91, and 111; 12 distilled records;
  100% faithful; zero non-content; zero inference calls
- Formation coverage: 2/4 locked domains, civil and monetary; art and marine
  plants were excluded by the top-three salience cap
- Compression: 12/111 dreamed episodes retained (10.81%)
- Primary failure: whole user/assistant episode scoring rewarded long,
  number-rich generated answers over concise user-planted facts
- Next target: atomic extractive spans with role-aware or length-normalized
  factual selection; retrieval diversity remains deferred until formation
  passes
- Active LTM retrieval remains mechanically implemented but not functionally
  validated

### Study 006 — Complete (PARTIAL)

- Atomic span formation reached 4/4 domains with 200 offset-verbatim records
- Zero non-content records and zero inference calls in formation
- Breadth probes remained 0.0/0.0; corrected total 9.0 versus 11.0 control
- Primary finding: formation succeeded and fixed-count retrieval lost breadth

### Study 007 — Complete (PARTIAL, corrected)

- Character-budgeted, diversity-floored retrieval at 32,000 characters
- Formation 4/4; targeted recall 12.0 versus corrected 10.0 control; Q11 0.0
  and Q14 0.5
- Binding correction `fd78018`: model used 10/10 delivered Q11 atomic facts,
  invented none, and lacked seven of 17 required items
- Primary failure: similarity floor selected overviews and uncapped fill went
  entirely to civil; retrieval, not context use, remained the bottleneck

### Study 008 — Complete (STOPPED AT PRE-RUN GATES)

- Registered factorial: density floor/fill cap x episode/span rendering
- Gate 1 confirmed no episode-rendered `k_min` solved fact-aware 4/4 at 32,000
- Arm A replay reproduced Study 007 Q11/Q14 blocks byte-for-byte
- Amendment 001 corrected span accounting after a nominal 28,498-character
  targeted selection rendered as an 83,106-character LTM block
- No `c_fill` from 1 through 50 passed breadth and targeted gates jointly
- No ablation, live run, human scoring, or bar evaluation was performed
- Next target: a newly registered rendering/allocation design that passes both
  gates; endurance remains deferred

**Last updated:** July 29, 2026
