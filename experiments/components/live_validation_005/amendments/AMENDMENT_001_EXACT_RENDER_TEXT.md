# LV-005 Amendment 001 — exact rendering text

**Status:** binding clarification before implementation  
**Date:** 2026-08-26  
**Parent registration commit:** `771eb828`

## Reason

The registration locks the meaning of each treatment preamble but does not
quote its literal text. Reader-facing wording is part of the intervention and
cannot be chosen during implementation. This amendment freezes that text before
the renderer exists. It changes no arm, population, runtime, endpoint or bar.

## Exact wrappers and preambles

All treatment blocks start with `<recent_context/>`, a blank line, and one of
the following opening tag plus note pairs. They end with the corresponding
`</retrieved_stm>` tag.

### T1 `GROUPED`

```text
<retrieved_stm organization="related_groups">
<organization_note>Evidence is grouped around query-relevant anchors. Groups are ordered by direct relevance. Within a group, a related spread item follows its query anchor.</organization_note>
```

### T2 `GROUPED_CHRONO`

```text
<retrieved_stm organization="related_groups_chronological">
<organization_note>Evidence is grouped around query-relevant anchors. Groups are ordered by direct relevance. Items within each group are ordered by when they appeared in the conversation.</organization_note>
```

### T3 `TEMPORAL_GUIDANCE`

```text
<retrieved_stm organization="related_groups_temporal_guidance">
<organization_note>Evidence is grouped around query-relevant anchors. Groups are ordered by direct relevance. Items within each group are in conversation order. Later means later in this conversation, not automatically a correction. For a current or latest question, prefer later evidence only when the text supports an update. For a historical question, use all relevant items.</organization_note>
```

Each group uses `<evidence_group rank="r">` and `</evidence_group>` on their own
lines. Each item uses an opening `<item ...>` line, the unchanged compact episode
element, then `</item>`.

- T1/T2 item attributes are exactly `role="query_anchor"` or
  `role="related_spread"`.
- T3 adds exactly one `temporal_role` attribute after `role`:
  `only_retrieved_item`, `earlier_in_conversation`, or
  `later_in_conversation`.
- Rank is one-based decimal group order.
- Tags, attributes and notes use the ASCII shown above and newline `\n`.

No other explanatory text, inferred entity label, current-state summary,
supersession label or renderer instruction may be added.
