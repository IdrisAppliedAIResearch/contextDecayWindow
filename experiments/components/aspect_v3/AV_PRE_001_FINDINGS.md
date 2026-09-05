# AV-PRE-001 — Does header-stripping change what ASPECT admits?

**Status:** `COMPLETE — registered read returns INDETERMINATE`
**Date:** September 1, 2026
**Cost:** offline. Zero generation calls. 1,540 query embeddings, 20 spaCy passes.
**Runner:** `src/analysis/av_pre_001.py`
**Artifacts:** `experiments/components/aspect_v3/artifacts/av_pre_001/{result.json,rows.jsonl}`

---

## 1. Result in one line

The reproduction gate passes on all 1,540 items. Header-stripping changes the
ASPECT-admitted set on **every one of the 1,540 items** — but by a median
Jaccard of **0.750**, which lands in the middle of the band the registration
declared indeterminate.

| Registered read | Threshold | Observed |
|---|---|---|
| Selection essentially unchanged → hypothesis dead | median J ≥ .9 | — |
| Selection moves materially → three-arm live study | median J ≤ .6 | — |
| **In between → report descriptively, decide with numbers** | .6 < J < .9 | **0.750** |

---

## 2. Gate 1 — reproduction

**1,540 / 1,540 reproduced.** Zero mismatches.

Each item was gated on the sealed per-item `payload_sha256` **and** on every
sealed non-timing field of `detail` — `aspect_count`, `semantic_count`,
`delivered_episode_turns`, `delivered_source_ids`, `dropped_ids`, `recent_ids`,
`chars_delivered`, `chars_wanted`, and the rest.

### A correction to the registered procedure

The registration asked to "gate on **byte-identical** reproduction of
`contexts.json` (`119a3152…c254caae`)". **That gate is unachievable by
construction, and not because anything drifted.** `contexts.json` stores two
measured wall-clock values per item:

```
"search_time": 2.7094 ,  "detail": { "latency_ms": 2709.389200012083, ... }
```

A file containing measured latencies can be reproduced only by copying it. The
digest was therefore used the one way it is meaningful — the committed artifact
was verified intact against `119a3152…c254caae` before anything read it — and
the *allocation* was gated on the sealed, timing-free fields instead. That is
what "if this does not reproduce, stop" was protecting, and it holds at 1,540/1,540.

### Embedder identity

The store-open sentinel gate passed on all ten stores: the pinned
Qwen3-Embedding-0.6B Q8_0 artifact (`06507c7b…`) re-embeds `SENTINEL_TEXT` to
the vector stored at HH-003 time. Given [[llama-cpp-build-is-the-identity]] this
was the live risk in moving machines, and it is closed. `CarriedEmbedder` runs
`n_gpu_layers=0, n_threads=1` — HH-003's embeddings were CPU and single-threaded,
so no GPU was needed for this stage.

The NF-004 embedding cache (`nf004_holdout_embeddings.db`, `file_sha256
96656024…`) was verified against its manifest but **was not needed**: the ten
sealed HH-003 stores carry their episode vectors as BLOBs, so only the 1,540
query embeddings had to be recomputed.

---

## 3. Gate 2 — the contrast

One change only: the header regex is stripped from the text handed to facet
extraction. CC80 ranking, scores, budget, `aspect_share`, greedy rule, packing,
renderer and recency are frozen. Episode embeddings are untouched, and
`additive_weight` reads the *rendered* episode, so every candidate's cost is
identical between arms.

**Header regex re-verified per conversation as the registration required: it
matches 100.0% of messages in all ten conversations** (both `user_message` and
`assistant_message`, 2 × every episode, no exceptions).

| | Value |
|---|---|
| Median aspect-set Jaccard | **0.750** |
| Mean | 0.747 |
| p10 · p25 · p75 · p90 | 0.639 · 0.690 · 0.805 · 0.850 |
| Min · max | 0.532 · 0.950 |
| Items with **identical** ASPECT admission | **0 / 1,540** |
| Items whose delivered payload changed | **1,540 / 1,540** |
| Mean episodes added · dropped per item | 5.05 · 5.65 |
| Mean `aspect_count`, v1 → clean | 36.68 → 36.08 (−0.61) |

### The distribution is narrow and sits inside the band

Only **44 items (2.9%)** reach the ≥ .9 "inert" threshold. Only **54 items
(3.5%)** reach the ≤ .6 "moves materially" threshold. **93.6% of items sit
strictly inside the indeterminate band.** This is not a bimodal mixture of
unaffected and transformed items being averaged into the middle — it is a
uniform, moderate shift applied to essentially every item.

### It is substitution, not a count change

The channel admits 36.7 episodes and replaces about 5.6 of them while adding
5.0 — roughly **15% turnover of the ASPECT channel**, with the admitted count
almost unchanged (−0.61). Cleaned facets are very slightly more expensive per
admission; they are not admitting a different *number* of episodes, they are
admitting different ones.

### It is stable across conversations and across the split

| Conversation | n | median J | added | dropped | Δ aspect | split |
|---|---:|---:|---:|---:|---:|---|
| conv-26 | 152 | 0.823 | 3.26 | 4.02 | −0.76 | dev |
| conv-30 | 81 | 0.841 | 3.38 | 3.88 | −0.49 | dev |
| conv-41 | 152 | 0.744 | 5.12 | 5.57 | −0.45 | **holdout** |
| conv-42 | 199 | 0.738 | 5.36 | 6.07 | −0.71 | **holdout** |
| conv-43 | 178 | 0.718 | 5.65 | 6.38 | −0.73 | dev |
| conv-44 | 123 | 0.714 | 5.59 | 6.59 | −1.01 | dev |
| conv-47 | 150 | 0.711 | 6.37 | 6.88 | −0.51 | **holdout** |
| conv-48 | 191 | 0.780 | 5.12 | 5.27 | −0.16 | **holdout** |
| conv-49 | 156 | 0.738 | 5.17 | 5.75 | −0.58 | dev |
| conv-50 | 158 | 0.736 | 4.59 | 5.33 | −0.74 | dev |

Range 0.711–0.841 across ten conversations. Development split 0.756, held-out
split 0.744 — a 0.012 gap. Whatever this intervention does, it does the same
thing on the four conversations no availability study has ever touched.

### What the reader would actually see

The ASPECT channel is only part of the delivered payload — 32 recency episodes
and the protected semantic half are also in there, and the semantic half is
identical between arms by construction. Measured on the **full delivered
context**, the median Jaccard is **0.864** (min 0.723, max 0.976).

So the honest framing of the reader-visible change: about **14% of the delivered
episode set turns over**, on every single item.

---

## 4. What this does and does not license

**Established.** The hypothesis is not dead. Header-stripping is not inert — it
is inert on zero items out of 1,540, changes ~15% of the ASPECT channel and ~14%
of the delivered context, and does so uniformly across all ten conversations and
both splits. The reproduction gate that makes any of this interpretable holds at
1,540/1,540.

**Not established.** That the change is an *improvement*. AV-PRE-001 measures
displacement, not quality, and was only ever designed to. A 14% turnover in
delivered context is large enough that a reader could plausibly answer
differently, and nothing here says in which direction.

**The reason for caution is on the record.** [[instrument-band-is-three-points]]
— five identical replicates of a prior study scored 8/8/8/8/11. A live contrast
this size needs enough items to clear that band, which is exactly why the
registered plan puts the 1,540-item AV-000 replication first.

---

## 5. Ordering consequence

AV-PRE-001 was a kill gate, and it did not kill. It also did not clear the
three-arm study on its own terms — the registration reserved that for J ≤ .6.

Per §6 of the handoff the order is unchanged and independent of this result:
**AV-000 comes next and gates everything.** If ASPECT-v1's +14 does not
replicate under the local reader, the three-arm study has no incumbent to
improve on and the action is to ship `aspect_enabled=False`, which is already
the default. The three-arm study remains conditional and downstream.

Still open before AV-000, unchanged from the handoff §8: the temperature-0
deviation from LV-009's registered `.6` needs registering, with its reason,
before any reader time is spent.

---

## 6. Environment defect found and fixed

ASPECT could not run at all on this machine on arrival. `uv sync` resolved
`typer 0.27.0`, which **dropped its `click` dependency**; spaCy 3.8.14's
`spacy/cli/_util.py` still does `from click import NoSuchOption`, and
`import spacy` pulls in `spacy.cli` unconditionally. Every ASPECT call raised
`EpisodicError: ASPECT requires the optional parser dependencies` — the error
text points at a missing extra, which is not what was wrong.

Fixed by adding `click` as an explicit dependency. The lock diff is exactly one
package (`click 8.5.0`); no other version moved, and `spacy 3.8.14` /
`en_core_web_sm 3.8.0` are unchanged and still the frozen pins ASPECT asserts at
load. Anything that pins spaCy through `typer` transitively is exposed to this
and should pin `click` directly.
