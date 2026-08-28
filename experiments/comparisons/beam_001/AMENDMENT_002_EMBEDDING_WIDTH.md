# BEAM-001 Amendment 002 - preserve the public store width

**Status:** `AUTHORIZED BLOCKER REPAIR - NO RUN`  
**Date:** August 28, 2026  
**Amends:** `AMENDMENT_001_OPENAI_MODELS.md` at commit `40725e38`

## 1. Trigger

Implementation inspection found that Amendment 001's 1,536-dimensional
default-width call conflicts with the unchanged base requirement to append
every episode through public `EpisodeStore.append()`. The public package
validates exactly 1,024 float32 values in `embed_solo()` and uses that guard on
store open, append and query. A 1,536-dimensional vector cannot enter that path
without editing a carried subsystem, which the base design and Amendment 001
both prohibit.

No implementation file, embedding request or BEAM mechanism output existed
when this repair was written.

## 2. External capability check

The official OpenAI Create Embeddings API reference, checked August 28, 2026,
states that `dimensions` is supported by `text-embedding-3` and later models:

`https://developers.openai.com/api/reference/resources/embeddings/methods/create`

The official GPT-4o mini model page still lists the requested dated snapshot:

`https://developers.openai.com/api/docs/models/gpt-4o-mini`

These checks establish API support only. The paid smoke gate still determines
whether the supplied account can call the pinned models.

## 3. Repair

Amendment 001 Section 3.1 changes in one field:

- model: `text-embedding-3-small`;
- requested dimensions: **1,024**, not the model's 1,536 default.

The canonical model specification and its SHA-256 include the explicit
`"dimensions":1024` field. Every API request supplies it. Every response and
cache row must contain exactly 1,024 finite float32 values.

The embedder remains the HH model family but is not HH-002's exact embedding
call, because HH-002 used the 1,536-dimensional default. Reports must say
`text-embedding-3-small at an explicit 1,024 dimensions`; they may not call the
embedding setup byte-identical to HH-002.

## 4. Restored public path

The study-private OpenAI embedder implements the public package's callable
embedder protocol and reports the canonical model-specification SHA-256 as its
`model_sha256`. Each arm uses an `EpisodicConfig` whose `embedder_sha256` is
that same value. The public package source and its dimension constant remain
unchanged.

All episode formation must again pass through `EpisodeStore.append()`. The
embedder serves append, open-sentinel and query vectors from the read-only
content-addressed cache during context construction. A miss fails before
selection; it never makes a hidden network request.

Amendment 001 Section 3.4 item 3 is replaced with:

> A public `EpisodeStore` using the study-private cached OpenAI embedder
> appends, reopens and verifies dimension, model-specification hash, sentinel,
> episode vectors and context payloads without editing package source or
> making a reopen-time API call.

## 5. Preflight consequence

PF2 must distinguish model identity from call identity: the model name matches
HH-002, while the explicit width does not. PF6 fails if any public-store source
file changes, any API request omits `dimensions=1024`, or any returned vector
has another width. All other Amendment 001 and base-design requirements remain
unchanged.
