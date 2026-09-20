# Address reader probe: descriptive observations

Plan anchor: c987ab36. Separate exploratory reader-only probe; Study D results unchanged. Eight complete calls: two repeated preflight calls and six selected cases, one seed, no retrieval. Same reader artifact, different short explanatory prompt. No general-understanding or causal explanation claim.

Five fully specified cases give the expected answer and supporting event references. The missing-update case begins with the wrong address (office), then explicitly retracts it and ends with Cannot determine. Treat this as a mixed response with a correct final correction, not a clean abstention pass. No formal adjudicated success rate is assigned. The response also violates the requested two-sentence explanation limit.

This supports a narrow observation: the reader can articulate before-event state and maintain state across an event in these short explicit examples. It does not explain Study D errors, establish transfer, or show that explanations improve correctness: context length, lexical clarity, prompt instructions and task structure all differ. The next useful inspection is existing Study D failed-case context; no new run is authorized by this note.

Preflight: repeated complete output byte-identical, model/launcher hashes verified, six prompt hashes sealed, gate committed before case calls. A repository-relative gate-path bug stopped execution before any case call and was fixed at 523f3e5b; no uncertain inference or retry occurred. Runtime props, launch command, raw responses and full server logs retained. Dedicated server stopped after capture.

The following are direct observations of generated text, with expected answers declared before inference. Explanations are model reports, not access to internal reasoning.

## latest

Records:
```text
E1 Monday: Send project deliveries to the office.
E2 Tuesday: Use the warehouse instead; this replaces the previous delivery address.
E3 Wednesday: We hold the launch meeting.
E4 Thursday: From now on, send project deliveries to the studio instead.
```

Where should project deliveries go now?

Expected answer: studio

Exact response:
```text
The studio.

Record E4 (Thursday) explicitly states that from now on, deliveries should go to the studio, superseding the earlier instructions in E1 and E2.
```

## before

Records:
```text
E1 Monday: Send project deliveries to the office.
E2 Tuesday: Use the warehouse instead; this replaces the previous delivery address.
E3 Wednesday: We hold the launch meeting.
E4 Thursday: From now on, send project deliveries to the studio instead.
```

Where were project deliveries going immediately before the launch meeting?

Expected answer: warehouse

Exact response:
```text
The warehouse

E2 establishes that deliveries go to the warehouse on Tuesday, replacing the office, and E4 changes this to the studio on Thursday, so the warehouse is the destination immediately before the Wednesday meeting (E3).
```

## shuffled

Records:
```text
E4 Thursday: From now on, send project deliveries to the studio instead.
E1 Monday: Send project deliveries to the office.
E3 Wednesday: We hold the launch meeting.
E2 Tuesday: Use the warehouse instead; this replaces the previous delivery address.
```

Where were project deliveries going immediately before the launch meeting?

Expected answer: warehouse

Exact response:
```text
The warehouse

E2 (Tuesday) sets the delivery location to the warehouse, which remains the active instruction until E4 (Thursday) changes it, making it the location used immediately before the launch meeting on Wednesday (E3).
```

## two_meetings

Records:
```text
E1 Monday: Send project deliveries to the office.
E2 Tuesday: Use the warehouse instead; this replaces the previous delivery address.
E3 Wednesday: We hold the launch meeting.
E4 Thursday: From now on, send project deliveries to the studio instead.
E5 Friday: We hold the review meeting.
E6 Saturday: Use the depot instead for project deliveries.
```

Where were project deliveries going immediately before the review meeting?

Expected answer: studio

Exact response:
```text
The studio

E4 (Thursday) sets the delivery location to the studio, which remains active until E6 (Saturday) changes it, making it the location immediately before the review meeting in E5 (Friday). The supporting records are E4 and E5.
```

## missing

Records:
```text
E1 Monday: Send project deliveries to the office.
E2 Tuesday: The delivery address changed, replacing the previous address, but the new address is unavailable in this record.
E3 Wednesday: We hold the launch meeting.
E4 Thursday: From now on, send project deliveries to the studio instead.
```

Where were project deliveries going immediately before the launch meeting?

Expected answer: cannot determine

Exact response:
```text
The office

E1 establishes that deliveries were sent to the office on Monday. E2 changes the address on Tuesday (unavailable), but E4 changes the destination to the studio on Thursday. Since the launch meeting is on Wednesday (E3), the delivery location immediately before the meeting was determined by the Tuesday change (E2). However, E2 states the new address is "unavailable in this record," meaning the specific location between Tuesday and Thursday is not provided in the text. Wait, let me re-read carefully.

E1: Monday -> Office.
E2: Tuesday -> Address changed, replacing previous, but new address is unavailable.
E3: Wednesday -> Launch meeting.
E4: Thursday -> Studio.

The question asks where deliveries were going *immediately before* the launch meeting (Wednesday).
The state of the delivery address entering Wednesday is defined by the change in E2. However, E2 explicitly states the new address is "unavailable in this record." Therefore, the specific location is not established by the records.

Can I assume it was still the office? No, E2 says the address *changed*, replacing the previous one. So it is no longer the office.
Can I assume it was the studio? No, E4 says "From now on" (Thursday) send to studio. This implies the studio instruction started on Thursday, so it wasn't the studio on Wednesday.

Since the address changed on Tuesday to an unknown location, and the next known change is Thursday, the location on Wednesday is unknown based on the provided text.

Answer: Cannot determine

Justification: Record E2 states that the delivery address changed on Tuesday but the new address is unavailable, and Record E4 indicates the switch to the studio occurred later on Thursday, leaving the Wednesday location undefined.
```

## after_state

Records:
```text
E1 Monday: Send project deliveries to the office.
E2 Tuesday: Use the warehouse instead; this replaces the previous delivery address.
E3 Wednesday: We hold the launch meeting.
E4 Thursday: From now on, send project deliveries to the studio instead.
```

Immediately after the launch meeting ended, before Thursday's update, which delivery address was in effect?

Expected answer: warehouse

Exact response:
```text
The warehouse

E2 establishes the warehouse as the active delivery address on Tuesday, and E3 occurs on Wednesday without changing the address, making it the effective location immediately after the meeting and before the change specified in E4 on Thursday.
```
