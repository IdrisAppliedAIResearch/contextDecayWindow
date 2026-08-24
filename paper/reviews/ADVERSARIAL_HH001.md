# Adversarial review — HH-001 in PAPER-002

Reviewer: adversarial pass, independent of the author's self-review.
Target: `paper/PAPER_002.md` at HEAD `6555fc7e`, branch `study/hh-001-head-to-head`.
Artifacts read directly: `experiments/comparisons/hh_001/artifacts/dev/result.json`,
`cost/storage.json`, `cost/mem0_ingest.json`, `cost/mem0_store_probe.json`,
`cost/mem0_ingest_tokens.json`, `commitments.json`.
Constitution read: `paper/notes/HH001_EVIDENCE_SPINE.md`,
`experiments/comparisons/hh_001/SCOPE_LIMITS.md`.

## Verdict

**REVISE.**

The registered contrast itself is clean. +7.7 points, 46/23, p = 0.0038, containment
agreeing at +9.7 / 40 / 11 / p = 2.85e-05 all reproduce from `result.json` to the
digit, and `sign_check.agree = true` licenses the directional claim exactly as §5.1
states it. §5.5 is a genuinely good scope-limits section. The defects are not in the
headline number. They are in the **standing label**, in **four stale sentences the
rewrite missed**, in **one ingest figure that does not reproduce under any denominator
I could construct**, and in **two uncomfortable baselines that are absent rather than
spun**. Nothing here requires withdrawing the head-to-head.

---

## Findings, ranked

### S1 — The standing label in the paper is one level above the artifact's own. `result.json` says DEVELOPMENT.

§5.5: *"**Not confirmatory.** LoCoMo is exhausted on both splits, so this is
`REGISTERED` under §4's taxonomy and does not become `CONFIRMATORY` by being
re-described."*

Two problems, and the second is worse than the first.

1. `result.json` records `"standing": "DEVELOPMENT — not confirmatory, and never
   becomes so"`. The spine header says `REGISTERED`. The artifact and the spine
   disagree, and the paper followed the spine. The artifact path is
   `artifacts/`**`dev`**`/`, the plan is `HH_001_`**`DEVELOPMENT`**`_PLAN.md`, and
   `commitments.json` carries `below_confirmatory_replicates: true`. Every other
   signal on disk says DEVELOPMENT.
2. **`REGISTERED` is not a level in §4.1.** §4.1 lists five: CONFIRMATORY,
   REGISTERED-OFFLINE, DESCRIPTIVE, NOT DEMONSTRATED, WITHDRAWN. §5.5 cites a
   standing to a taxonomy that does not contain it. And HH-001 cannot be
   REGISTERED-OFFLINE, whose stated requirement is *"zero generative calls"* — the
   judged endpoint spent 900 reader calls per arm plus a judge.

Compounding: §4.1's assignment table is introduced as *"The assignment, **in full**,
so this table is checkable without leaving the paper."* The paper's centrepiece
result is not in it.

**Replacement.** Add HH-001 to §4.1's table as two rows, because it has two endpoints
of different kinds:

| HH-001 judged, A2 over A3, +7.7 (§5.1) | DEVELOPMENT | Scored and live; 3 replicates against the programme's own minimum of 5; the paired sign test, not a variance estimate, is what carries it |
| HH-001 containment, +9.7 (§5.1) | REGISTERED-OFFLINE | Deterministic, model-free, bars hashed at `c143620b83c3f300` first; corpus already observed |

and change §5.5 to: *"this is `DEVELOPMENT` under §4.1's taxonomy — the standing
`result.json` itself records — and does not become `CONFIRMATORY` by being
re-described."* If you prefer `REGISTERED` as a sixth level, define it in §4.1 and
correct `result.json`'s `standing` field to match. Do not leave the artifact and the
paper asserting different grades for the same result.

### S2 — "No system named above was run here." Mem0 was.

Three stale sentences survived the rewrite. All three are the class you asked me to
hunt, and one is in bold.

- **Line 229, §2.1:** *"**No system named above was run here.** Every number
  attributed to one is cited from its publication and labelled as such."* The systems
  named above are Letta, Mem0, Zep, HippoRAG, GraphRAG. Mem0 was installed and run.
  The second sentence is now false too: §5 attributes measured numbers to Mem0.
  **Replace with:** *"**Of the systems named above, one was run here: Mem0 2.0.18, in
  §5.** Every number attributed to any other is cited from its publication and
  labelled as such."*
- **Line 192, §1.3:** *"No comparison against HippoRAG, Mem0, Zep or Letta was run,
  and §2 says exactly what is and is not being compared."*
  **Replace with:** *"Mem0 2.0.18 was run here and only Mem0; no comparison against
  HippoRAG, Zep or Letta was run, and §2 says exactly what is and is not being
  compared."*
- **Line 1715, Provenance:** *"**No number changed in this rewrite**; the ordering and
  the standing labels did."* Contradicted by the spine's own §9 closing note: the
  longest and shortest conversation figures were corrected from 90,034/45,616 to
  90,713/45,984 **during this rewrite, by the gate, on 2026-08-20**. You report a
  KB-conversion correction in the same cycle.
  **Replace with:** *"Two numbers were corrected in this rewrite, both found by the
  number-trace gate and recorded in `HH001_EVIDENCE_SPINE.md` §9; §5's material is
  new. The ordering and the standing labels also changed."*

Line 283 (*"which is all of them except Mem0"*) and line 1455 (*"One of them was run
here"*) are correct. The rewrite reached those two and stopped.

### S3 — §13.10 tells the reader a sealed LoCoMo holdout is still held. §5.5 says it is exhausted.

§13.10: *"The LoCoMo holdout in §6.1 is now the only sealed external evidence this
programme holds, and **four of the ten LoCoMo conversations are likewise spent**."*

The spine header states the opposite, as the reason HH-001 cannot be confirmatory:
*"LoCoMo is exhausted on both splits (NF-004 ran the holdout)."* HH-001 ran six
conversations — `conv-26, 30, 43, 44, 49, 50` in `mem0_store_probe.json`. After §5 all
ten are spent. As written, §13.10 understates a limitation and contradicts §5.5 four
pages earlier.

**Replace the clause with:** *"and after §5's head-to-head all ten LoCoMo
conversations are spent, so that holdout cannot be re-sealed either. This programme
now holds no unspent sealed external corpus."*

### S4 — "roughly a thousand prompt tokens apiece" does not reproduce.

§5.2: *"Mem0 built its store with **1,646 generative calls over 284 minutes**, one
call for every message pair, **roughly a thousand prompt tokens apiece**."*
Spine C5: *"~1,000 prompt tokens per stored turn."*

From `cost/mem0_ingest_tokens.json`: `window_prompt_tokens` = 5,988,818 over
`window_history_rows` = 1,597 (rows 230 to 1,827), cumulative counter ending at
6,305,880.

| Denominator | Result |
|---|---:|
| per history row | 3,750 |
| per pair (1,597 rows ÷ 1.10 memories/pair ≈ 1,452 pairs) | **4,125** |
| per stored turn (2 messages per pair) | 2,063 |
| per pair, cumulative 6,305,880 ÷ 1,646 | 3,831 |
| per turn, cumulative ÷ 3,220 source turns | 1,958 |
| **per call, all 5,545 calls including the 3,899 embedding calls** | **1,080** |

The only denominator that lands near 1,000 is *every call including embeddings*, which
is not "apiece" for a generative call and is not "per stored turn". As attached in
§5.2 — apiece, per message pair — the figure is understated by roughly **4x**.

The error runs in Mem0's favour, so it is not a rescue; it is a transcription error of
the kind you predicted. But it is load-bearing: that clause is the paper's only
quantification of what the generative write path costs in tokens.

**Replacement.** Either strike the clause, or write what the artifact supports:
*"one call for every message pair, and roughly **4,100 prompt tokens** apiece,
measured over a mid-ingest steady-state window of llama-server's cumulative counters —
a slice, not the whole run."* Correct spine C5 in the same edit; it is wrong at
source, which is why the number-trace gate did not catch it.

> **Superseded, 2026-08-21 — this review record is left unedited above.** S4's
> diagnosis was right and its replacement value was not. Every denominator in
> the table above divides `window_prompt_tokens`, and that numerator is not an
> ingest cost: the counter is cumulative and process-wide and ran 105 minutes
> past Mem0's last write, so 73% of it belongs to the reader phase. S4 fixed the
> denominator while inheriting the defect. The corrected figure is **1,131
> tokens per pair, 1,862,108 over the ingest** — and the row this table rejected,
> *per call including embeddings, 1,080*, was rejected for a sound reason but
> happened to land nearest the truth. See
> `../../experiments/comparisons/hh_001/amendments/AMENDMENT_001_ingest_token_window.md`.

### S5 — The exec-summary table reports an architectural claim as a measured win, against the artifact's explicit instruction.

Page 1, inside a two-column head-to-head table:

| Answers absent from the store | **none, by construction** | **up to 21%** |

`cost/mem0_store_probe.json` says, in its own `comparison` field:

> "The verbatim arms retain every answer their source states, by construction, because
> they store the turn unchanged. That is architecture, not a measured win, **and must
> not be reported as one.**"

A bolded row in a head-to-head table, opposite a measured number, is reporting it as
one. The two cells are also not commensurable: 21% is a containment measurement over
Mem0's store; "none" was never measured on ours.

**Replacement.** Move the row out of the table into the prose beneath it, where the
"A verbatim store cannot lose what it was given" sentence already sits, and bound the
Mem0 half in the same breath: *"Up to 21% of answers stated verbatim in the source are
absent from Mem0's finished store — an upper bound, because this is a containment test
in which a preserved paraphrase counts as absent. The verbatim store has no
corresponding number, because it stores the turn unchanged; that is architecture, not
a measured win."*

### S6 — Page 1, read in isolation, tells a reader four things that are not quite true.

I read lines 11–67 alone and asked what a reader who stops there believes.

1. **They believe the four-part architecture beat Mem0.** *"**How it works.** Four
   parts. ... and a **set-level coverage objective** that packs one character budget"*
   sits three paragraphs below the table showing 0.563 against 0.487.
   `SCOPE_LIMITS.md` §2: *"A2 is NF-004's `P_PAIR_RANK`... It contains **no set-level
   coverage objective and no diversity floor.**"* The arm that scored 0.563 is not the
   system described on the same page. §5.5 fixes this; page 1 does not, and page 1 is
   the quoted surface. **Add to the "How it works" paragraph:** *"The arm measured
   against Mem0 above carries the first three parts; the coverage objective was not in
   that test (§5.5)."*
2. **They believe 0.563 and 0.487 are objective accuracies.** Page 1 never says the
   primary endpoint is model-judged, by the same local 27B that answered. §13.8's
   rater caveats are about the internal rubric and do not reach here. **Change the row
   label to:** `Questions judged correct, of 300 (model judge)`.
3. **That row label is also a unit error.** *"Questions answered, of 300"* against a
   value of `0.563` invites "0.563 of 300 = 169". It is a rate. Write `0.563 (169 of
   300)` or fix the label as above.
4. **The 21% loses its bound on page 1.** *"Of the answers written verbatim in those
   conversations, **up to a fifth never reached its store**"* keeps "up to" but drops
   the reason — the containment test. The abstract carries the caveat in full; page 1
   does not. Spine §8 forbids *"Mem0 loses 21% of memories"*, and "never reached its
   store" is one careless paraphrase away from it. **Append:** *"...never reached its
   store — an upper bound, since a preserved paraphrase counts as absent under this
   test."*

### S7 — The fixed-width baseline is smaller and cheaper than ours, and neither number appears anywhere in the paper.

You surfaced 0.550 against 0.563 honestly and prominently, in the exec summary's own
"What this does not establish". That is the right instinct and I credit it. But the
accuracy near-tie is the *least* uncomfortable of A4's numbers, and the other two are
absent from the document entirely — grep for `2.8 MB`, `2,789`, `866` and `3,904` in
`PAPER_002.md` returns nothing.

From `cost/storage.json` and `result.json`:

| | A2 (this component) | A4 (fixed-width chunks) |
|---|---:|---:|
| Judged | 0.563 | 0.550 |
| Prompt tokens per read | 4,009 | **3,904** |
| Store bytes | 7,176,599 (**7.2 MB**) | **2,789,194 (2.8 MB)** |
| Bytes per turn | 2,229 | **866** |

The trivial baseline is within 1.3 points, reads **cheaper**, and stores in **2.6x
less space**. Meanwhile §5.2 builds a store-size argument — *"The finished store
occupies 42.8 MB against 7.2 MB, six times larger"* — from which the arm that beats us
on that exact axis is silently omitted. That is the one place in §5 where a reviewer
holding `storage.json` would say the paper chose its comparison.

**Required.** Add to §5.2, in the same breath as the 42.8/7.2 sentence: *"Fixed-width
chunking is smaller still, at 2.8 MB and 866 bytes per turn against this component's
2,229, and marginally cheaper to read at 3,904 prompt tokens against 4,009. On this
corpus the storage and read-cost advantages over Mem0 are not advantages over
chunk-and-embed."* Add the two cost columns to §5.1's table while you are there.

Also worth one clause: 7.2 MB is **94% embedding vectors** — `text_bytes` 434,583
against `vector_bytes` 6,742,016. It tells a reader that the verbatim store is nearly
free and the index is not, which strengthens rather than weakens the architecture
argument.

### S8 — §5.5 imports holdout language into the one block where the spine forbids it.

§5.5: *"The longest **holdout** conversation is 90,713 characters."*

Spine §8 forbids *"`CONFIRMATORY` standing, or any sealed-holdout language"* for this
block, because LoCoMo is exhausted. The word appears in the subsection whose job is to
refuse exactly that, four lines above *"**Not confirmatory.**"*

**Replace with:** *"The longest conversation in this corpus is 90,713 characters."*
Value confirmed: `mem0_store_probe.json` `conv-43.source_chars` = 90,713, shortest
`conv-30` = 45,984. The dropped-newline correction landed correctly in both places.

### S9 — §2.1 rests its strongest axis on `1 + n`, which this repository measured as 1.0.

§2.1's table, in the row the paper singles out as *"the axis on which the difference
is largest"*: *"Mem0's ingestion is one extraction call per message pair **plus one
update call per extracted fact**, so `1 + n`."*

`cost/mem0_ingest.json`: `generative_calls_per_pair: 1.0`, exactly 1,646 calls for
1,646 pairs across all six conversations. Spine C2 flags the discrepancy — *"Mem0's
paper describes `1 + n`; this build spent one"* — and the paper never reconciles it.
As it stands, §2.1 leans on a published description that §5.2's own measurement
contradicts, in the direction that flatters the argument.

**Add after §2.1's table:** *"One correction to the first row from §5: Mem0's
published description implies `1 + n` calls per pair, but the 2.0.18 build measured
here spent exactly 1.0 (`cost/mem0_ingest.json`, 1,646 calls for 1,646 pairs). The
architectural difference is against 1, not against `1 + n`."*

### S10 — A2 has the lowest judged unanimity of any memory arm, and the paper reports no unanimity at all.

`result.json` `judged_unanimity_rate`: A0 1.000, A4 0.887, A3 **0.870**, A1 0.867,
A2 **0.853**. The winning arm's verdicts are the least stable across the three
replicates, and Mem0's are more stable than ours. The spine carries this column (§2).
The paper mentions unanimity nowhere — grep returns only §13.1's unrelated internal
figure.

Not fatal: the contrast is **paired per item**, so replicate instability lands inside
the sign test rather than hidden from it. But omitting the column entirely, when it is
the one column where our arm ranks last among memory arms, reads as selection.

**Required.** Add a unanimity column to §5.1's table plus one sentence: *"Judged
unanimity across the three replicates is 0.853 for this component and 0.870 for Mem0
— the winning arm's verdicts are the less stable of the two. The contrast is paired
per item, so that instability sits inside the sign test rather than beside it."*

### S11 — Two small imprecisions.

- §14: *"reached its store **41 times faster**"*. 41x (spine R6) is
  `block_seconds_p50` — assembling a context block, 0.010 s against 0.413 s. "Reached
  its store" is a different operation. **Replace with:** *"assembled a context block
  41 times faster"*.
- §13.1 is stale in two ways now that §5 exists: *"Every scored comparison in this
  paper is a single run at a fixed seed"* (HH-001 is three replicates at seed
  5005 + replicate, per `commitments.json` and spine P5), and *"three of this arc's
  **four** scored verdicts fall inside the band"* (the arc now has five). **Replace
  the first clause with:** *"Every scored comparison in this paper except §5's
  head-to-head is a single run at a fixed seed; §5 ran three replicates per item per
  arm."* And say explicitly that the 3.0-point band was measured on the internal
  13-point rubric over 17 items and **does not transfer** to a 300-item LoCoMo
  instrument — otherwise a reader will apply it to 7.7 and reach a wrong conclusion in
  one direction or the other.

---

## Where the draft under-claims

You asked for this direction too, and there is one clear instance.

**§5.1 does not say why the paired design makes the 3.0-point band irrelevant, and it
should.** The paper spends §13.1 establishing that scored comparisons in this arc are
untrustworthy below 3.0 points, then reports a scored 7.7-point gap without saying why
it is not subject to the same doubt. The answer is in `result.json` and it is good:
the contrast is **paired within item**, 46 gains against 23 losses over 231 ties, so
run-to-run variation that moves both arms together lands in the ties and never reaches
the statistic; and the model-free containment endpoint, which no judge can be talked
into, agrees in sign at p = 2.85e-05. That is a stronger evidentiary position than any
other scored result in this paper, and §5.1 currently leaves the reader to construct
the argument unaided. **Add one sentence.** Do not soften anything.

Against that, I found **no** over-hedging that needed removing. §5.5 is dense with
caveats, but every one is a caveat the artifacts require, and they are sectioned
rather than scattered through the prose, which is the correct shape.

---

## Checked and found clean

Listed so you can tell checked-and-clean from not-checked.

**Recomputed from `result.json`, exact:**

- Judged: A1 0.6133, A2 0.5633, A4 0.550, A3 0.4867, A0 0.000 — §5.1's table and
  Figure 1's caption match to three decimals.
- Containment: 0.320 / 0.313 / 0.287 / 0.217 / 0.000 — match.
- `accuracy_delta` judged 0.076667 → "7.7 points"; gains 46, losses 23, ties 231,
  ratio 2.00, `p_one_sided` 0.0038103 → "p = 0.0038". All match.
- Containment contrast: delta 0.096667 → "+9.7", gains 40, losses 11,
  p 2.8519e-05 → "2.85e-05". Match.
- `sign_check.agree = true`, `directional_claim_permitted = true`. §5.1's *"both
  endpoints point the same way, which is the condition this study registered in
  advance"* is exactly right, and the guard is real rather than decorative.
- A0 = 0.000 with `gold_survived_into_block = 0`. The contamination-floor claim holds.
- Fidelity: A2 101/108 (0.9352), A3 79/108 (0.7315), A4 94/108, A1 108/108. §5.3's
  "0.935 against 0.732" matches. §5.3 uses the 108 denominator and does not mix it
  with L1's 315 — the spine's L6 warning was heeded.
- Long-horizon deltas, recomputed A2 − A3 by bucket: **+11.86, −3.07, +2.00, +14.92**
  → §5.4's "+11.9 oldest / −3.1 second / +14.9 newest". Correct, including the sign on
  the quarter where we lose, which §5.4 states rather than omits.
- `prompt_tokens_relative_to_cheapest_arm` A1 = 222.58 → "222 times". Correct, and
  correctly anchored to A0 rather than to a memory arm.
- Read costs: A3 3,392.5, A2 4,008.8. §5.2's "3,392 against 4,009" is right, and
  **R9 is honoured everywhere I looked** — every ingest-cost figure in the exec
  summary, the abstract and §5.2 has the read-cost reversal adjacent to it. Spine §8's
  hardest procedural rule is satisfied, including in the abstract, which is where it
  is easiest to drop.
- `block_seconds_p50` A2 0.010, A3 0.413 → 10 ms / 413 ms / 41x. Correct.

**Recomputed from `cost/*.json`:**

- `mem0_ingest.json`: 1,646 generative calls over 1,646 pairs, 17,024.7 s = 283.7 min
  → "284 min". Correct.
- `mem0_store_probe.json`: 66 absent of 315 = 20.95% → 21%. Retention range 0.6818
  (conv-30) to 0.8627 (conv-49) → "0.68 to 0.86". Correct.
- `storage.json`: A3 43,463,806 − 692,224 = 42,771,582 → 42.8 MB; A2 7,176,599 →
  7.2 MB; ratio 5.960 → "six times larger". **The ÷1000 conversion bug is fixed** —
  both figures now divide by 1e6, and the history log is excluded in the direction
  that favours Mem0.
- Conversation extremes 90,713 / 45,984 — the dropped-newline correction landed.

**Prohibition sweep against spine §8 and `SCOPE_LIMITS.md`:**

- **66.88% as a denominator:** clean. It appears twice, both times inside an explicit
  refusal, and is never divided into or subtracted from anything.
- **"Mem0 loses 21% of memories":** the forbidden phrasing appears nowhere. §5.3 and
  the abstract both carry the upper-bound framing in full, and §5.3 goes further —
  *"that is the honest reading and it is the one to quote"*. Only page 1 is thin
  (S6.4).
- **Zep / A-MEM / HippoRAG / LangMem / Mem0-graph:** no measured claim about any of
  them anywhere in the document. §5.5's disclaimer is explicit and correct. The only
  defects are the two stale *negations* at S2, which err toward under-claiming rather
  than over.
- **Breadth / multi-domain:** clean, and better than clean — §5.5's "Not a breadth
  result" names `P_PAIR_RANK`, names the missing coverage objective, and cites
  `SCOPE_LIMITS.md`. The only leak is the page-1 architecture description at S6.1.
- **A2 ≈ A4 read as evidence about NF-004:** clean. The withdrawn "not earning its
  keep against a trivial baseline" inference from `SCOPE_LIMITS.md` §1 does not
  reappear in any form. The exec summary's framing — *"against chunk-and-embed on this
  corpus it does not"* — is the narrower replacement §1 prescribes, near verbatim.
- **CONFIRMATORY or sealed-holdout language in §5:** one leak only, S8's "holdout
  conversation". Otherwise refused correctly and repeatedly.
- **"Zero inference calls":** not present. The paper consistently writes "no
  generative calls" and flags the resident embedder. `DO_NOT_WRITE.md` item 1 holds.
- **NF-004's scope cap:** *"bounded to evidence availability and authorizes no reader
  claim"* survives intact in the abstract and in Figure 3's caption, and
  p = 6.19e-12 is stated plainly rather than hedged into vagueness.
- **Study 009 +3.0, LV-001 −2.0, Study 011 −1.0:** all three carry the NOT
  DEMONSTRATED label in §4.1's table and §13.1, and *"Not demonstrated is not refuted"*
  is stated explicitly. No rescue reading of the instrument band; K-first packing is
  not revived anywhere.
- **Availability is not correctness:** §14 states *"Availability and correctness were
  measured moving in opposite directions once, and that result stands unrescued."*
  Correct, and correctly placed at the centre rather than in a footnote.

**Style sweep:** no `delve`, no `leverage` as a verb, no `robust`, no `seamless`. No
self-description as novel — §1.3 explicitly disclaims novelty for MMR, facility
location and submodular selection. Bare adjectives are rare and mostly attached to
numbers.

**`README.md`:** contains no reference to Mem0, HH-001 or any head-to-head, so it
carries no stale "no competitor was run" sentence. It is out of date rather than
wrong. Not a blocker, but worth updating in the same commit.

**Not checked:** §§6–12 beyond a skim; Figures 4–7 captions; `ERRATA.md` (appendix D
says 20 entries; I did not verify the count or the contents); `DO_NOT_WRITE.md`'s 35
items individually — I checked the HH-001-relevant prohibitions through spine §8's
mirror of them, not against the source list; whether
`scripts/check_paper_002_claims.py` actually passes at this revision;
`cost/mem0_ingest_latency.json` — I took I1 through I3 from the spine rather than
recomputing them, so Figure 2's 11.9 s / 34.8 s / 1.13x / 1,137 bursts are
**not** independently verified.
