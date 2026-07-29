# Study 010 Context-Peak Provenance Audit

**Status:** PASS
**Scope:** committed Study 010 serialized prompts and context telemetry

## Result

| Arm | Rows checked | Peak turn | Serialized chars | Chars before cue | Logged estimate | Recomputed estimate |
|---|---:|---:|---:|---:|---:|---:|
| arm_l | 1000 | 985 | 108,629 | 108,617 | 27,154 | 27,154 |
| arm_s | 1000 | 982 | 70,176 | 70,164 | 17,541 | 17,541 |

All rows match: **True**.
Inputs unchanged: **True**.

The runner computed telemetry from the complete constructed prompt before
appending the 12-character `\n\nAssistant:` generation cue. The logged
peak therefore does not use the undercharged LTM content total.

## Boundary

The telemetry is a character-based estimate from the serialized prompt, not an exact model-tokenizer count.
This pass does not repair or excuse the separate LTM budget violation.

## Integrity

- Input files: 2,002
- Input tree SHA-256 before: `b169659853eda44d84a7072395bd8405c5fb6841b0def8f36d471ee51f6a1b99`
- Input tree SHA-256 after: `b169659853eda44d84a7072395bd8405c5fb6841b0def8f36d471ee51f6a1b99`
