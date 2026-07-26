# Amendment 001 — Delivered LTM Information Was Mis-Measured; `B_ltm` Re-Derived

**Study:** 007
**Registered:** before any implementation file was written (S7-T-004, the Correction 4 stage-interface check)
**Amends:** pre-registration *Summary*, §1 *Budget expressed in information*, §3 *Containment dedup*, *Observational Measures*, and the Study 006 LTM analysis it cites
**Status:** BINDING

---

## 1. What triggered this

The pre-registration adds Correction 4 as a standing rule:

> If any study changes the granularity, units, or size distribution of what a stage emits, every downstream stage's budget, cap, or threshold that consumes that output must be explicitly re-derived, and the re-derivation recorded in the pre-registration — even if the downstream stage is otherwise out of scope.

S7-T-004 performs that check for Study 007. Performing it surfaced a **second, previously undiscovered instance of exactly the failure Correction 4 was written to prevent** — this time at the retrieval/render interface, inside Study 006's own results.

The rule caught a live bug on its first application. That is the strongest argument for keeping it that this program is likely to get.

## 2. The defect

`get_distilled_retrieval_rows()` (`src/memory/distilled_ltm_store.py:453`) selects:

```sql
SELECT distilled.id, distilled.source_episode_id, ..., distilled.embedding,
       episodes.turn_number, episodes.user_message, episodes.assistant_message, ...
FROM distilled_ltm AS distilled
LEFT JOIN episodes ON episodes.id = distilled.source_episode_id
```

The row's `id` is the **source episode id**, and `user_message` / `assistant_message` are the **source episode's full text**. `distilled.text` — the selected span — is never read. It survives only as an embedding (for ranking) and as a `distilled_id` provenance attribute on the rendered element.

So the read path ranks by span and renders by episode.

This was invisible through Study 005, where a distilled record *was* a whole turn and record text was identical to episode text. Study 006 changed the record to a sentence span, and the two diverged silently. Nothing errored; the numbers simply began meaning something else.

## 3. Measured consequences (Study 006 artifacts, `runs/study_006_full_001` and `controls/whole_turn_seeded/run_001`)

### 3.1 The pre-registration's central figure is wrong by ~22×

| Quantity | Pre-registration | Measured | Source of the error |
|---|---:|---:|---|
| Treatment LTM chars delivered, Q11 | ≈ 584 | **13,130** | 4 records × 146 chars/record, where 146 = 29,214 store chars ÷ 200 records |
| Control LTM chars delivered, Q11 | ≈ 20,700 | **21,805** | 5 × 4,149 — accidentally close, because control records *are* whole episodes |
| Ratio control : treatment | ≈ 35× | **1.66×** | |

The treatment figure was computed from mean **stored record** size. Delivered size is mean **rendered episode** size, which is 3,940 chars — 27× larger.

Q14 (turn 121): treatment 16,027 chars, control 21,875 chars. Ratio 1.37×.

**The delivered-information collapse that Study 007 was designed to reverse did not happen.** Delivered LTM information fell by a third, not by an order of magnitude.

### 3.2 What actually differed at the probes

| Arm | Turn | LTM episodes | Distinct topics | Planted terms in the rendered block |
|---|---:|---:|---:|---|
| Treatment | 120 | 4 | **2** | Halcyon, 847, S460ML, Bekova, 92.4 |
| Control | 120 | 5 | **4** | Halcyon, 847, S460ML, Bekova, 92.4, della Rovere, Federal Reserve, Taylor, marine snow |
| Treatment | 121 | 4 | 3 | + Vampyroteuthis, Watanabe, marine snow, photophore |
| Control | 121 | 5 | 3 | + 1483, Vampyroteuthis, Watanabe, marine snow |

The discriminating variable at Q11 is **topic coverage in the block: 2 versus 4.** It is not delivered volume.

### 3.3 A correction to the Study 006 analysis report

`runs/study_006_full_001/condition_c/ltm_analysis/analysis_report.md` states that at Q11 the treatment surfaced only `Halcyon` from one domain. That table was computed against **distilled record text**, not against the constructed prompt. Measured against the prompt the model actually received, the treatment's Q11 block contained **all five** civil plants and a marine-biology episode.

This does not change any Study 006 verdict — Q11 still scored 0.0, both breadth probes still failed, and the store-versus-retrieved gap the report identified is still real. It changes the *magnitude* attributed to it and rules out "too little text reached the model" as the explanation. The Study 006 report is closed and merged; this amendment is the correction of record and is cited from Study 007's report.

### 3.4 A second collapse the pre-registration did not model

200 distilled records resolve to **69 distinct source episodes**. Because arbitration and the tagged renderer key on `id` (= `source_episode_id`), multiple selected spans sharing a source episode collapse into one rendered element.

Per topic (all four topics hold exactly 50 spans, by the C = 50 cap):

| Topic | Spans | Distinct source episodes |
|---|---:|---:|
| civil_engineering | 50 | 20 |
| renaissance_art | 50 | 15 |
| monetary_policy | 50 | 16 |
| marine_biology | 50 | 18 |

So a count-based top-M = 5 over spans can deliver fewer than 5 elements, and a character budget charged at span size would systematically under-count what is actually spent.

## 4. What changes

### 4.1 The budget is charged at rendered cost

The pre-registration says characters are the unit because "records are stored as text and character counts are what the existing logs carry." That sentence assumed record text equals delivered text. It does not.

**Amended rule.** `B_ltm` is charged against the **characters the record contributes to the rendered `<retrieved_ltm>` block** — that is, its resolved source episode's `user_message` + `assistant_message`, after identifier dedup. A record whose source episode is already admitted costs **zero** additional budget and does not consume a slot.

This is the only reading of "budget expressed in information" that measures the information the model receives. Charging at span size would leave the budget as decorative as the count it replaces — the same class of error, one interface further down.

### 4.2 `B_ltm` is re-derived

The pre-registration's proposed 4,000 characters was derived from the false 584-char baseline, and was intended to raise delivered information ≈ 7×. Against measured reality, 4,000 chars would **cut** the treatment's Q11 delivery from 13,130 to under 4,000 — a 3.3× reduction — and could not hold one episode from each of four topics at a mean 3,940 chars each.

The proposed value is therefore **withdrawn, not adjusted**: it cannot satisfy the replay gate's four-domain criterion at any `k_min ≥ 1`, so keeping it as the anchor would guarantee a gate failure for a reason unrelated to the policy.

`B_ltm` is re-derived from measured rendered sizes and calibrated by the Retrieval Replay Gate under the pre-registration's existing smallest-sufficient rule, which is unchanged. Sweep anchors, recorded now so the sweep is not fitted after the fact:

- Floor of the sweep: **16,000** chars ≈ 4 topics × 3,940 mean episode chars — the smallest budget that can hold one episode per topic on average.
- Ceiling of the sweep: **40,000** chars ≈ 10,000 tokens, which keeps projected peak context inside the gate's 60%-of-`--ctx-size` limit with the observed STM and recent blocks.
- Study 006's treatment delivered 13,130 chars at Q11 and covered 2 topics, so any passing value will exceed it. **Study 007 will deliver more LTM text than Study 006, not less.** This is a change of direction from the pre-registration's stated intent and is called out so it is not mistaken for drift.

`k_min` keeps its proposed value of 3 as the sweep anchor, unchanged.

### 4.3 Containment dedup is strengthened, and its rationale corrected

The pre-registration justifies containment dedup as: a span is a substring of its source episode, so if the episode is in STM the span is redundant.

Measured, the case is stronger and simpler: the LTM element **is** the source episode, verbatim. A containment hit is exact duplication of several thousand characters, not the partial redundancy the pre-registration describes. The rule and its direction are unchanged — drop the LTM entry, keep STM — and its expected saving is now large enough to be worth logging separately, which §5 of the pre-registration already requires.

### 4.4 Observational measures

`delivered_ltm_chars` is measured on the rendered block. The Study 006 comparison baselines become **13,130 (treatment Q11) / 21,805 (control Q11)**, replacing ≈ 584 / ≈ 20,700. Two measures are added: `distinct_topics_in_block` (the variable that actually separated the arms) and `records_collapsed_to_episode`.

## 5. What does not change

- Both new mechanisms ship as pre-registered: information-expressed budget, per-domain floor + similarity fill.
- Floor, fill, round-robin, floor protection, containment-dedup direction — unchanged.
- Smallest-sufficient calibration rule, both offline gates, and the requirement that they pass at the same parameters — unchanged.
- All three bars, their criteria, and the ceiling note on Q5/Q8 — unchanged.
- Formation — untouched, as pre-registered.
- **The renderer is not fixed.** See §6.

## 6. Rejected: making the read path render span text

The obvious repair is to render `distilled.text` instead of the source episode. It is rejected for this study, and the reasoning is recorded because a reviewer will ask.

1. **It is a second concurrent change to the mechanism under test.** The pre-registration refuses concurrent changes on exactly this ground ("Changing C or salience concurrently would confound the retrieval fix"). Rendering spans would alter delivered content, delivered volume, and the meaning of a "record" simultaneously with the budget and floor. No observed difference could be attributed.
2. **It would silently rewrite the control.** The Bar 2 baseline runs checked-out Study 006 code. A renderer change lands only in the treatment, so the arms would differ in two places instead of one.
3. **Study 006's verdict depends on it.** Study 006 was scored, reported, and merged with this renderer. Changing it mid-comparison would make the Study 007 treatment incomparable to the Study 006 result it exists to improve on.
4. **It is not obviously the right fix.** Rendering spans delivers less context per record but more distinct records per budget. Whether that helps or hurts recall is an empirical question of the same size as this study, and it interacts with the floor. It deserves its own study, not a line in this one.

**Recorded as the leading candidate for Study 008**, alongside the minimum-viable-C question, and stated as a limitation in the Study 007 report: this study optimizes retrieval over an element whose rendered form is a whole episode, so its conclusions about budget sizing do not transfer unchanged to a span-rendering read path.

## 7. Risk this amendment accepts

Correcting the premise weakens the study's prior. The pre-registration expected a large effect from restoring delivered volume; measurement says volume was never the deficit, so the **entire expected effect now rests on the diversity floor.** If breadth does not recover, the diagnosis is cleaner than it would have been — the budget cannot be blamed — but the study has one mechanism carrying it rather than two.

The pre-registered failure-condition table already covers the outcome. "Bar 1 fails with four-domain coverage in the log" remains the interesting result and its meaning is unchanged: the bottleneck is neither formation nor retrieval, and the next study targets context presentation.

## 8. Authorization

Registered under the author's standing instruction that amendments are made, registered, and the study continues, rather than halting at a pre-registered stop condition. The trigger here was not a failed gate but a false premise found before implementation began — the cheapest point at which it could have been caught, and the point Correction 4 exists to create.

**Verification commands** (all figures in §3 reproduce from committed artifacts):

```bash
PYTHONUTF8=1 .venv/Scripts/python.exe scripts/verify_study_007_amendment_001.py
```

Invoked through the interpreter directly rather than `uv run`, which cannot
build this project (`pyproject.toml` carries a direct-reference dependency
without `tool.hatch.metadata.allow-direct-references`). Unrelated to Study 007
and left unfixed inside the study window; noted as post-study work.
