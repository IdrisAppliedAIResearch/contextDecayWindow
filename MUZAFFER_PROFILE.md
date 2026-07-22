# Research Profile

## Active project

- Repository: `contextDecayWindow`
- Research direction: bounded, retrieval-constructed conversational memory with STM and LTM layers
- Local inference hardware: NVIDIA RTX 5090
- Current local inference model: Qwen3.6 27B UD-Q6_K_XL served by llama.cpp
- Embedding model: Qwen3-Embedding-0.6B

## Study status

### Study 003 — Complete (PARTIAL)

- Accepted run: `study_003_full_002`
- Rubric: 12.0 / 13.0
- Success bars: 2 of 3 passed
- Middle-plant recall: 3.0 / 3.0
- Final topic count: 1 (bar passed; turn-120 over-merge caveat)
- LTM: 21 of 90 evaluated episodes promoted; 21 unique rows; 23.33% evaluation promotion rate
- Promotion events: exactly turns 31, 61, and 91
- Primary failure: full four-domain enumeration omitted Renaissance art and monetary policy

### Study 004 — Complete (PARTIAL)

- Accepted v4 run: `study_004_full_002`; same-settings v3 control: `v3_control_002`
- Rubric: v4 7.0 / 13.0 and Q14 0.0; control 11.0 / 13.0 and Q14 0.0
- Success bars: 1 of 3 passed — consolidation purity only
- Retrieval: LTM contributed on all 90 eligible turns; 450 LTM placements, one deduplication, and zero STM-displacement events
- Final LTM: 12 episodes — nine civil-engineering episodes plus one generic episode from each later domain
- Promotion events: turns 31, 61, 91, and the turn-111 final-domain flush
- Consolidation: five final topics and zero cross-domain merges
- Primary failure: promotion selectivity omitted all later-domain rubric plants, while targeted recall regressed against the control
- Next target: dream-cleaning/factual-salience and domain-diversity promotion, plus a tagged/read-off ablation
- Active LTM retrieval is implemented but not validated as beneficial

**Last updated:** July 21, 2026
