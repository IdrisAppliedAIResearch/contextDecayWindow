# HH-003 Amendment 001 - A_RAG prediction digest transcription

**Date:** August 24, 2026
**Timing:** Before implementation commit, before context construction, and
before any paid API call
**Pre-registration anchor:** `ea5cf2b6`

## Correction

Section 5 transcribed the SHA-256 of HH-002
`artifacts/A_RAG/predictions.json` as:

`bc49bb20a6172dcfa68e3ef825487c776674afa0f95e19cf9509d4dcaea68af`

The actual file digest, re-read by explicit path after the G2 gate failed, is:

`bc49bb20a6172dcfa68e3ef825487c776674afaf0f95e19cf9509d4dcaea68af`

The omitted `f` was a transcription error. The HH-002 artifact is unchanged.
All other registered hashes were re-read by explicit path and match. This
amendment changes no arm, parameter, population, endpoint, gate, or inference.
