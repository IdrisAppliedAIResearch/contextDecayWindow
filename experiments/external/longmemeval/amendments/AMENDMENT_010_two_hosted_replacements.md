# EC-001 Amendment 010 — Two hosted replacements

**Study:** EC-001 External Calibration on LongMemEval  
**Registration anchor:** `b595b05e1469c67277844d4bd97f77c89a20772b`  
**Scoring amendment anchor:** `37864822e4c429412b81f67db8af4af804308b8f`  
**Manual-switch amendment superseded in part:** `c2bd4b52ee0904c15135efcaf099e094da21b56c`  
**Completed local rater commits:** Phi `53fb26fc`; Mistral `06b6b3dd`  
**Status:** AUTHORIZED BEFORE CODEX-AGENT SCORING, TRIGGER PREPARATION, IDENTITY UNSEALING, OR FINAL AGGREGATION  
**Authorization:** Program author, August 3, 2026: “Just let me use 5.4
and 5.5.”

## Trigger

Amendment 009 assigned five hosted Codex models as replacement raters and Sol
as adjudicator. That is unnecessary. Two calibrated local rater families,
Phi and Mistral, are already complete and committed. The only unavailable
registered roles are the GPT-4o third rater and the GPT-5.2 independent
adjudicator.

No Codex-agent calibration, real-item scoring, trigger preparation, identity
unsealing, or final aggregation has occurred.

## Change

Supersede Amendment 009's five-rater panel and six-stage model sequence.
Preserve its manual-switch, fresh inherited-child, blindness, attestation,
retry, and reproducibility limitations.

Use exactly two hosted replacements:

1. **GPT-5.4 — third blind rater.** Combine its labels with the already
   committed Phi and Mistral labels. The rater panel is therefore Phi,
   Mistral, and GPT-5.4.
2. **GPT-5.5 — independent adjudicator only.** GPT-5.5 supplies no panel vote.

The fixed manual stages are:

| Stage | Parent model selected by user | Role | Resume phrase |
|---|---|---|---|
| C1 | GPT-5.4 | third rater | `EC001 RESUME C1 GPT-5.4 SWITCHED` |
| C2 | GPT-5.5 | adjudicator | `EC001 RESUME C2 GPT-5.5 SWITCHED` |

At each stage, the selected parent spawns one child with `fork_turns="none"`
and omits model and reasoning overrides so the child inherits the manually
selected model with no conversation history.

After C1 passes calibration and its 140-item output is committed:

1. combine the committed Phi, Mistral, and GPT-5.4 rater outputs;
2. prepare and commit H1-H5 triggers without opening the sealed identity map;
3. stop for the manual GPT-5.5 switch;
4. run C2 only on the committed masked adjudication packets.

The three-rater consensus and H1-H5 rules remain those in Amendment 004:
unanimous labels are final unless selected by H5; any disagreement is H2;
GPT-5.5 adjudication takes precedence for triggered items.

## Reporting boundary

- Do not produce or impute the pinned GPT-4o benchmark-protocol score.
- Do not compare GPT-5.4 labels directly with published LongMemEval scores.
- Report the consensus as a **Codex-substituted integrity score**.
- Phi, Mistral, and GPT-5.4 are three distinct named model lines, but GPT-5.4
  is a hosted Codex selection without an immutable API snapshot, fixed seed,
  temperature, or build hash.
- GPT-5.5 is a separate hosted model line from every panel member, but no claim
  of vendor- or architecture-level independence is made.

## Rationale

This is the smallest replacement that fills the two blocked roles. It retains
the two already valid local passes, avoids unnecessary hosted scoring, and
keeps the adjudicator outside the voting panel.

## Exclusions

- Do not run GPT-5.4 mini, Luna, Terra, or Sol.
- Do not rerun or reinterpret the committed Phi and Mistral passes.
- Do not use GPT-5.5 as a rater or GPT-5.4 as adjudicator.
- Do not edit reader answers, packets, mechanical-zero decisions,
  calibration expectations, rubrics, or local rater artifacts.
- Do not open `SEALED_MASK_MAPPING_DO_NOT_OPEN.json` before C1, trigger
  registration, and C2 adjudications are committed.
- Do not call the result official LongMemEval scoring or a benchmark-comparable
  GPT-4o score.
