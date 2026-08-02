# CC-005 — Eviction and Store Growth

**Pre-registration:** `CC_003_004_005_deployment_closeout.md` at `43588944`
**Branch:** `cc/005-eviction`
**Gated on:** `DECISION_001_dx002_growth_branch.md` (Part 0)
**Artifacts:** `artifacts/cc005/`
**Status:** PASS — documentation and measurement, no eviction implemented

Closes `CC_001` O5 as *stated*.

## 1. How Part 0 resolved the gate

§3.1's first row made the scoping of this part conditional: *"if H-A,
bounded by budget; if H-B/C, a leak to name"*. The answer came in two
pieces and they point different ways.

- **DX-002 returned Branch B.** The Study 010 runner's context was not
  bounded: its `<retrieved_stm>` block was still setting records at turn
  1,000.
- **CC-003's G-E0 found the library bounded.** Replaying the same 1,000
  episodes through `build_context`, the delivered block never exceeded the
  budget and its p95 moved +18 characters.

So for `episodic`, the context path *is* bounded by construction, and
eviction is a disk-and-latency policy after all — but on G-E0's authority,
not on a plateau read off DX-002. Had this part been scoped from DX-002
alone it would have been scoped wrong.

The caveat is worth keeping: the ceiling governs the block `context()`
returns. A caller that assembles a prompt around it inherits exactly the
runner's problem unless it budgets its own additions too.

## 2. What grows

| Path | Grows with | Measured | Verdict |
|---|---|---|---|
| Delivered context | turn count | +18 chars p95 over 1,000 turns; −0.02% window over window | Bounded (CC-003 G-E0) |
| Disk | turn count, linearly | 4,743 bytes/turn marginal; 4.8 MB at 1,000 turns | Cheap |
| Retrieval latency | store size, super-linearly | 190 ms at 1,000 candidates; exponent 1.25 | **Binding** |

Disk is 86% embeddings — 4,096 bytes of float32 per turn against roughly
650 bytes of text. At 10,000 turns the store is about 48 MB. Nothing about
that number ends continuous operation.

Latency does. Clustering is **81%** of the cost at 1,000 candidates, up
from 37% at 50, and its own exponent is 1.54.

## 3. The correction

§3.1 quotes DR-002 as "~40 µs/candidate, exponent 0.96" projecting "~40 ms
at 1,000 candidates and ~400 ms at 10,000". Measuring the same
configuration on the same material to 1,000 candidates gives **190 ms**,
about five times that projection.

DR-002 is not wrong. Its committed sweep runs from 20 to 119 candidates —
six rows, described in its own report as "a 6x range in pool size" — and
inside that range per-candidate cost is flat at 35–43 µs exactly as
recorded. The projections extend that curve **84× beyond its last measured
point**, and per-candidate cost stops being flat shortly after DR-002 ran
out of data: it roughly doubles between 119 and 1,000 candidates.

Two published statements are corrected in `ERRATA.md`:

1. `episodic/README.md` claimed the sweep covered "20–3,000 candidates".
   It covered 20–119. The 3,000 was a cumulative *character* figure from
   the DR-002 report's greedy-trace table, misread as a pool size.
2. The projections built on the 0.96 exponent are withdrawn and replaced
   with measurements to 1,000 candidates and clearly labelled projections
   above that.

The practical consequence is that **the horizon is nearer than the
pre-registration assumed** — seconds per query at 10,000 candidates rather
than the 400 ms §3.1 treats as the number that ends continuous operation.

## 4. The policy, stated

**Unbounded retention. This version evicts nothing.**

§3.4 recommended shipping neither bounded-cost candidate generation nor
archival in v0, on the grounds that building an eviction policy before
anyone has hit the wall is speculative work. That recommendation is
followed, and §3.3's point stands: stating the policy *is* the deliverable.

The stated horizon: **comfortable to a few thousand episodes, unusable in
an interactive loop somewhere before 10,000.**

### Why trimming is not the fix

The obvious move is to keep the pool small by dropping low-similarity
episodes. That is the one operation measured to break retrieval: dropping
the 19 lowest-cosine episodes from a 119-episode pool cost an entire domain
and all known-optimum overlap, despite 4 of the 5 optimum episodes
surviving the cut. The selector clusters over the pool, so tail removal
reshuffles the objective rather than removing options (DR-002).

Any eviction policy therefore has to be evaluated against **domain
coverage**, not against a similarity threshold. The candidate policy
defaults to the full store and the trimming knob keeps its `unsafe_` prefix
with the finding in its docstring.

### The open question, named as one

Latency is dominated by clustering, which is recomputed over the whole pool
on every query. That is a caching and incrementality problem before it is
an eviction problem, and it is out of scope here. ANN was already refuted
at synthetic scale (bakeoff T5). Noting it as the open question it is.

## 5. Deliverables

- [x] Measured disk growth per turn — 4,743 bytes/turn marginal
- [x] Latency curve to the largest store available, projection labelled —
      to 1,000 candidates, projections above that marked as projections
- [x] README growth section with the stated policy and the unsafe-trimming
      finding
- [x] `unsafe_` prefix retained on the trimming API
- [x] **No eviction implementation in v0** — asserted by tests that scan
      the package for eviction entry points and for `DELETE FROM episodes`

21 policy tests; full suite 1,007.

## 6. Boundary

- One machine, one runtime, one quantization, one store. The absolute
  milliseconds are not portable; the exponent and the clustering share are
  the transferable findings.
- The latency curve is measured to 1,000 candidates because that is the
  largest store the program has. Everything above is a fitted projection,
  and a fitted projection is exactly what this part had to correct in
  DR-002's numbers. It is labelled everywhere it appears and should be
  treated with the same suspicion.
- Disk growth is measured with a deterministic stub embedder. Vector width
  and row shape are identical to production, so the byte count is faithful;
  only the vector contents differ, and nothing here depends on them.
- The horizon statement is about this configuration at a 32,000-character
  budget with 16 clusters. It is not a property of the design.
