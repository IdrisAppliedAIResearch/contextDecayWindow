# LV-001 — Live Validation of the Shipping Selection Configuration

**Pre-registration:** `LV_001_pre_registration.md` at
`89614a0c3799e0e96edb7809ba11eac07d39ac90`
**Authorization:** granted 2026-08-02, conditional on `AGENTS.md` compliance
**Status:** COMPLETE
**Verdict: B1 WEAK · B2 FAIL · promotion killed**

Blind mapping, opened after scores were committed: **arm A was L-A3** (the
shipping configuration), **arm B was L-A0** (the deployed baseline).

---

## 1. Result

| Measure | L-A0 control | L-A3 treatment | Registered rule | Outcome |
|---|---:|---:|---|---|
| **B1** Q11 items correctly attributed | 6 | 7 | ≥3 CONVERTS · 1–2 WEAK · 0 no · <0 INVERTS | **WEAK** (+1) |
| **B2** targeted Q1–Q8 | 3.5 / 8 | 1.5 / 8 | L-A3 must not fall >0.5 below | **FAIL** (−2.0) |
| **B3** probes containing fabrication | 4 / 8 | 3 / 8 | descriptive | recorded |

§3 fixed the consequence before any number existed: *"A B2 failure kills the
promotion regardless of B1."* It fails by four times the tolerance.

**The offline advantage did not convert, and the thing the program said it was
protecting is what broke.**

---

## 2. What B1 actually measured

Offline, L-A3's configuration made 12 of 17 items available against the
baseline's 6 — a six-item gap. Live, the same configuration produced **7
correctly attributed items against 6**. The gap did not survive the trip from
the window to the answer.

Both arms failed the same way, and it is worth stating plainly because it is
larger than the difference between them: **neither arm delivered a single art
item.** L-A3 said outright that no art episodes were in its context. Both then
enumerated general domain vocabulary — zone boundaries, pigment families, policy
instruments — in place of the planted specifics they were asked for.

One presence/attribution split occurred, and it is the split §5's surrogate
audit was written to catch. L-A3 states "600–900 meters" as a mesopelagic zone
interface while *Vampyroteuthis infernalis* is absent from its answer entirely.
A presence-only scorer credits the item; an attribution scorer cannot, because
there is no subject to attribute it to. Scored 8 present, 7 attributed.

---

## 3. Why B2 failed, and why it matters more than B1

L-A3 lost ground on exactly the probes that ask for one specific fact:

| Probe | L-A0 | L-A3 | What changed |
|---|:--:|:--:|---|
| Q1 steel grade | 1.0 | 0.5 | L-A3 has 847 but reports the steel grade as not in context |
| Q3 formatting rules | 1.0 | 0.0 | **L-A3: "there is no record of the very beginning of our conversation. The earliest available context is from episode 82."** |
| Q8 photophore location | 1.0 | 0.5 | L-A3 gives mantle surface rather than the margin |
| Q2 load rating | 0.0 | 0.5 | the one probe L-A3 wins |

Q3 is the clearest case. The two formatting rules are planted in turns 1 and 2.
The coverage objective, spending its budget on domain spread, stopped carrying
the conversation's opening — and the model correctly reported that it could not
see it. The baseline's per-item cosine ranking kept those turns and answered
both rules verbatim.

**This is the trade the ledger named and the offline result could not see.**
`RETRIEVAL_MECHANISM_LEDGER.md`: *"Every candidate carries a no-regression arm
against targeted recall. Breaking the one thing that works to fix the one that
doesn't is a bad trade and is undetectable without measuring it."* E005 measured
targeted preservation offline at 16 of 16 and passed. Live, targeted scoring
fell from 3.5 to 1.5.

Those two results are not in contradiction. Offline preservation asked whether a
targeted item's text was *available* in the block. It was. B2 asked whether the
model *answered correctly*. It did not. **The gap between those two questions is
the entire finding of this run**, and it is the same gap PAPER-001 §5.1.1 flagged
as unmeasured. It is now measured, once.

---

## 4. B3 — fabrication

Both arms fabricated confidently on the domain neither retrieved.

- **L-A0** attributes *The Annunciation of Forlì* to **Piero della Francesca**,
  commissioned by Guidobaldo da Montefeltro, dated 1470.
- **L-A3** attributes it to **Leonardo da Vinci**, commissioned in 1472 by
  Benedictine monks, and on Q6 asserts that Cardinal della Rovere's patronage is
  "a historical myth… debunked by art historians", naming one.

The planted answer is Melozzo da Forlì, Cardinal Giuliano della Rovere, 1483.

L-A0's Q5 is the sharpest instance. Asked for the pigment technique, it produces
a fabricated analysis of a painting by the wrong artist that nonetheless
contains **both correct planted pigment terms**, lead white and ultramarine. A
presence-only scorer credits it. This is precisely the failure mode §5 required
the scoring to defend against, and it occurred.

Both arms refused honestly on Q7, where the material was genuinely absent.
Fabrication tracked the *unretrieved* domain, not the arm.

---

## 5. What this does and does not establish

**Establishes, on one corpus at one seed:** the six-item offline availability
advantage produced a one-item live difference, and the configuration carrying it
scored 2.0 lower on targeted probes than the baseline it was meant to replace.
Availability is not answer quality, and on this run the two moved in opposite
directions.

**Does not establish:** anything about breadth in general, anything at a second
seed, or that a coverage objective must cost targeted accuracy. One run. No
error bars. §3's own WEAK band exists because a one-item difference is inside
the noise of a single unreplicated comparison — and the same caution applies to
the −2.0, which is larger but equally unreplicated.

**Divergence caveat.** The arms generate their own assistant messages, so their
stores diverge from turn 1. The 17 target facts are planted in scripted *user*
turns and are identical in both stores; the assistant halves are not. Part of
the B2 difference may be path divergence rather than selection.

---

## 6. Consequences for PAPER-001

§8 of the pre-registration fixed both reporting outcomes in advance. The
DOES-NOT-CONVERT branch applies in substance: the paper's availability hedging
**stays**, and is promoted from caution to finding.

Required changes:

1. **§5.1's availability note becomes a finding, not a caution.** It now has a
   measured instance: the offline gap did not convert, and targeted accuracy
   moved the other way.
2. **§6's opening survives with its meaning changed.** It said no live run
   existed. One does now, and it did not promote the configuration.
3. **§8.6 gains its answer.** It named LV-001 as the remedy for the paper's
   largest structural weakness. The remedy ran, and the weakness is real.
4. **The decomposition in §5 is untouched.** LV-001 measured whether delivery
   predicts answers. It did not measure the pool, the objective, or the
   similarity floor, and the structural claim in §5.6 — art absent from the
   deployed 34-pool — is unaffected by anything here.

The shipping configuration's registered status returns from PROMOTION_ELIGIBLE
to **not promoted**, on its own pre-registered kill criterion.

---

## 7. Integrity

| Item | Value |
|---|---|
| Gates | G1–G6 all PASS before inference |
| Server build | `b9294-0f3cb3fc8`, one slot, `n_ctx` 50176, speculative none, seed 5005 |
| `llama-server.exe` | `3827a6b6…` — matches the Study 010 record |
| Generation model | `f3b4a622…` — matches |
| Embedding model | `06507c7b…` — matches E005's `embedding_model_sha256` |
| Turns | 121 per arm; L-A0 50.5 min, L-A3 44.1 min |
| Budget breaches | 0 of 121 in both arms |
| Blinding | seeded shuffle, mapping sealed; scores committed at `HEAD~1` before the mapping was read |

**Rater shortfall, stated.** The registered protocol calls for three blind
passes with adjudication triggers. This run scored one pass, by one rater. That
is a real shortfall and it is recorded here rather than in a footnote; a second
and third pass would be the first thing to add before any of these numbers is
quoted as settled.
