# Aspect v3 — session handoff, cloud to local

**Date:** September 2, 2026
**Branch:** `claude/hh-005-post-mortem-m6jowm` — 6 commits, pushed, tree clean
**Reason for the move:** every remaining step needs hardware or files that exist
only on the local machine. Nothing below is blocked on thinking; it is blocked on
the GPU, the embedding cache and the corpus.

---

## 1. What exists on this branch

| File | What it is |
|---|---|
| `experiments/audits/da_arc/DA_ARC_HH005_POST_MORTEM.md` | Post-mortem on DA-001…101 + HH-004/005 |
| `experiments/components/aspect_v3/AV_000_THESIS_DRAFT.md` | The v3 direction, live-only plan |
| `experiments/components/aspect_v3/AV_ANATOMY_001_WHAT_ASPECT_DOES.md` | Measured anatomy of the deployed extractor |
| `experiments/components/aspect_v3/AV_HANDOFF.md` | This file |

Published companions (readable from any machine, same account):

- DA Arc Post-Mortem — `https://claude.ai/code/artifact/6491c460-4454-420a-afe4-44b22fa79da9`
- Aspect v3 Thesis — `https://claude.ai/code/artifact/8fda627e-f8f4-4656-845f-50c7307d7a9f`
- ASPECT-v1 Anatomy — `https://claude.ai/code/artifact/d53ca2d3-a59b-4da0-b085-c05252be040e`

---

## 2. Picking it up locally

```bash
git fetch origin claude/hh-005-post-mortem-m6jowm
git checkout claude/hh-005-post-mortem-m6jowm
uv sync                      # spaCy + en_core_web_sm 3.8.0 are already pinned in pyproject.toml
```

The conversation history does not transfer. This document plus the three above
are the state. Nothing else from the session is needed.

---

## 3. Decisions already made — do not re-litigate

1. **Availability is not an endpoint anywhere in this arc.** It has disagreed
   with live reader outcomes in both directions (TC-011/HH-003, DA-098/HH-005).
   No AV study reports it as a primary, secondary, or promotion criterion.
2. **The reader is the local Qwen3.8 stack**, not the paid API. Cost is no longer
   a reason to defer a live check.
3. **Reader runs greedy at temperature 0**, deviating from LV-009's registered
   `.6`. Reason: one sample per arm at `.6` makes labels noisy, and HH ran at 0,
   so this also makes replication cleaner. *This deviation is not yet registered
   and should be, with its reason, before AV-000.*
4. **The renderer stays frozen** at `<episode turn="N">`. LV-009 and HH-005 each
   changed selection and presentation together and neither can attribute its
   result. v3 changes one thing at a time.
5. **Development / confirmation split.** HH-003 spans ten conversations; NF-004
   and the whole DA arc selected on six. Develop on those 848 items; confirm on
   the 692 in `conv-41`, `conv-42`, `conv-47`, `conv-48`, which no availability
   study has ever touched. No arm ships on a development-split result.
6. **The five-arm share sweep is retracted.** Testing `.5/.25/.125` asks how much
   of a mechanism to apply before anyone established what the mechanism does.
   Superseded by the single hypothesis in §5.

---

## 4. What was blocked in the cloud, and why local unblocks it

| Blocker | Where it lives | Unblocks |
|---|---|---|
| Embedding cache `nf004_holdout_embeddings.db` — 2,749 × 1024 f32, 13.3 MB. `*.db` is gitignored; only the digest manifest is committed. | recorded as `C:\Users\muzaf\PycharmProjects\contextDecayWindow\experiments\components\biological_memory\nf_004\artifacts\` | Any CC80 re-ranking, therefore any re-run of `_protected_aspect`, therefore §5 |
| LoCoMo corpus `locomo10.json` | recorded as `C:\Users\muzaf\Downloads\locomo10.json` in `hh005_contexts.py` | Building any new context set |
| RTX 5090 + `Qwen3.8-27B-UD-Q4_K_XL.gguf` + llama.cpp on `127.0.0.1:8000` | local, via `start-model.ps1` | Every live arm |

Verify the cache before trusting it — the committed manifest records
`file_sha256 96656024f79a360798be1c9461585ac47a2b6d6bdfb20d9357d52206e860874c`
and `content_sha256 2e73bff9178d054e0638a20c6af87d760fdcbe14348f921c5f9052e8df6d4892`,
2,749 entries, dimension 1024, dtype float32, call shape `solo`, model
`06507c7b…`. A mismatch means the cache drifted and nothing downstream is
comparable to HH-003.

---

## 5. The immediate next action

**AV-PRE-001 — does header-stripping change what ASPECT admits?**
*Offline. No model calls. Needs only the embedding cache and the corpus.*

The anatomy note measured that 33.6–41.1% of ASPECT's facet mass comes from the
`H:MM pm on D Month, YYYY | Speaker:` header inside `user_message`. What it did
**not** establish is whether removing that changes the *selection*. If the
admitted set barely moves, the hypothesis dies here for the cost of an afternoon
and no reader time is spent.

Procedure:

1. Rebuild HH-003's ASPECT-on allocation exactly, from the sealed cache, and
   gate on **byte-identical** reproduction of `contexts.json`
   (`119a3152c5c3c300df34930a42dbb96e2454e960e48a84de2b9964d7c254caae`) across
   all 1,540 items. If this does not reproduce, stop — nothing else is
   interpretable.
2. Re-run the same allocation with one change: strip the header regex from the
   text handed to `prepare_facets`. **Everything else frozen** — CC80 ranking,
   scores, budget, `aspect_share`, greedy rule, packing, renderer, recency.
   Embeddings are unchanged, because `searchable_text` still feeds CC80 as
   before; only facet extraction sees the stripped text.
3. Report, per item and in aggregate: Jaccard between the two aspect-admitted
   sets, count of episodes added and dropped, and change in `aspect_count`.

Registered read before running, so the outcome cannot be reinterpreted after:

- **Median Jaccard ≥ .9** → selection is essentially unchanged. The header
  contamination is real but inert. The hypothesis is dead; do not take it to a
  reader. Record the negative and move to the share sweep or to AV-000 alone.
- **Median Jaccard ≤ .6** → selection moves materially. Proceed to the three-arm
  live study (`CC80` · `ASPECT_v1` · `ASPECT_clean`) on the development split.
- **In between** → report descriptively and decide with the numbers in hand, not
  in advance.

The header regex used in the anatomy measurement, which matched 208/208 episodes
in conv-26 and should be re-verified per conversation before use:

```python
HDR = re.compile(r'^\s*\d{1,2}:\d{2}\s*[ap]m on \d{1,2} \w+, \d{4}\s*\|\s*[^:]{1,30}:\s*', re.M)
```

---

## 6. Then, in order

1. **AV-000** — replicate HH-003's ASPECT-on/off contrast on all 1,540 items
   under the local reader. ~3,080 reader calls ≈ 3.0 h, 9,240 judge ≈ 1.5 h.
   Gates everything: if ASPECT-v1's +14 does not replicate, the answer to
   "does the architecture work" is no, and the action is to ship
   `aspect_enabled=False` — already the default.
2. **The three-arm study**, only if AV-PRE-001 says selection moves.
   Development split, then held-out confirmation.
3. **AV-003 write-time facet cache** — independent of all of the above, and worth
   doing whichever way they land. Facets on append, `facet_bundle` threaded
   through `_chat_context`, gated on byte-identical allocation. Target
   2,522.7 ms → under 100 ms. This is the difference between an aspect path that
   can ship and one that cannot.

---

## 7. Corrections made during the session — do not reintroduce

- **AV-002 as originally written was impossible.** HH-003 seals `aspect_count`
  and `coverage_count` as scalars; there is no greedy `order` or `marginal`
  trace. Marginal gains and any minimum-share counterfactual need a re-run.
- **Evidence annotations cover 848 of 1,540**, not all of HH-003. Of its 46
  ASPECT rescues, 30 fall inside NF-004's six holdout conversations; of the 32
  losses, 15.
- **The `</user_>` junk facets in my first pass were my artifact, not the
  pipeline's.** `searchable_text` is `user_message\nassistant_message` with no
  XML; the tags are added by the renderer afterwards. The *timestamp*
  contamination is real; the *markup* contamination was not.
- **The returned-semantic-slack channel is not a confound** for HH-005's −16.
  Measured across all 1,540 HH-003 ASPECT items: median 1, mean 0.6, max 3.

---

## 8. Open items not yet addressed

- The temperature-0 deviation (§3.3) needs registering before AV-000.
- PR #91 is still open and unmerged. This branch does not depend on it, but the
  HH-004 erratum recommended by the post-mortem belongs in that PR's scope, not
  this one.
- The post-mortem recommends a status marker in
  `experiments/comparisons/hh_004/` recording that the run is a valid ablation
  but not the registered intent. Not done; also PR #91's scope.
