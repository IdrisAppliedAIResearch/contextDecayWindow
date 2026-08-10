# Standing Rule — Mandatory Preflight

> **Binding standing rule.** `AGENTS.md` §4 carries the mandate and the ten check
> IDs; this file is the authority for their wording and for the failing precedent
> behind each one. Where the two disagree, this file governs.
>
> **Not retroactive.** It binds specs written from August 8, 2026 onward. Work
> already past its gates is not reopened by it — but where a completed study
> would have failed a check, that is recorded in the study's own report rather
> than quietly left out.

---

## Preflight — required in every spec, before any run

**No spec is complete without a Preflight section, and no run begins before Preflight passes.** This applies to studies, analyses, counterfactuals, diagnostics, engineering specs, and benchmark adoptions alike. A spec without Preflight is returned, not run.

Preflight has two parts and they run in order: **explore, then verify.**

### Part 1 — Exploration (characterize before you test)

**Before designing a test of a mechanism, characterize the mechanism empirically.** Not by reading the code, not by trusting its name, not by citing what a prior study said it did. Run it and record what it does.

The exploration is written into the spec as a required deliverable with committed artifacts, and its findings may change the design before anything is locked.

Minimum exploration for any spec that touches an existing component:

- **Behavioral identity.** What does this component actually do, measured on committed data? State it in one sentence that a reader could falsify.
- **Name-to-behavior check.** Every named component, block, tier, and variable in the design does what its name claims. **A name is a claim and must be tested like one.**
- **Distribution, not summary.** Report the shape of what the component produces. Medians conceal 18× aggregate changes; peaks conceal curves.
- **Degenerate and absorbing states.** Can the mechanism enter a state it cannot leave? Can it produce a constant output? For any mechanism with feedback — where an output influences a later input — this is mandatory and must be demonstrated on a real trace, not argued.

### Part 2 — Checklist (mechanical verification)

Every item is answered explicitly in the spec. "Assumed" is not an answer; "verified at `<SHA>`" is.

| # | Check | Failing precedent |
|---|---|---|
| **PF1** | **Inputs exist.** Every artifact the spec consumes is present, readable, and identified by hash. Count them | E006 Part 1: rarity scores existed for 6 of 76 episodes across three unreconciled variants; the gate failed closed after implementation |
| **PF2** | **Mechanism identity verified.** Each component's behavior confirmed against its name and its documented description, on committed data | The N tier was a least-recently-delivered coverage rotation rendering into `<recent_context>`; unexamined for eleven studies |
| **PF3** | **Gate ordering is enforced, not assumed.** Every gate is implemented and proven to execute *before* what it gates. Assert the ordering in git and in the run header | Study 011's determinism check was implemented and run after every arm was scored, unsealed, and reported. A gate that runs afterward is not a gate |
| **PF4** | **Thresholds are achievable.** Every bar, gate value, and kill condition is checked reachable given known limits, before it is locked. If unreachable, say so in the spec | Q11 required ≥14/17 with 11 reachable; Study 003's weighted route capped at 0.35 against a 0.60 threshold and was structurally unreachable |
| **PF5** | **Comparison keys are stable.** Replays and equality checks key on content hashes, never on generated identifiers, timestamps, or paths | An A0 replay gate compared `uuid4` values regenerated on every rebuild; 500 of 500 reports failed while delivered context was byte-identical |
| **PF6** | **Reproduction anchor.** Any replay or counterfactual reproduces a known prior result — by identity and payload digest, not by count — before new output is opened | Counts can match on different episodes |
| **PF7** | **Absorbing-state proof.** For any mechanism with feedback, a mechanical check demonstrating no absorbing state, run on a real trace of the intended length | Arm S locked at turn 11 and delivered the same block for 111 turns; the 35-turn ablation ran past the lock and recorded the result |
| **PF8** | **Ablation length is adequate to the failure.** State what the ablation can and cannot detect at its length | The 35-turn ablation could not detect a lock that begins at turn 11 and only becomes visible as staleness later |
| **PF9** | **Surrogate audit.** For every gate, bar, metric, and check: *can this pass while the property it certifies is false?* Record accepted residuals | The program's one named failure class |
| **PF10** | **Live-evaluation requirement stated.** If the mechanism affects delivery, the spec states that availability is not a verdict and names the live evaluation required | LV-001: 16/16 offline availability, 1.5/8 live |

### Scope note

**Preflight is not a formality and is not satisfied by asserting the items.** Each check names the artifact or the executed test that answers it. A Preflight section consisting of ticked boxes without artifacts is the same failure the checklist exists to prevent.

### Why this exists

Every item above is derived from a failure this program found in its own work, and in every case the failure was invisible to the checks that were running. The pattern is consistent: **the checks were aimed one level away from the property that mattered.** Structural purity verified a tier's absence and said nothing about what the surviving tier selected. Counters saw ten episodes a turn and volume was never the failure. A name was a name.

Preflight is the attempt to check the level where these live: what the thing *is*, before what it *scores*.

---

*Added August 8, 2026, following the Study 011 gate-ordering finding, the N-tier identity finding, and the Arm S lock.*
