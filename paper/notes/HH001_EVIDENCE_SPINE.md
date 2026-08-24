# HH-001 evidence spine

Every number PAPER-002 may use from the head-to-head, with the committed
artifact it came from and that artifact's SHA-256 prefix as of the run commit
`5db0865e`. Hashes are `git show HEAD:<path> | sha256sum`, first 16 hex.

**Standing of the whole block: `REGISTERED`, not `CONFIRMATORY`.** LoCoMo is
exhausted on both splits (NF-004 ran the holdout), so nothing here earns
sealed-holdout standing. The endpoint is new and no arm was tuned against it,
which is worth something and is not worth that. See `HH_001_DEVELOPMENT_PLAN.md`
§2 and `SCOPE_LIMITS.md`.

**Substrate: local.** Every arm, including Mem0's own internal calls, ran on
`Qwen3.8-27B-UD-Q4_K_XL` at `127.0.0.1:8000`. **No number here may be placed
against Mem0's published 66.88%**; that figure was produced with GPT-4o-mini and
is not this study's denominator. See §6.

---

## 1. The registered contrast

`result.json` · `7fa4119c29f06b1c`

| id | value | what it is |
|---|---|---|
| H1 | **+7.7 points** | A2 `CDW_PAIR` over A3 `MEM0`, judged accuracy, 300 paired items |
| H2 | **46 gains / 23 losses / 231 ties** | paired discordant counts, judged |
| H3 | **p = 0.0038** | one-sided exact binomial sign test, judged |
| H4 | **ratio 2.00** | gains to losses, judged |
| H5 | **+9.7 points, 40 gains / 11 losses, p = 2.85e-05** | the same contrast under the deterministic containment endpoint |
| H6 | **both endpoints agree in sign** | the registered guard passed; a directional claim is permitted |

## 2. Every arm

`result.json` · `7fa4119c29f06b1c`

| id | arm | judged | contained | judged unanimity |
|---|---|---:|---:|---:|
| A0 | `NO_MEMORY` | 0.000 | 0.000 | 1.00 |
| A1 | `FULL_CONTEXT` | 0.613 | 0.320 | 0.87 |
| A2 | `CDW_PAIR` | 0.563 | 0.313 | 0.85 |
| A4 | `RAG_FIXED` | 0.550 | 0.287 | 0.89 |
| A3 | `MEM0` | 0.487 | 0.217 | 0.87 |

**A0 = 0.000 is the floor and it is exact.** The reader answered none of the 300
items without a memory block.

## 3. What the write path cost

`cost/mem0_ingest.json` · `a9653199d0d8317f`,
`pilot/mem0_observation.json` · `9fe9d7ca25c952ab` and
`cost/mem0_ingest_tokens_corrected.json` · `1373ac7f03c5ff81`

| id | value | what it is |
|---|---|---|
| C1 | **1,646** | generative calls Mem0 spent ingesting the six conversations |
| C2 | **1.0 per message pair** | measured. Mem0's paper describes `1 + n`; this build spent one |
| C3 | **284 minutes** | wall clock for that ingest |
| C4 | **0** | generative calls this component spends on the same corpus. Architectural, not measured |
| C5 | **~1,131 prompt tokens per ingested pair**; **1,862,108** across the whole ingest | `cost/mem0_ingest_tokens_corrected.json`, RECOMPUTED: the 86.6% of the ingest the counter overlaps, scaled by wall clock |
| C5a | **1,612,718** | MEASURED floor. Prompt tokens inside the overlap, no scaling |
| C5b | **1,843,446** | completion tokens, whole ingest, same scaling. Mem0 writes back almost as much as it reads |
| C5c | **the per-pair cost does not climb with store size** | slope **−0.444** tokens/min per stored memory over 246 → 1,816 memories |

**C5 has been corrected twice, in opposite directions. Read both.**

*First correction.* An earlier draft said "~1,000 prompt tokens per stored turn".
That divided an early, short window by *memory writes* and labelled the result
per *turn* — two errors compounding, understating Mem0's cost roughly fourfold.
It was caught by adversarial review, not by the gate, because the gate checks
that a number is in this file and not that this file is right. **It fixed the
denominator. The numerator was the defect.**

*Second correction (Amendment 001, 2026-08-21).* The 5,988,818 was a delta on a
**cumulative, process-wide, un-reset** counter, taken across the whole sampling
window. Mem0's history table dates its last write at `20:31:29Z`; the window ran
to `22:15:19Z`. **The counter ran 105 minutes past Mem0's last write and booked
4,376,100 prompt tokens in those minutes — 73% of the published figure — to the
reader phase sharing the server.** The published value was inflated **3.22×**,
this time in this programme's own favour. The uncovered head is excluded rather
than added back: its cumulative prompt/predicted ratio is 1.424 against the
overlap's 1.010, so it holds the pilot and the probes too.

The "climbs through the ingest" clause went with it. It was asserted from the
same contaminated tail and the clean overlap contradicts it. The drift that is
real is in **latency**, 1.13× first-to-last decile (I2), not in tokens.

**C1–C4 are untouched, and C1 is the load-bearing number.** 1,646 generative
calls against zero is the architectural comparison; it was never a token count
and no bar moves.

Derivation: `scripts/hh001_ingest_token_correction.py`. Every field is derived
from hashed inputs; none is typed. See
`../../experiments/comparisons/hh_001/amendments/AMENDMENT_001_ingest_token_window.md`.

## 4. What the write path lost

`cost/mem0_store_probe.json` · `e2a837604f3e6c4a`,
`cost/mem0_ingest.json` · `a9653199d0d8317f`,
`result.json` · `7fa4119c29f06b1c`

| id | value | what it is |
|---|---|---|
| L1 | **249 of 315 retained; 66 absent (21%)** | gold answers stated verbatim in the source, checked against Mem0's whole store |
| L2 | **1,811 memories from 1,646 pairs** | 1.10 per pair |
| L3 | **509 of 1,646 pairs (31%) produced no memory at all** | derived: 1,137 write bursts against 1,646 calls |
| L4 | **16 of 1,646 (0.97%) extractions returned malformed JSON** | logged by Mem0 and discarded; counted from the ingest log |
| L5 | **0.68 to 0.86** | per-conversation retention range |
| L6 | **A3 delivered the answer into its block for 79 of 108 items (0.732)** | against A2's 101/108 (0.935), A4's 94/108 (0.870), A1's 108/108 (1.000) |

**L1 is an upper bound on loss and must be written as one.** It is a containment
test over Mem0's memory text, so a *preserved paraphrase counts as absent*. The
test can overstate extraction loss and cannot understate it.

**L6's denominator differs from L1's** — 108 is the subsample's eligible items,
315 is the whole answerable population. They are not the same measurement.

## 5. Cost at read, latency, size

`result.json` · `7fa4119c29f06b1c` and `cost/storage.json` · `adcc2ea410046e22`

| id | arm | prompt tokens / read | block build p50 | store bytes | bytes / turn |
|---|---|---:|---:|---:|---:|
| R1 | A0 | 82 | 0.000 s | — | — |
| R2 | A1 | **18,187** | 0.000 s | — | — |
| R3 | A2 | 4,009 | **0.010 s** | 7,176,599 | 2,229 |
| R4 | A4 | 3,904 | 0.005 s | 2,789,194 | 866 |
| R5 | A3 | **3,392** | **0.413 s** | **42,771,582** | **13,283** |

| id | value | what it is |
|---|---|---|
| R6 | **41×** | A2's block-build speed over A3's, p50 |
| R10 | **judged unanimity 0.853 / 0.870 / 0.891** | A2, A3, A4 replicate agreement. **A2's is the lowest of the three memory arms** |
| R11 | **A4 stores 2.8 MB and reads at 3,904 tokens** | smaller and cheaper than A2 on both, at 0.550 against 0.563 |
| R7 | **5.96×** | A3's store size over A2's, qdrant only, excluding its 692,224-byte history log |
| R8 | **222×** | A1's prompt tokens over the cheapest arm (A0) |
| R9 | **A3 is the cheapest memory arm per read** | 3,392 against A2's 4,009. The write cost and the read cost run in opposite directions |

## 6. Ingest latency against store size

`cost/mem0_ingest_latency.json` · `0ad65363b635b6e7`

| id | value |
|---|---|
| I1 | p50 **11.9 s**, p95 **34.8 s** per ingested pair |
| I2 | first decile mean **14.5 s**, last decile **16.5 s**, ratio **1.13×** |
| I3 | **1,137 write bursts** measured, store reaching **1,825** memories |

**I3 is not the call count.** Pairs that wrote nothing leave no burst, so the
latency figures describe the 69% of pairs that wrote something — likely the
slower subset, since a no-op returns faster. The artifact carries this note.

## 7. Instrument and population

`commitments.json` · `c143620b83c3f300`,
`subsample_manifest.json` · `19d4e438b5a429da`,
`pilot/contamination.json` · `b6fc5716856d753e`,
`pilot/timing.json` · `84acda3f79dbf125`,
`runtime/reader.json` · `e950d59be2692e2d`

| id | value |
|---|---|
| P1 | 300 items, seeded and stratified from **850 answerable**; 254 adversarial excluded, and why is in the plan §3.1 |
| P2 | 3 replicates per item per arm; the confirmatory minimum is 5 and this is below it, by design |
| P3 | 16,000-character matched budget, `len()` of the exact string handed to the reader |
| P4 | contamination probe **0 of 50**, all fifty replies `I don't know`, none empty |
| P5 | seed `5005 + replicate`, so replicates vary and the unanimity rate measures something |
| P6 | reader `Qwen3.8-27B-UD-Q4_K_XL`, SHA-256 `bee238bb…`, one slot, ctx 200000 |
| P7 | one embedder for every arm that embeds, verified **bit-identical** to the sealed cache |
| P8 | commitments written and hashed **before** the run: `c143620b83c3f300` |

## 8. What this block does not license

Grep-able prohibitions. These replace, for the locally-run comparison only, the
blanket ban in `COMPETITIVE_LANDSCAPE.md` §5.

| Forbidden | Why |
|---|---|
| Any comparison to Mem0's **published** 66.88%, or to any published LoCoMo score | Different substrate, different judge, different endpoint. Mem0 published on GPT-4o-mini |
| "Mem0 loses 21% of memories" | L1 is answers absent from the store under a containment test, not memories lost, and it is an upper bound |
| Any claim about Mem0's **graph** variant, Zep, A-MEM, HippoRAG or LangMem | None was run. `DO_NOT_WRITE.md` item 35 still binds for every system except Mem0 |
| `CONFIRMATORY` standing, or any sealed-holdout language | LoCoMo is exhausted |
| Any claim that the component's **breadth** or multi-domain behaviour beat anything | A2 is `P_PAIR_RANK` and carries no coverage objective. `SCOPE_LIMITS.md` §2 |
| Reading A2 ≈ A4 as evidence about NF-004 | A4 is not NF-004's control. `SCOPE_LIMITS.md` §1 |
| Any ingest-cost figure quoted without the read-cost figure beside it | R9. They run in opposite directions and half the picture is not the picture |
| "Zero inference calls" | Withdrawn. `DO_NOT_WRITE.md` item 1. **No generative calls**; an embedder is resident |
| Generalizing beyond this reader, corpus, budget and pair of configurations | One reader, one corpus, 300 items, 3 replicates |

---

## 9. Derived and unit-converted values

The paper reads in megabytes and milliseconds; the artifacts record bytes and
seconds. Every conversion is listed here with its source, so a reader can check
the arithmetic rather than trust it. The number-trace gate reads this section.

| Paper value | Source | Arithmetic |
|---|---|---|
| **7.2 MB** | `storage.json` A2 `total_bytes` 7,176,599 | ÷ 1e6 |
| **2.8 MB** | `storage.json` A4 `total_bytes` 2,789,194 | ÷ 1e6 |
| **42.8 MB** | `storage.json` A3 `total_bytes` 43,463,806 less the 692,224-byte history log | 42,771,582 ÷ 1e6 |
| **692,224 bytes** | measured on `mem0_history.db` | none; quoted in bytes because ÷1024 gives 676 KB and ÷1000 gives 692 kB, and the two disagree |
| **413 ms** | `result.json` A3 `block_seconds_p50` 0.413 | × 1000 |
| **10 ms** | `result.json` A2 `block_seconds_p50` 0.010 | × 1000 |
| **90,713 / 45,984 characters** | `Conversation.chars`, the delivered string | none |
| **~22,700 tokens** | 90,713 ÷ 4 | the same 4 chars/token the runner uses for A1's allowance; an estimate and written as one |
| **369 / 680 turns** | `Conversation.turn_count`, min and max over the six | none |
| **+11.9 / −3.1 / +2.0 / +14.9 points** | `result.json` `long_horizon.by_arm`, A2 minus A3 by depth bucket | × 100 |

**One correction this section caused.** The paper and the plan both said the
longest conversation was **90,034** characters and the shortest **45,616**.
Those figures summed the per-turn renderings and dropped the newline that joins
them — one character per turn. The delivered string, which is what the budget
measures, is **90,713** and **45,984**. Corrected 2026-08-20; found by the gate.
