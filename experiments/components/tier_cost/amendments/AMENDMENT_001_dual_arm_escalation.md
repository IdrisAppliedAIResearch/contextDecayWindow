# Amendment 001 - Dual-Arm Escalation

**Study:** TC-001
**Status:** `BINDING - ESCALATION AND REPORTING CORRECTION`
**Amends:** nothing in `../TC_001_PRE_REGISTRATION.md`. That document stays
locked, its bars stay as written, and its verdict stays as reported.
**Date:** August 22, 2026
**Authorization:** author instruction, quoted in full below.

---

## 1. Trigger

The author, having read the TC-001 report:

> Make an amendment and test a "dual arm" where its relevance and coverage
> only. Recency was only put in place for a conversational use case.

The second sentence is the substantive claim, and TC-001's own report already
argued the same thing from the other direction. Section 5 of that report, on
what the result does not license:

> LoCoMo asks questions about a whole finished conversation, so a recency
> window is close to worthless here **by construction** - its 61% budget share
> buys almost nothing on this corpus and might buy a great deal on a live
> continuing conversation, which is the setting the tier was built for.

So the request is not a rescue attempt. It names a confound TC-001 recorded as a
limitation, and asks for it to be removed and the measurement repeated.

## 2. Why this cannot be an amendment to TC-001

`AGENTS.md` section 5, in its own words:

> Legitimate amendments correct measurement units, repair protocol
> contradictions, and do not make a criterion easier after results are known.
> **Adding a factor, policy level, or budget is a new study and must be
> escalated.**

A third arm is a policy level. Two further rules bite in the same direction:

- **Section 7** forbids adding an arm after observing a result and reporting it
  under the original registration.
- **Section 9.4** forbids applying a bar - either bar - after a number exists.
  TC-001's numbers exist and are public. Any bar written into TC-001's own
  registration now would be written by someone who has seen them.

Folding the dual arm into TC-001 would therefore convert a clean registered
result into a contaminated one, which is the opposite of what the request is
for. **This amendment escalates instead.**

## 3. What this amendment does

1. **Records the escalation and its authorization.** The author asked for the
   arm; `AGENTS.md` section 5 requires that request to become a new study; the
   new study is `../TC_001B_PRE_REGISTRATION.md`, registered before any of its
   numbers were computed and locked in a commit containing no implementation.
2. **Binds the new study to TC-001's frozen machinery.** TC-001B inherits, and
   may not vary: the corpus and its split, the candidate identities, the
   embedding cache and its digests, the renderer, the packer, the drop policy,
   the budgets, the endpoint definitions, and the statistic. Anything it varies
   beyond the arms is a defect in it, not a licence granted here.
3. **Caps what TC-001B may claim.** Its arms were chosen after TC-001's result
   was known. It is therefore capped at `REGISTERED-OFFLINE` and explicitly
   labelled as characterization, exactly as TC-001 is, with the additional
   caveat recorded in its own section 9.

## 4. What this amendment does not do

- It does not reopen, revise, or re-run TC-001. Its disposition remains
  **`D3 FLAT_WINS`**, at 749 against 314, on the bars locked at commit
  `4c561e91`.
- It does not change any TC-001 artifact, hash, or reported number.
- It does not adopt, delete, or authorize a change to any shipped default.
  `EpisodicConfig.recency_window_n` stays at 32. TC-001B sets it to 0 **inside
  its own arm construction only**, and its report carries no deployment
  recommendation.
- It does not alter `TC_ARC_ROADMAP.md`. TC-002 through TC-006 are untouched
  and remain design only.

## 5. One reporting correction, which is amendment territory

TC-001's null band was derived from sham within-arm budget perturbations, and
`src/analysis/tc001_exploration.py::_sham_band` scored those perturbations on
the **any-evidence** endpoint:

```python
baseline["flat"][question.identity] = bool(target & set(flat_ids))
```

The registration then applied the resulting `B = 4` to the **complete-evidence**
primary as well as to the any-evidence secondary. The band was measured on one
endpoint and applied to two.

**This is recorded, not repaired, and it changes nothing.** The observed primary
margin was 435 against a band of 4, and the any-evidence secondary margin was
422; no plausible re-measurement of a packing-boundary wobble reaches either.
TC-001's disposition is unaffected and its artifacts are not reissued.

TC-001B measures its band on **both** endpoints and takes the maximum over all
four arms, so the defect is not carried forward.

## 6. Exclusions

- No corpus is spent that was not already spent. LoCoMo development was spent
  by NF-004, HH-001 and HH-002 before TC-001 and is spent again here; nothing
  in this escalation touches a sealed holdout, because this programme has none.
- No model call is authorized. TC-001B is replay-only against the CC-006
  read-only cache, and its guard makes a model call raise.
- No change to `episodic/` is authorized. `_context.py` is SHA-256 pinned inside
  TC-001's committed run header, so TC-001B's ranked variant restates the
  composition locally and proves it equal to the shipped function on every
  question at every budget before it is allowed to differ from it.
