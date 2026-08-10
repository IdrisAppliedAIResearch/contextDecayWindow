# Amendment 001 — Phase 1 Report

## The Probe Reproduced Everything. Phase 2 Showed Why That Was the Wrong Conclusion.

**Amendment:** `../amendments/AMENDMENT_001_determinism_and_noise_band.md`, authorized 2026-08-09
**Measured:** 2026-08-09
**Evidence:** `phase_1_sampling_determinism.json`, `phase_1_recorded_prompt_replay.json`,
`phase_1_generations.jsonl` (800 rows, every generation)
**Status:** COMPLETE. **§3.1's hypothesis is NOT TESTED, because the symptom did not appear.**

> **SUPERSEDED IN PART, same day, by Phase 2.** This probe reproduced 820 generations
> without divergence and concluded the recorded divergence was an outlier of
> unidentified cause. Phase 2 then reproduced it exactly on the first turn of five
> 121-turn replicates — 343 characters against 80, diverging at character 79, matching
> both committed digests. **The probe missed it because it isolated the model call from
> the runner around it**: no store, no embedding model, no 121-turn sequence. It
> measured the call, not the system that makes the call, which is this program's
> recurring surrogate failure class with the probe in the surrogate seat. Every number
> below stands as measured; §4's third bullet and §5's framing do not. See
> `../noise_band/NOISE_BAND_REPORT.md` and `ERRATA.md`.

---

## 1. Result

**820 generations. Zero divergence.**

| Condition | Registered | Prompts | Generations | Reproduced | Identity rate |
|---|---|---:|---:|---:|---:|
| `standing_temp1_same_process` | §3.2.2 | 20 | 200 | 20/20 | **1.0** |
| `greedy_temp0_same_process` | §3.2.3 | 20 | 200 | 20/20 | **1.0** |
| `greedy_temp0_fresh_process` | §3.2.4 | 20 | 200 | 20/20 | **1.0** |
| `standing_temp1_varied_history` | **addition** | 20 | 200 | 20/20 | **1.0** |
| Recorded-prompt replay | **addition** | 1 | 20 | 1/1 | **1.0** |

No first-divergence position exists to report, in any condition, because nothing
diverged.

The prompt set is 20 committed Arm D windows, evenly spaced across the run by a rule
fixed in code, spanning **743 to 32,668 characters**. Generation goes through the
provider the live runs used, so the closed think block and the rule-detection suffix
are present; a probe on a call shape no study ever made would not characterize this
record's instrument.

## 2. §3.1's hypothesis is not supported, and not refuted — it is untested

§3.1 proposed that stochastic sampling amplifies non-associative GPU reduction into
different sampled tokens, and that greedy decoding should therefore reproduce where
sampling does not.

**The standing runtime reproduced.** There was no divergence for greedy decoding to
remove, so the comparison the hypothesis rests on cannot be made. The artifact records
this as `NOT TESTED` rather than as support, because a cure cannot be credited for a
symptom that never appeared.

**The greedy conditions were not the standing runtime under another name.** The server's
loaded parameters are asserted at startup, but that is a claim about configuration. The
behavioural check is that temp 0 and temp 1 produced **different text on 20 of 20
prompts**, so the flag reached the sampler. Without it, "greedy reproduces" would be
compatible with greedy never having run — the exact row §5's surrogate audit flagged.

## 3. Two conditions beyond §3.2, both disclosed as additions

Neither touches a criterion, a bar or a gate; neither feeds a decision rule; both can
only find **more** divergence than the registered conditions found, never less.

### 3.1 `standing_temp1_varied_history`

The registered design holds constant the one thing the recorded failure varied. In
`standing_temp1_same_process` every round visits the prompts in the same order, so each
request always meets the same predecessor and the same slot state. This condition
changes the visiting order each round and nothing else — same prompts, same repeat
count, same process, same sampler, same seed.

The order comes from a seeded shuffle rather than a rotation. Rotation preserves
adjacency, so every prompt would keep its predecessor while passing a naive check that
the order had changed; a test asserts the adjacency actually moves.

It reproduced everything. Request history is not the variable.

### 3.2 The recorded-prompt replay — the decisive one

Phase 1's registered prompt set never issues the prompt whose divergence the amendment
is built on. That prompt is **Arm A's ablation turn 1, 757 bytes**, and it is
byte-identical between the two committed runs.

| | Response | Characters | Output tokens |
|---|---|---:|---:|
| `study_011_ablation_a` | committed | 343 | 122 |
| `study_011_determinism_a` | committed | 80 | 56 |
| This replay, ×20 | **all identical** | 343 | — |

The two committed responses diverge at **character 79**. Twenty generations in a fresh
process produced **one** output, and it is the ablation's committed response, byte for
byte. **The determinism rerun's 80-character answer does not recur.**

## 4. What this establishes

- **The recorded divergence is real and is not retracted.** Two different answers to a
  byte-identical prompt are committed in the repository, and two tests now pin that
  premise so it cannot quietly stop being true.
- **It is not a property of seeded sampling.** 820 generations on this machine, this
  build and this model reproduced exactly, including 20 replays of the exact failing
  prompt. This report first called it an outlier; Phase 2 reproduced it deterministically
  on five 121-turn replicates, so *outlier* was wrong. The trigger is present in the
  full runner and absent from this probe.
- **The standing rule is satisfiable between runs that share process state.** Study 011
  §1.1 concluded that *require a byte-identical seeded prefix rerun* "is not satisfiable
  on this runtime." On this prompt, in a fresh process, it is satisfied 20 times out of
  20 — and Phase 2 later satisfied it across three consecutive byte-identical 121-turn
  reruns. **It is not satisfiable between a cold-start run and a warm-start one**, which
  Phase 2 also showed. This report originally concluded the committed sentence was simply
  too strong; that reading was wrong and is reversed in `ERRATA.md`.

## 5. What this does not establish

- **What produced the outlier.** The determinism rerun ran at 23:29 on a server the
  manifests record as having been up since 19:45 and having served roughly a thousand
  requests, including four 121-turn runs. Accumulated process state is a candidate.
  **It is a candidate, not a finding, and no mechanism is claimed.**
- **That the record's numbers are noise-free.** Phase 1 measures reproduction of a
  single call. It says nothing about the spread of a 121-turn run, which is Phase 2's
  question and is measured there.
- **Anything about other hardware or builds.** One machine, one llama.cpp build
  (`b9294-0f3cb3fc8`), one model file, one day.

### 5.1 A limitation of the record itself, not of this probe

`_server_pid()` reads `CDW_INFERENCE_SERVER_PID` from the environment and checks only
that the PID is alive. It does not discover which process is serving the port. Every
manifest on August 7 therefore records PID 13088 because the operator's environment
said so, and **"the same server process" in §1.1 is an operator-supplied assertion the
harness never independently established.** This does not explain the outlier and is not
offered as an explanation. It is recorded because a claim the artifacts do not actually
support should not be read as one they do.

## 6. Surrogate audit of this probe

The failure class here is a probe that reports reproduction because it never issued the
failing case.

| Check | Could it pass while the property is false? | What was done |
|---|---|---|
| Identity rate across repeats | **Yes** — identical repeats in identical order hold slot state constant | §3.1's added condition varies visiting order |
| Identity rate on the Arm D prompt set | **Yes** — the failing prompt is not in it | §3.2's added condition replays that exact prompt |
| "Greedy reproduces" | **Yes** — greedy may never have run | Behavioural check: 20/20 prompts differ between temperatures |
| Server settings asserted at startup | **Yes** — configuration is not behaviour | Same check, from the other side |
| 800 generations with no divergence | **Yes** — a divergence rate of 1 in 1,000 would very likely show zero here | Stated as a bound, not as proof of impossibility |
| The probe's prompt set and call shape | **Yes — and this is what happened** | Nothing. The probe issued model calls without the store, the embedding model or the 121-turn sequence around them. Phase 2 found the divergence immediately. **This row is the one that failed** |

**Accepted residual:** zero divergence in 820 generations bounds the rate loosely, not
tightly. It is consistent with a rare event, and the one recorded event is exactly that.

## 7. What Phase 1 does not authorize

§3.3, restated because the artifact is what a later reader finds first:

**Phase 1 does not change the standing runtime.** Temp 0 is a different runtime and
would break comparability with every prior study. **Phase 2 runs at temp 1 regardless
of Phase 1's outcome**, because Phase 2's purpose is to characterize the instrument the
existing record was produced on.

Nothing here bears on B1. §1.2's non-rescue clause is binding: Arm C scored 7.0 against
Arm D's 8.0, the packing correction is not adopted, and no measurement under this
amendment may be cited toward adopting K-first packing.
