# HH-001 Development Plan — How Do We Actually Do Against Mem0

**Status:** `DEVELOPMENT PLAN — no implementation authorized yet`
**Stage:** development. The confirmatory stage is
`HH_001_PRE_REGISTRATION.md`, which is blocked on this.
**Authorized by:** user, August 19, 2026 — to write the plan
**Corpus:** LoCoMo, six holdout conversations (read; see §2)
**Seed:** 5005
**Date:** August 19, 2026

---

## 1. The question

Under one reader, at the same context budget, does this component deliver
context a model answers as well from as Mem0's does?

That is the whole question. Not whether we beat a published score, not whether
the result generalizes, not whether anything should be promoted. Just: on a real
external corpus, with everything else held constant, how do we do.

## 2. What this is, and what it is not

**It is development.** Its job is to produce the first real numbers and the
pilot data the confirmatory registration needs — `n`, replicate count,
discordance rate, wall clock, and whether the tier boundaries in
`HH_001_PRE_REGISTRATION.md` §7 are reachable at all. NF-004 ran four LoCoMo
development conversations before it opened its holdout, for exactly this reason.
A confirmatory registration written without pilot data names guessed thresholds.

**It is not confirmatory, and cannot become confirmatory later.** LoCoMo is
exhausted on both splits. Nothing measured here gets that standing by being
re-described.

**It does not compare against Mem0's published number.** Every arm runs on the
local model, so the published 66.88% is not this study's denominator and does
not appear in its report. That is a deliberate trade: we lose the ability to say
*against Mem0 as published*, and we gain a comparison that holds the reader
constant instead of varying substrate, judge and system all at once. For the
question in §1, the second is worth more.

## 3. Arms

Everything is frozen before the run. Nothing is tuned inside this study.

| Arm | Memory layer | Why it is here |
|---|---|---|
| **A0** `NO_MEMORY` | none; question only | Floor. How much does the reader already know? |
| **A1** `FULL_CONTEXT` | whole conversation | Ceiling. What is available to win |
| **A2** `CDW_PAIR` | this component, frozen at NF-004 `P_PAIR_RANK` | Us |
| **A3** `MEM0` | Mem0 OSS, pinned version, local models | Them |
| **A4** `RAG_FIXED` | plain chunked embedding retrieval | Does any of this beat a naive vector store? |

**A0 and A4 are what make the answer interpretable**, and neither is optional
for that reason. Without A0 a high score might be the reader's pretraining;
LoCoMo has been public since February 2024. Without A4, A2 beating A3 could be
two elaborate systems both losing to chunk-and-embed. A4 may be dropped only if
§7's timing pilot says the run does not fit, and the report then says it was
dropped and why.

### 3.1 Population — found while building, recorded before running

Adapting the corpus turned up three facts the plan had not accounted for. All
three are settled here, before any arm runs.

**850 answerable items, not 1,098.** The six holdout conversations hold 1,104
canonical unique QA records. **254 of them are LoCoMo category 5, the
adversarial class**: they carry `adversarial_answer` instead of `answer`, and
the correct behaviour is a refusal rather than a fact. Neither the containment
endpoint nor a correctness rubric measures a refusal, and `AGENTS.md` §7 forbids
scoring an answerless item above zero — a fluent wrong answer would score as
correct. **The primary population is the 850 answerable items.** The adversarial
254 are reported as their own stratum, scored for refusal rate only, and cannot
touch the contrast.

**NF-004's 1,098 is a different number from this study's denominator.** Six
records name a dialogue id their conversation does not contain, and dropping
those from 1,104 is how NF-004 reached 1,098. The judged endpoint does not read
evidence, so those six stay in the primary population here. They are excluded
**only** from the availability secondary, mechanically, along with the nine
records that resolve no evidence at all. Copying NF-004's population across
would have quietly changed what was measured.

**A1's ceiling can exceed the reader's window.** Holdout conversations run
45,984 to 90,713 characters as delivered, so the longest sit close to a
32,768-token window once the prompt is added.

**Corrected 2026-08-20.** An earlier draft of this paragraph said 45,616 to
90,034. That figure summed the per-turn renderings and omitted the newline
joining them, so it understated the string the reader actually receives by one
character per turn. The delivered figure is the one that binds, because the
budget is `len()` of the delivered string. Caught by the paper's number-trace
gate, not by review. A1 is given an explicit character allowance and **records any
shortfall on the block**: a ceiling that silently truncates is not a ceiling,
and an unmarked one would understate every other arm's gap to it.

## 4. What is held constant

Only the memory layer varies. Everything downstream of it is one fixed thing.

- **Reader:** `Qwen3.8-27B-UD-Q4_K_XL`, SHA-256
  `bee238bbeb3dc0a34bde4d0dedbaee1f98c009e8bb4226f03070054c12fb1372`,
  17,923,394,624 bytes, served by `llama-server` on `127.0.0.1:8000` at
  `--ctx-size 200000 --parallel 1`.

  **Re-pinned 2026-08-19, before any arm ran.** An earlier draft of this plan
  named `Qwen3.6-27B-UD-Q6_K_XL` (SHA-256 `f3b4a622…`), carried from LV-001's
  runtime record. That model is not what this machine serves: it is a different
  model at a different quantization, and `.env`'s `CDW_INFERENCE_MODEL_PATH`
  still points at it but is inert because `CDW_INFERENCE_SERVER_URL` is set and
  wins. Every HH-001 number therefore belongs to the model named above and to no
  other. This is a reader change, so it is not comparable to any earlier live
  result in this programme — LV-001 and Study 011 ran a different model.
- **Prompt:** one template, byte-identical across arms, only the memory block
  differs. Template and one rendered example per arm are committed before the
  first generation call.
- **Embedder:** the pinned `Qwen3-Embedding-0.6B-Q8_0`, SHA-256 `06507c7b…`, for
  every arm that embeds — including Mem0, which supports a configurable
  embedder. Otherwise the contrast is architecture plus embedder quality and we
  cannot separate them.
- **Budget:** 16,000 delivered characters, NF-004's operating point, measured by
  `len()` on the exact string handed to the reader. Each system fills it in its
  own selection order and truncates at the cap. A1 is exempt and labelled the
  unbudgeted ceiling.
- **Judge:** one model, one rubric, blind to arm identity, answers presented in
  a seeded shuffle.

## 5. What is measured

**Primary: judged correct**, per item, majority across replicates.

**Cross-check: deterministic containment** of the gold answer — casefold, NFKC,
whitespace and punctuation collapse, with a registered number and date
normalizer. No model. It is the weaker measure and it misses correct paraphrase,
but it cannot be flattered by a judge.

**If the two disagree in sign on the A2-versus-A3 contrast, we report that and
make no directional claim.** This is the cheap version of the guard the
programme actually needs. NF-003 is why: its loose measure read 49 gains and 0
losses, its strict measure read 26 gains and 63 losses — not a smaller effect,
the opposite sign.

**Secondary: availability at 16,000 characters**, joined to NF-004's committed
per-item outcomes by canonical QA hash. This is the interesting one. LV-001
found availability and answers pointing in opposite directions on our own
corpus; this says whether that reappears here. It sets nothing.

**Cost, measured not cited:** generative calls at ingest and at query, tokens,
wall clock, per arm, via a counting shim. Our zero is architectural and is not a
finding. What is worth checking is Mem0's observed count against the `1 + n` per
message pair its paper describes.

## 6. What is committed before anything runs

This is the whole of the pre-commitment, and it is deliberately short. Its only
job is to stop us from getting a number and then deciding what it meant.

1. The five arms in §3 and their frozen configurations.
2. The primary endpoint in §5, and that the judge and containment measures are
   both computed on every answer, both reported.
3. The 16,000-character matched budget.
4. `n`, the item count, and `R`, the replicates — set from §7's timing pilot,
   written down, and not revised after any outcome is seen.
5. The comparison: A2 against A3, paired by canonical QA hash, reporting gains,
   losses, ties, net, and exact McNemar p.
6. **No arm is re-run after its score is seen.** A failed run is re-run only for
   a named mechanical fault, and the fault is recorded.

That is the list. Six items. Everything else in this document is design notes
and may change while building, provided it changes before the run.

## 7. Two cheap checks that come first

Both are hours, not days, and both can change the plan.

**Contamination probe.** Run A0 on a seeded 50-item sample and look at the
score. If the reader answers most LoCoMo questions with no conversation at all,
it has seen the dataset and no memory layer is discriminable. That would be a
real finding about the corpus and would move this study to a different one —
better learned now than after the rig is built.

**Timing pilot.** One conversation, all arms, R replicates, wall clock. This
produces `n` and `R` and tells us whether A4 survives. It is the difference
between a study that finishes and one that stops at 40 percent.

Alongside them, the thing we have not done and cannot skip: **install Mem0 and
watch what it does.** Ingest one conversation and record the actual call count,
call kinds, memory count and median memory length. The `1 + n` figure is read
from their paper, not observed here. This programme has been wrong about the
behaviour behind a name four times, and never once because the name looked
suspicious.

### 7.1 Pilot results — measured 2026-08-19/20, before the run

**Contamination: 0 of 50.** With no memory at all the reader answered nothing
correctly — all 50 replies were `I don't know`, none empty. So the floor is
genuine, not an instrument failure, and it also confirms the prompt's abstention
instruction works. `G-FLOOR` passes decisively: this reader has not memorized
LoCoMo, and the arms are discriminable. It also makes retention arithmetic
simple, since `acc(A0) = 0`.

**Timing: about 0.51 s per reader call** on conv-26 at 5 items x 3 replicates
(A0 0.18, A1 0.32, A2 0.85, A4 0.69). A1 is fast because llama.cpp reuses the
prompt prefix across items from one conversation; that advantage shrinks but
does not vanish across six. **`n` = 300 and `R` = 3** are set from this and
written into the commitments before any outcome exists.

**Mem0, observed rather than cited.** Version 2.0.18 on 10 real pairs:
**1.0 generative call per pair**, 12 embedding calls, 4.65 s per pair. The
paper's figure is `1 + n` per message pair; what this build actually did on
this corpus was one. The number in the report is the measured one.

**Mem0 returns far less than the budget.** Ten ingested pairs yielded 16
memories totalling **2,107 characters against the 16,000-character budget** —
about 13%. The asymmetry §4 warned about is real and it is large: at matched
budget this component may deliver several times more text. Both configurations
are reported and neither is reported alone.

### 7.2 Three things the rig had to be told, found by running it

**The local server does not serve embeddings.** It is started without
`--embeddings` and answers `/v1/embeddings` with HTTP 501, and its start script
is immutable. `scripts/hh001_embedding_shim.py` serves the carried
`Qwen3-Embedding-0.6B-Q8_0` over an OpenAI-shaped endpoint instead, one text per
model call. Its output was checked against the sealed cache and is
**bit-identical**, so §4's one-embedder-for-every-arm rule holds rather than
being asserted.

**Mem0's search API is not what the documentation describes.** 2.0.18 takes
`filters={"user_id": ...}` and `top_k`, and rejects `user_id=` and `limit=`
outright. It also defaults to `threshold=0.1`, which drops candidates *before*
the character budget binds. The primary relaxes that to 0.0 so the budget does
the truncating, as §4 requires; the native default belongs to the secondary.

**A2 overran its budget by 120 characters.** NF-004's packer charges candidate
text only — it budgeted candidates it never rendered into one block, so its cost
model has no join in it. Rendering added two characters per join across 61
candidates. A2's ranking is still NF-004's untouched; its packing now charges
the separator, exactly as A3 and A4 already did. Charging one arm for its
separators and not another would have been a thumb on the scale, and the
overrun was caught by the runner's own budget assertion rather than by review.

## 8. Replicates, and why R is not 1

The reader is not deterministic across runs and this programme has measured that
about itself: five identical replicates of one internal arm scored 8, 8, 8, 8
and 11 — a switch, not a spread. The confirmatory minimum carried from Study 011
Amendment 001 is five.

**Development runs R = 3 unless the timing pilot says otherwise**, and the
report says so plainly. Three is enough to take a per-item majority and to
measure the per-item unanimity rate, which is this instrument's own noise
reading and one of the numbers §9 hands forward. It is **not** enough to settle
a close contrast, and a near-tie here is reported as a near-tie rather than
resolved.

## 9. What this can and cannot say

**Can say:** on six LoCoMo conversations, at a 16,000-character budget, under
one local reader and judge, arm A2 answered *k* items that A3 did not and A3
answered *j* that A2 did not, at these costs. And whether availability predicted
answers.

**Cannot say:** anything about Mem0 as published; anything about another reader,
another corpus, another configuration; anything CONFIRMATORY; anything about
deployment. The report states in its title line that this was the local-substrate
development run.

**The result is real either way.** `AGENTS.md` §9: the question is rarely whether
the deterministic version wins, it is how much of the layer survives without the
call. A number showing we recover most of it and still lose is the finding, not
a failure — provided it is reported with its margin rather than rounded in
either direction.

## 10. What it feeds

`HH_001_PRE_REGISTRATION.md` — the confirmatory stage — is blocked on this and
gets four things from it: `n` and `R` from the timing pilot, a discordance rate
for its power calculation, PF4 reachability evidence for every tier boundary it
names, and a contamination reading for its `G-FLOOR`. Its two open user
decisions (vendor tier, competitor scope) are better made with these numbers in
hand than without.

## 11. Layout

```text
experiments/comparisons/hh_001/
  HH_001_DEVELOPMENT_PLAN.md      this file
  HH_001_PRE_REGISTRATION.md      confirmatory stage; blocked on this
  artifacts/dev/
    pilot/                        contamination probe, timing, Mem0 observation
    commitments.json              §6, hashed, committed before the first run
    runtime/                      model, build and server hashes
    outcomes/                     one artifact per arm, written before judging
    judging/                      blinded surface, sealed mapping, rationales
    cost/                         call and token counts
  HH_001_DEVELOPMENT_REPORT.md    numbers, both endpoints, what feeds §10
```

## 12. Build state

The rig is built and unit-tested. Nothing has been run.

| Module | What it holds |
|---|---|
| `src/analysis/hh001_corpus.py` | corpus adaptation, gold answers, seeded stratified subsample |
| `src/analysis/hh001_arms.py` | the five arms; Mem0 imported lazily |
| `src/analysis/hh001_prompt.py` | one reader template, judge template, blinding |
| `src/analysis/hh001_endpoints.py` | containment normalizer, majority, unanimity, sign guard |
| `src/analysis/hh001_stats.py` | paired counts, exact sign test, PF4 reachability |
| `src/analysis/hh001_commitments.py` | §6, hashed, and the gate that enforces it |
| `src/analysis/hh001_cost.py` | call and token ledger, split generative from embedding |
| `src/analysis/hh001_run.py` | generate → seal → judge → gate → analyze |
| `scripts/run_hh001_dev.py` | `pilot`, `observe-mem0`, `capture`, `commit`, `run`, `report` |

**One thing is written but unexercised: the Mem0 binding.** `mem0ai` is not
installed. Installing it pulls a large dependency tree into this virtual
environment and can move pinned versions the rest of the programme's results
were produced under, so it is a deliberate separate step, and the full suite is
re-run afterwards to confirm the 1,832-test baseline still holds. Until then
`Mem0Arm` is import-safe and its result parsing is tested against the shapes
Mem0 has returned across versions; what is untested is the live call.

**Nothing runs by default.** `run` refuses to start unless `commit` has already
written the commitments file, because the whole point of §6 is that the numbers
were fixed first.

The paper's positioning sections do not change on this study's output.
`COMPETITIVE_LANDSCAPE.md` §5 and `DO_NOT_WRITE.md` item 35 stay in force: a
development number against a locally-run competitor does not license a sentence
about a published one.
