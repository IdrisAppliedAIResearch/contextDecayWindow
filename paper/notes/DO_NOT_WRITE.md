# Do not write — withdrawn and corrected claims

**Purpose.** Every sentence this programme has published and then withdrawn or
corrected. A rewrite is the most likely moment for one of them to reappear, because
withdrawn claims are usually the *cleaner* sentence — that is why they were written
the first time.

**How to use it.** Grep the draft for the superseded value, not for the superseded
sentence. Pass 6's own note applies: *"It was found by grepping for the superseded
value rather than by rereading, which is the only method that works."*

**Sources.** `ERRATA.md` (20 entries), `paper/reviews/CYCLE_1.md` (sixteen
objections, all accepted), `CYCLE_2.md` (ten, all accepted),
`PASS_6_SLOP_AUDIT.md`, `paper/CLAIM_TO_ARTIFACT.md` §A.9.

---

## 1. The ten highest-risk repeats

These already appeared in a published draft. Each is a cleaner sentence than its
replacement, which is exactly the hazard.

| # | ❌ Never write | ✅ Write instead |
|---|---|---|
| 1 | "No inference calls anywhere in the memory path" | **No *generative* model calls** in the memory path. An embedding model must be resident: `context()` embeds every query, `append()` embeds every episode. Determinism holds **given a pinned embedder** |
| 2 | "Every one of the 146 configurations beat the deployed 6 of 17" | True only on the 119-episode pool. Per-pool minima are **7 / 5 / 4**; on the deployed 34-episode pool the shipped configuration scores **5/17 against the baseline's 6/17** |
| 3 | NF-003's "49 gains, zero losses" | A **session-touch surrogate**. The strict answer-episode measure **reverses** it: 388 → 351, **26 gains and 63 losses** |
| 4 | "IDF ranked the six hard plants worse than density" | **Withdrawn.** Mean IDF was worse on 5/5 eligible; max IDF improved 2; sum-per-word improved 1. **No variant was registered primary**, so the family was not refuted |
| 5 | MMR is "non-submodular" | MMR is **non-monotone submodular** (Lin & Bilmes 2011, ACL-HLT 510–520, §3 Thm 2). The greedy guarantee fails for want of monotonicity. **Repository-wide prohibition** |
| 6 | Any live-study tier called a "recency window" | A **least-recently-delivered rotation**, and before that a **locked prefix holding source turns 1–9**. Overlap with a true window **0.205**. **No arm in the programme ever ran a real window** |
| 7 | 12/17 as a shipped system's performance | **Offline availability** on one enumeration probe. **LV-001 killed the promotion** on its own registered bar (B2 FAIL, −2.0 against a 0.5 tolerance) |
| 8 | "Eleven studies" | **Ten numbered studies plus one registered exploratory bakeoff** |
| 9 | Latency "20–3,000 candidates"; "~40 ms at 1,000" | Measured range is **20–119**. **190 ms at 1,000**, exponent **1.25**, clustering **81%** and rising. The withdrawn projection ran **84× past its last data point** |
| 10 | 20.0% or 12.22% against any published LongMemEval score | **Codex-substituted integrity scores.** Amendment 010 forbids the comparison; the pinned GPT-4o evaluator was unavailable |

---

## 2. The full withdrawn list

Numbered as in the audit. Each is a landmine.

11. ❌ "outperformed every mechanism this program layered on top of it" → most of
    those mechanisms **were never run live**. Use gate language.
12. ❌ "smaller than the deployed systems named in §2" → an observation about the
    **listed mechanisms** only. No system was run here.
13. ❌ "the failure is specific to enumeration rather than general to similarity
    retrieval" → **one probe behaving unlike eight.** One instance cannot establish
    a type. The abstract must not assert what the body declines to assert.
14. ❌ "PRIMACY MECHANISM LIVE" (AS-001) → **withdrawn.** The rule could not
    distinguish a primacy mechanism from the joint effects of rank, greedy N-first
    packing and budget. Rank 27 first enters at **108,432 characters**.
15. ❌ Study 010's 31,991 / 31,847 chars as "near-saturation" → actual serialized
    **53,726 / 53,839 — 67.9% and 68.2% over budget.** The budget was violated, not
    saturated; **the compact-store scaling conclusion is withdrawn.**
16. ❌ "per-candidate cost is flat to about 119 candidates" → not a reading of
    CC-005's curve. Cost rises 84.0 → 100.1 µs between 50 and 100.
17. ❌ Q4 cosine `0.16612689197063446` → **`0.12042197585105896`.** The old value has
    no committed generating code.
18. ❌ Oracle rank 21 at turn 118 → **rank 20.** Oracle ranks are **14, 20, 22, 86,
    112**.
19. ❌ E002 targeted "14/16" → **16/16.** The gate `preserved == required` was
    **unsatisfiable by construction** for any selector, from a `(turn, item)` vs
    `(question, turn, item)` keying mismatch.
20. ❌ SUP-001 byte-identity as a factual measure → **withdrawn.** It measured
    serialization, not correctness: `$35.00` == `$35`. Corrected to **C0 8/9, T1 9/9**.
21. ❌ Study 011's prediction 4 ("Arm A ≈ Study 009's Arm S") → **withdrawn as
    unscorable.**
22. ❌ Study 009's Arm S as "the pure STM architecture" → it was **nine fixed
    episodes and one recent one.**
23. ❌ Study 001 as VALIDATED → **PARTIAL.** The 2026-07-26 audit changed 19 of 222
    items and removed the programme's only VALIDATED verdict.
24. ❌ "about 20 remaining scoring errors" unqualified → attach the interval.
    3 of 26 gives **~3 to 43** over 143 unreviewed items (95% Clopper-Pearson). The
    figure is **extrapolated, not observed.**
25. ❌ Rater self-consistency 97.47% → **CUT, untraced.** Use only the sourced
    11.54% control disagreement.
26. ❌ "three degradation probes" → **DEMOTED, count untraced.** Describe the
    validator and the error class without asserting a count.
27. ❌ "the byte-identical rerun rule is not satisfiable on this runtime" (flat) →
    satisfiable **between runs sharing server process state**; not satisfiable
    cold-start vs warm-start. **No study in the arc pinned process state.**
28. ❌ Study 009's 3.0, LV-001's −2.0, or Study 011's −1.0 asserted as demonstrated
    → **all inside the measured 3.0 band.**
29. ❌ Study 010's LTM saturation as evidence about consolidation → **844 of 1,000
    episodes are exact content duplicates**; only 156 distinct pairs exist. It has a
    mechanical reason to saturate independent of any consolidation behaviour.
30. ❌ 13/17 presented as overturning 8/17 → **different objects, different
    denominators.**
31. ❌ "the target was always reachable" without its qualifier → **four of the five
    optimum episodes are prior probe answers**, and this probe's earlier answers were
    largely wrong. An item counts as available if its text appears, however wrong the
    surrounding response.
32. ❌ The cross-corpus binding-ratio law → **refuted.** Seven overlapping cells have
    opposite signs.
33. ❌ Session-touch as a delivery measure, anywhere → it **hides every strict loss**
    (10 baseline / 15 treatment false hits on LoCoMo development).
34. ❌ DMR-001's G4/G5 numbers cited as results → computed **post-stop**, descriptive
    only.
35. **AMENDED 2026-08-21 — HH-002 placed this component on the published table.**
    Two amendments now sit on this entry; read both.

    **2026-08-20, HH-001.** A comparison to **Mem0 as run in HH-001** is measured
    and may be stated plainly; see `COMPETITIVE_LANDSCAPE.md` §4.1 and
    `HH001_EVIDENCE_SPINE.md`.

    **2026-08-21, HH-002.** The paper may state that this component **scored
    79.09% on the 1,540 LoCoMo questions, harness, answer prompt, judge and
    metric that produced arXiv:2504.19413 Table 2**, and may print that table's
    rows beside it with attribution. Placement on a shared axis is not a
    measurement of another system, and the axis is licensed by G-CTRL: the same
    rig reproduced full context at 72.47% against a published 72.90%. See
    `HH002_EVIDENCE_SPINE.md`.

    **Still forbidden, and this is the whole point of the scope:**
    - ❌ That this component **beat**, **outperformed** or **trailed** Mem0, Zep,
      A-MEM, Mem0ᵍ or OpenAI memory. None of them was run here.
    - ❌ Any **paired test, sign test, p-value or gain/loss count** against an
      inherited row. Their per-item answers were never published.
    - ❌ **40.58**, or any other floor-adjusted figure derived from a quoted row.
      The 26.30% floor was measured on this rig and is **not uniform** by
      stratum (32.34% open-domain, 11.21% temporal); subtracting a scalar from a
      row whose strata were never published is arithmetic, not measurement.
      Floor-adjusted values for rows **measured here** are permitted.
    - ❌ Any comparison to Mem0's current **92.5%** — different harness, gpt-4o
      answerer, `top_k=200`.
    - ❌ Describing Mem0's 66.88% as something this programme measured.

    ❌ Original: Any comparison to HippoRAG, Mem0, Zep or Letta presented as measured →
    **none were run here.**

---

## 3. Claims deliberately not made

From `CLAIM_TO_ARTIFACT.md` §A.9. These were considered and refused.

| Forbidden | Why |
|---|---|
| "Similarity retrieval fails" | Measured the **opposite** on 8 of 9 probes |
| "Our approach doubles performance" | True of 6/17 → 12/17 and **misleading** without 14/17 and 15/17 beside it |
| Novelty for MMR, facility location, or submodular selection | Established methods. What is offered is the decomposition and the measurement, not the selector |
| That the pool cut costs seven facts in general | One frozen configuration |
| That the 15/17 optimum is achievable by a retriever | **It is computed with the answer key** |
| That `episodic` is bounded in general | One store, one conversation shape, one horizon |

---

## 4. Style constraints

From `PASS_6_SLOP_AUDIT.md`. All currently at zero hits and must stay there.

**Banned outright:** delve; leverage (as a verb); robust; seamless; cutting-edge;
paradigm shift; "it is important to note"; "in the realm of"; "a testament to";
"this raises interesting questions"; hedging stacks ("may potentially", "might
possibly", "could potentially"); filler openers ("In recent years", "increasingly
important").

**Rules that carry:**

- **The paper never calls its own contribution novel.** The three surviving uses of
  "novel" are Study 003's filter, which is literally named that, and §1.3 using the
  word to *refuse* the claim.
- **No rhythmic tricolons.** The tell is a three-part list whose following paragraph
  explains only two of the three.
- **Every adjective attached to a number, or cut.** Permitted unquantified kinds:
  structural ("append-only", "set-level", "verbatim", "offline"); explicitly marked
  interpretation; negations of a measured quantity.
- **Negative results stated flatly, without cushioning.** The model: *"All 17 facts
  were present in the raw store. Retrieval did not find them."*
- **Where uncertain, name the settling measurement.** Every limitation does.
- **Read-aloud test:** if a paragraph could preface any paper in any field, delete it
  and write what happened.

---

## 5. Stale cross-references to fix, not inherit

Found in the current `PAPER_001.md` during the rewrite audit. All are the same
species the slop audit caught — a value updated in one place and not another.

| Location | Defect |
|---|---|
| `PAPER_001.md:1250` | "All **six** items were caught by gates" — §7 now names seven corrections and `ERRATA.md` holds **19** |
| `PAPER_001.md:851`, `:1178` | Point at **§7.4**; the call-shape and sentinel content is **§7.2** |
| `REPRODUCTION.md:111` | Same stale **§7.4** pointer |
| `PAPER_001.md:360` | "not true before DR-001 (**§7.2**)" — the budget correction is **§7.1** |
| `REPRODUCTION.md:22` | Cites **§8.10**; §8 ends at 8.9 |
| `AGENTS.md:341` | Lists a three-reader readability review under `paper/reviews/`; no such artifact is committed |

---

## 6. Machine-checkable superseded values

Read by `scripts/check_paper_002_claims.py`. One value per line, then a pipe, then
what supersedes it. These are values with **no legitimate corrective use** — a value
the paper may name while correcting it belongs in `EVIDENCE_SPINE.md` §7.11 instead,
not here.

```superseded
0.16612689197063446 | Q4 cosine; corrected to 0.12042197585105896
97.47 | Rater self-consistency; CUT as untraced
6.09e | guard against malformed routing-ceiling restatement
```

The list is deliberately short. Most withdrawn claims in §1 and §2 are *sentences*
rather than bare numbers, and a grep for their numeric parts would collide with the
corrected values that legitimately replace them — 12/17 appears in both the withdrawn
framing and its corrected one. Those are checked by reading §1 and §2, which is what
the integrity stage's reviewer does, and by the standing labels the spine assigns.
