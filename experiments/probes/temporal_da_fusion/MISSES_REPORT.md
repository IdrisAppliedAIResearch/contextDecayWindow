# Why the four chronological-reader misses lack evidence

Exploratory existing-artifact audit, September 6, 2026. Plan **ba9d0dd6**, code **10fc36dc**. Four full140-record histories; eight exact packer replays plus original/chronological context equality. No new reader calls, policy, thresholds or scores.

**All four effective updates exist in storage and pass temporal eligibility. They are lost during packing. Newest-first retrieval fills its protected block with the anchor and intervening no-change notes before reaching the update. The semantic fill then also runs out of room before admitting it.**

## Exact failure points

| Project | Needed update | Temporal position | Direct relevance rank | Position in final merged order | Space left when final packer considers it | Exact extra cost |
|---|---|---:|---:|---:|---:|---:|
| Harbor-485 | turn55: office | 12 | 41 | 51 | 46 chars | 776 chars |
| Meadow-228 | turn60: warehouse | 12 | 33 | 42 | 742 chars | 782 chars |
| Riverside-324 | turn81: annex | 12 | 64 | 74 | 643 chars | 781 chars |
| Riverside-481 | turn45: laboratory | 11 | 35 | 45 | 609 chars | 787 chars |

In every case the temporal block admits10 records under its carried8,000-character allowance. Space left at the required record is129,38,32 and23 characters respectively. Each required update therefore fails this first route and must compete in semantic fill. The total32,000-character packer then rejects it at the positions and costs above. The exact cost includes serialization separators, so it is one character larger than the standalone episode fragment measured in earlier diagnostics.

This is a joint priority/packing/capacity limitation. Meadow-228 misses final fit by40 characters, but that does not license a40-character budget fix: the other misses differ, and a threshold fitted to these four cases would not be a sustainable completion rule. No capacity sweep or budget change was performed.

## What the reader actually sees

For Harbor-485 the selected history includes turn54, saying workshop. Turn55 changes the location to office, but is omitted. Turns57–64 are delivered and say that reviews made no location change, followed by a schedule check and the review anchor. Chronological presentation makes this incomplete sequence easy to follow; it does not tell the reader that the missing turn contained a change. The reader answers workshop.

The same pattern appears in all four cases:

| Project | Most recent delivered effective update before anchor | Missing later effective update | Chronological answer |
|---|---|---|---|
| Harbor-485 | turn54: workshop | turn55: office | workshop |
| Meadow-228 | turn57: studio | turn60: warehouse | studio |
| Riverside-324 | turn80: office | turn81: annex | office |
| Riverside-481 | turn43: hangar | turn45: laboratory | hangar |

Every wrong answer matches the latest effective location statement actually delivered before the anchor. This supports a stale-evidence explanation rather than requiring invented values. It is an observable input/output match, not proof of the reader's internal reasoning. Turn-number gaps remain visible, and the reader did not abstain; the probe does not establish that answering from an incomplete history is safe.

Future/proposal qualifiers are present: Meadow-228 includes a later announcement explicitly not yet effective; the Riverside cases include unaccepted proposals. Those records and the anchor are available. The missing piece is the effective state update, not the temporal question anchor or these qualifiers.

## What is and is not implicated

- Storage, candidate eligibility and rendering are cleared for these four misses: the update exists, is eligible and is rejected before rendering. Exact replays reproduce both selected ids and payloads.
- The additive last32 exchanges were unrelated later continuity and excluded from retrieval. Removing them occurred after selection and did not refill the retrieved block. These four required updates were absent in all three presentation arms; recency removal did not cause their absence.
- Chronological order helps interpretation of available evidence; it cannot repair an omitted update.
- The retrieval code knows to search before an anchor, but it does not identify the last effective update. Recency determines protected priority, and query similarity determines fallback priority.
- Existing fusion measurements recover Riverside-324 through a forward link from turn80 to81, but do not recover the other three under any tested variant. That is availability only; no chronological fusion reader was run.

The next design requirement is therefore **retrieve enough of the state history to establish the last effective value before the anchor**, while avoiding a block dominated by repeated no-change records. These synthetic first-sentence patterns make a hardcoded solution easy; they do not validate a general state-transition detector. A larger reader check should retain chronological presentation while treating evidence completion as a separate retrieval problem. No automatic deployment or new inference is implied.

## Audit trail

`chronology_artifacts/misses_audit.json` contains every source window, exact cost at rejection, selected temporal turns, existing fusion outcomes and input hashes. `misses.py` reproduces the carried temporal and final packer before reporting each case. Counts and selection membership match the committed verified Study E diagnostics and chronological probe contexts. PF1–PF10 follow MISSES_PLAN.md: fixed known misses, no outcome bars, finite replay, source identities/content anchors, no inference, and explicit limits on attributing reader behavior from source availability.
