# Research Profile

## Active project

- Repository: `contextDecayWindow`
- Research direction: bounded, retrieval-constructed conversational memory with STM and LTM layers
- Local inference hardware: NVIDIA RTX 5090
- Current local inference model: Qwen3.6 27B NVFP4 served by llama.cpp
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

### Study 004 — Planned

- New component: LTM retrieval read path
- Fixes from Study 003: broad-query domain coverage, STM/LTM deduplication, topic-cluster purity checks, final-topic promotion, and positive merge-relabel guard coverage
- Pre-registration not yet committed

**Last updated:** July 19, 2026
