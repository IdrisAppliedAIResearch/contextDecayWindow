# Study 004 - Full Run 001 Failed Diagnostic: Response Truncation

**Recorded:** July 21, 2026
**Execution ID:** `study_004_full_001_failed_truncation`
**Source commit:** `9059b41c39efce9dd311c53f8d55d73b5d56e658`
**Condition:** Condition C v4 / iterative
**Protocol status:** Failed diagnostic; excluded from scoring and confirmatory analysis

## Run status

The run was stopped under the pre-registered monitoring rule after the first
three consecutive visibly truncated responses. The untouched partial archive
contains turns 1-13 because turns 11-13 were already in flight while the
process tree was being terminated. No rubric scoring or arbitration analysis
was performed.

The locked response budget remained 1,024 tokens. No prompt, runtime, memory,
or response-budget change has been made after observing this failure.

## Stop trigger

Turn 6 reached 1,024 tokens, followed by a non-capped turn 7. The first
consecutive stop-trigger sequence was turns 8, 9, and 10. Each response is
preserved verbatim in
[`responses.md`](runs/study_004_full_001_failed_truncation/condition_c/responses.md):

| Turn | Output tokens | Characters | Exact final text |
|---:|---:|---:|---|
| 8 | 1,024 | 5,047 | `6.  **Phased Replacement Strategy:** Based on the fatigue life assessment` |
| 9 | 1,024 | 5,027 | `ensuring that the foundation does not fail in shear or` |
| 10 | 1,024 | 4,814 | `9.  **Galvanic Corrosion Prevention:** S460` |

Turn 11 was also a coherent response truncated at 1,024 tokens. Turn 12 ended
normally at 923 tokens; turn 13 reached the cap. These in-flight turns do not
change the first stop-trigger sequence.

Archive integrity evidence:

1. `responses.md` SHA-256:
   `19B0CD5B32735FBF07561D3DF7E60D4366C309ADD1F6075D1E03D9AEEC6DE1F0`
2. `logs/turns.jsonl` SHA-256:
   `9CF05A3582E5A64446673A2F9FD407BAC3A2FF41A9DA60858099F19EF28EE32E`
3. Turn-8 prompt SHA-256:
   `B16702C03B6747513D9687E0F04DF65D6A08F09C8566448FCED6B7711ACFA3FE`
4. Turn-9 prompt SHA-256:
   `D9DE610E91EC0EC2D589044132CDCEAD615E8A99343BF9188B1271611BBBFD89`
5. Turn-10 prompt SHA-256:
   `FE8920338DF364F2F34E5E3A8D13DA08FE700792A509E603F5D1F745F0BB5FD4`

## Failure classification

**Classification: genuinely longer and clean.** This is response-budget
exhaustion under the registered UD-Q6_K_XL runtime, not tag echoing and not a
generation loop.

Evidence:

1. The three trigger responses remain coherent and advance through distinct,
   relevant numbered items until the final partial item. There is no repeated
   phrase, paragraph, list cycle, or semantic reset characteristic of looping.
2. None of the 13 stored assistant responses contains a context-construction
   tag or a `<rule_detection>` tag echo.
3. The constructed prompts for turns 8-10 contain one structurally balanced
   instance of each registered top-level context section. Empty retrieval
   sections are correctly self-closing; no malformed or duplicated tag is
   present.
4. LTM was empty: zero promotion events, zero LTM-in-context rows, and zero
   turns with an LTM context episode. The failure therefore occurred in the
   pure-STM regime and cannot be attributed to LTM retrieval or arbitration.
5. The responses follow the pinned numbered-list and engineering-risk rule.
   Their length comes from detailed treatment of broad technical questions;
   the output cap is reached before the requested rule-detection suffix can be
   emitted.

## Disposition

1. Do not apply a tag/prompt fix based on this evidence.
2. Do not treat this as a looping-runtime defect.
3. Preserve this execution only as a failed diagnostic; do not score it.
4. Keep the response budget at 1,024 unless a separate, author-approved,
   pre-run protocol amendment is written and committed.
5. If a 2,048-token amendment is considered, document its potential Bar 2
   non-regression confound and explicitly decide whether Study 003 requires a
   same-settings rerun to keep the baseline comparison honest.
