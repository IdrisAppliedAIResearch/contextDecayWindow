# Amendment 003 — Human Rater Unavailable; Two of Correction 2's Three Components Restored

**Study:** 007
**Registered:** before any response was scored and before the sealed mapping was opened
**Amends:** pre-registration *Correction 2*, *Method — Evaluation*, *Open Decisions* item 5
**Status:** BINDING

---

## 1. What Correction 2 requires

Study 006 deviated from the scoring protocol on two counts, and the
pre-registration restores three properties in response:

| # | Component | Study 006 | Correction 2 requires |
|---|---|---|---|
| 1 | **Human rater** | agent | a human rater scores Q1–Q14 for both arms |
| 2 | **Score before mechanism logs** | violated — Bar 1 formation was computed first | no formation, retrieval, arbitration or dreaming output opened until scores are committed |
| 3 | **Blinding** | not attempted | arm identity masked; mapping sealed until scores land |

Open Decision 5 is explicit about the cost of not meeting these: *"Confirm the
human rater is available; if not, **the study waits** rather than repeating Study
006's deviation."*

## 2. What is actually available

**No human rater is available to this execution.** The study is being run
end-to-end by an agent under a standing instruction to register amendments and
continue rather than halt at pre-registered stop conditions. Waiting is not an
outcome this execution can produce; it would leave the study permanently
unfinished rather than finished with a stated limitation.

So component 1 **cannot be met**. Components 2 and 3 **can**, and both are met
in full — which is more than Study 006 managed on either.

## 3. What is done instead

| # | Component | Status | Mechanism |
|---|---|---|---|
| 1 | Human rater | **NOT MET** | agent rater (Claude Opus 5), same as Study 006 |
| 2 | Score before mechanism logs | **MET** | verifiable from git history: apparatus commit → scores commit → formation/retrieval analysis commit |
| 3 | Blinding | **MET** | `arm_A/` and `arm_B/` contain only responses; assignment is derived from a SHA-256 of the two response files; mapping sealed in `sealed_mapping.json`, committed unopened |

### Why the blinding is real and not declared

Study 006's rater knew which arm was which and had already computed Bar 1. Here:

- The arm-to-letter assignment is computed from a hash of the response files
  themselves, so **no one chooses it** — not the author, not the rater, not the
  script's caller.
- The anonymized files carry no policy name, parameter, record count, or log
  reference. The stale `Q1: Budget Cap`-style headers, which name an earlier
  study's question set, are stripped and replaced with the locked rubric's
  mapping — identical in both arms.
- The rater scores from `arm_A/responses.md` and `arm_B/responses.md` only, and
  does not read `sealed_mapping.json` until `rubric_scores.json` is committed.

This is enforceable for an agent rater in a way it was not in Study 006: the
mapping is not in context, and the responses do not identify their arm.

### Where blinding remains imperfect

Stated plainly, because a reader will work it out:

1. **The rater has domain knowledge of the study.** The agent scoring these
   responses has, earlier in the same execution, registered amendments and read
   the replay gate. It knows the treatment delivers a larger LTM block and that
   the replay predicted four-domain coverage. If one arm's Q11 answer enumerates
   four domains and the other does not, that is a strong cue to arm identity.
   **This cue cannot be removed** without removing the result being measured.
2. **Blinding protects against directional bias, not against inference.** It
   ensures no score is assigned *because* the arm was known at the moment of
   scoring; it does not make the arms indistinguishable.

Both were true of Study 006 as well, and unmanaged there. Here they are managed
as far as they can be and disclosed where they cannot.

## 4. Dual scoring (Correction 3) is unaffected

Correction 3 stands unchanged: any answer whose credit depends on a hedged or
alternative-offering formulation is scored twice — a **primary** score under the
locked criteria, which governs all bars, and a **strict** score in which a term
offered as one of several alternatives earns no credit. Both are recorded per
question with a written rationale, so any individual score can be audited or
replaced by a human rater later without re-running anything.

That last point is the practical mitigation for §3: `evaluation/rubric_scores.json`
carries per-question rationale for both arms, so a human rater can review the
judgments against the committed responses and substitute their own. The run
artifacts do not need to be regenerated for the bars to be re-derived.

## 5. Effect on the study's claims

The report must state, in the results section and not only in limitations:

- the rater was an agent, not a human, as in Study 006;
- scoring was blind and preceded every mechanism log, unlike Study 006;
- therefore **Bar 2's verdict is comparable to Study 006's in rater type**, and
  the cross-study comparison is not made worse by this deviation, but neither is
  it made sound;
- any bar verdict that turns on a single 0.5 must be reported with its
  sensitivity, as the pre-registration already requires.

Study 006's Bar 3 failed by exactly one 0.5 on the softest judgment in the
rubric. If Study 007 lands in the same place, the rater deviation is a material
limitation on the conclusion and must be named as one rather than buried.

## 6. Authorization

Registered under the author's standing instruction that the study finishes.
The alternative permitted by Open Decision 5 — waiting for a human rater — is
recorded here as the option not taken, and as the single cheapest improvement
available to this study's evidence: re-scoring the committed, unchanged
responses with a human rater would upgrade Bar 2 without any new run.
