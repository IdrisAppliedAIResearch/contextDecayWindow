# BEAM-001 Amendment 001 - OpenAI embedding and reader models

**Status:** `AUTHORIZED DESIGN AMENDMENT - NO RUN`  
**Date:** August 28, 2026  
**Amends:** `BEAM_001_IMPLEMENTATION.md` at commits
`8d123b333c62ee275161bd35ababd22f7eaee7c8` and
`64385997569b4b8c8afb8ff0f406933150d9de6b`

## 1. Trigger and authorization

Before implementation or BEAM output, the author requested that BEAM-001 use
the OpenAI model pair carried by the HH studies instead of the local generation
and embedding models. The author supplied a temporary API credential and
authorized implementation and execution with durable checkpoints. The
credential remains process-only through `OPENAI_API_KEY`; it is never written
to source, artifacts, manifests, logs or command-line arguments.

No BEAM mechanism output, answer, judgement or outcome field had been opened
when this amendment was written.

## 2. Blocking evidence

This is not a transport-only substitution. HH-002 pins
`text-embedding-3-small` at its default 1,536 dimensions, while the shipped
`episodic-chat` path pins a 1,024-dimensional Qwen3 embedding artifact and
validates that width in package code. Changing the embedder changes CC80
scores, ASPECT parent identities, packed payloads and every HH-003 payload
digest. Therefore the original descriptions of A0 and C0 as byte-identical
deployed HH-003 controls cannot survive this amendment.

The original Part 1 also forbids generated answers and judge calls. A
generation-model pin may be reserved now, but no generation implementation or
call is authorized before Part 1 closes and a standalone live pre-registration
is committed.

## 3. Change

### 3.1 Part 1 embedder

All three BEAM arms use the following shared embedding specification:

- provider: OpenAI Embeddings API;
- model: `text-embedding-3-small`;
- dimensions: 1,536, the HH-002 default;
- input: exact UTF-8 episode or question text already defined by the base
  design;
- corpus calls: deterministic ordered batches, with output rebound to the
  input content hash and position;
- question calls: one question per request, matching HH-002 query handling;
- storage: float32 vectors in a content-addressed, append-only cache; and
- reuse: every episode and question vector is created once and shared read-only
  by all arms.

The canonical JSON model specification, not a nonexistent local model-file
hash, is the model identity. Its SHA-256 and the OpenAI Python package version
are recorded in every cache and run manifest. A cache row records the exact
model, dimensions, input hash, vector width and vector SHA-256. Cache misses
fail in read-only exploration mode.

The 1,536-dimensional width is a study-private adapter boundary. The public
`episodic-chat` package, its defaults and its 1,024-dimensional production
guard are not edited.

### 3.2 Future reader and judge

Any later live registration produced after Part 1 must use
`gpt-4o-mini-2024-07-18` at temperature 0.0 for both answer generation and
blind judging unless a new author-approved amendment is committed before that
registration. Prompt bytes, response format, output limits, transport,
schedule, scorer and rate limits remain open until that registration.

Part 1 makes zero chat-completion calls. An API smoke test during Part 1 may
exercise only the embedding endpoint and is not a reader run.

### 3.3 Arm names and claim boundary

For BEAM output, the arm identifiers become:

- A0 `CC80_OPENAI_COMMON`;
- C0 `STATIC_ASPECT_OPENAI_COMMON`; and
- T1 `PARENT_OPPORTUNITY_ASPECT_OPENAI_COMMON`.

They compare the three registered selection architectures under one shared HH
embedder. They are not byte-identical reproductions of HH-003's deployed Qwen
operating point. The public default remains a guardrail architecture, not a
deployed-payload control. No result may be described as a direct deployed
package comparison without a separate package-port validation under the
production embedder.

### 3.4 Reproduction anchors

Section 7 of the base design is replaced for the amended BEAM run:

1. Frozen pure-function fixtures reproduce CC80 ordering, static-ASPECT
   allocation, packing, rendering and additive-recency composition by ordered
   identity and payload SHA-256.
2. T1 reproduces all 871 committed TC-014 `opportunity` selected identity
   sequences and payload digests from frozen candidate scores; this tests the
   selector independently of the new embedder.
3. A study-private 1,536-dimensional adapter reproduces package ranking,
   selection, packing and rendering behavior on dimension-adjusted synthetic
   fixtures where expected orders are analytically fixed.
4. Two paid embedding smoke requests are persisted and reopened byte-for-byte;
   the first uses one question and the second an ordered episode batch.
5. Reopening a frozen BEAM cache reproduces every stored vector SHA-256 and
   every context payload digest without an API call.

No original HH-003 payload digest is claimed under the amended embedder.

## 4. Unchanged design

The corpus boundary, stable keys, exact messages, latest-32 additive recency,
32,000-character long-term allowance, CC80 0.8/0.2 weights, BM25 parameters,
ASPECT share and facets, one-child parent fan-out, opportunity admission,
deduplication, packing, rendering, outcome separation, three-arm population,
viability gates and Part 1 reporting requirements remain unchanged.

The amendment adds no reader run, scorer, outcome access, model sweep,
dimension sweep, prompt change, retrieval coefficient, budget or fourth arm.

## 5. Preflight additions

- **PF1 Inputs:** record the OpenAI package version and canonical model-spec
  SHA-256; never record credential material.
- **PF2 Mechanism identity:** verify on committed traces that only vector
  production and width changed; every selection and packing rule retains its
  registered behavior.
- **PF3 Gate ordering:** the two-request embedding smoke gate, cache integrity
  gate and read-only reopen gate precede the detached population job.
- **PF4 Reachability:** construct fixtures where each of A0, C0 and T1 differs
  from both alternatives under 1,536-dimensional vectors.
- **PF5 Stable keys:** vectors are keyed by canonical model specification plus
  exact input bytes, never request ids or timestamps.
- **PF6 Reproduction:** all five amended anchors in Section 3.4 pass before
  any BEAM summary.
- **PF7 Feedback:** API responses populate the cache only before exploration;
  context construction remains read-only and query-order independent.
- **PF8 Adequacy:** Part 1 characterizes the normal BEAM scales only and cannot
  establish production-Qwen behavior or 10M behavior.
- **PF9 Surrogates:** matching vector width, successful API calls and stable
  cache digests can all pass while retrieval quality falls. They certify the
  instrument, not answer quality.
- **PF10 Live requirement:** the dated generation-model reservation authorizes
  no answer or judge call. A later standalone registration remains mandatory.

## 6. Runtime checkpoint rule

After local tests and amended anchors pass, make exactly two paid embedding
smoke requests and inspect their persisted records. Launch remaining embedding
population and context construction as a detached process with PID, command
without secrets, progress counters, append-flush-fsync outputs, failure
sentinel and resumable content-hash keys. Once launch health is established,
the agent stops polling; later status is read from durable artifacts.
