# LV-007 — compact semantic-community rendering Part 1

**Type:** label-blind mechanism exploration  
**Date:** 2026-08-26  
**Status:** complete; no reader run, registration or outcome labels opened

## Behavioral identity

- **Pairwise control:** LV-005 `TEMPORAL_GUIDANCE` makes one group for every
  selected semantic episode and appends at most that episode's assigned selected
  spread child. It produced 1,069 groups over the 17 prompts: 452 singleton and
  617 paired groups.
- **Semantic community:** visit the same selected episodes in frozen relevance
  order. Assign each episode to the open group with the greatest mean affinity
  when that mean clears a threshold and the group is below its size cap;
  otherwise open a group. Affinity is a convex combination of episode-embedding
  cosine and IDF-weighted deterministic facet Ochiai overlap.
- **Chronology:** group rank follows the earliest frozen relevance position;
  unchanged episode elements are ordered only within a group by numeric
  conversation turn.
- **Question repeat:** the exact question string occurs before memory and again
  in the unchanged final answer cue. It does not affect selection or grouping.

The community renderer groups by episode content, not by retrieval route. CC80
and ASPECT identities may therefore occur in the same group without preserving
their frozen parent-child assignment.

## Inputs and calls

The population is the exact 17-row LV-005 prompt population and exact TC-014
32k opportunity selections: 1,686 selected episodes. The LV-005 prompt seal is
`d0a3ac38e15c1738387c9d3216de532195959dd4c8ac7515a03209bbfebe8b80`;
the TC-014 selection seal is
`32b1db4d5476cfe97eb6cb306c29c63d597b8bfc219ca73db181396ed5d750f7`.
The committed solo-vector cache supplied 2,236/2,236 hits and zero misses.
spaCy 3.8.14 `en_core_web_sm` supplied the already established six TC-011
facet families. There were zero new embedding calls and zero LLM calls.

## Distribution and degenerate states

Within the selected sets, episode cosine is weakly separated: min/median/max is
-.1496/-.0018/.1811 and p95 is .0489. At the carried threshold/cap, pure cosine
therefore yields 45/57/72 groups per prompt and a median group size of one. Its
median within-minus-between affinity is only .00052.

Facet Ochiai min/median/max is 0/.0629/1.0. The full label-blind sweep covers
embedding weights 1.0/.8/.5, thresholds .02-.05 and caps 4/6/8/12/unbounded.
Both absorbing regimes are demonstrated on these traces: a threshold above the
observed maximum makes every item a singleton; a sufficiently low threshold
makes the cap, rather than affinity, partition the list.

## Carried structural setting

The proposed registration will lock:

- embedding cosine weight `.8`;
- facet-Ochiai weight `.2`;
- mean-affinity threshold `.04`;
- maximum group size `8`.

Across the 17 prompts this produces 29/42/49 groups, group size 1/2/8, and
9/17/23 singleton groups per prompt (min/median/max). Within-group chronological
rendering changes the frozen flat order on 17/17 prompts. Six to fifteen groups
per prompt mix semantic and spread identities. The cap binds on 0/1/3 groups
per prompt, so it is active but not the dominant partition rule. Median
within-group affinity is .0237 versus .0128 between groups.

This setting was selected structurally: it reduces the 1,069 pairwise groups,
keeps groups at eight episodes or fewer, avoids the pure-cosine singleton
regime, and has measurable within/between separation. No gold answer, required
evidence identity, prior reader answer or arm mapping was used to select it.

## Surrogate audit and claim boundary

Mathematical affinity is not semantic coherence. Generic shared facets can join
unrelated passages, and weak cosine separation means a group can satisfy the
rule while remaining unhelpful to a reader. A compact layout can also improve
token count without improving answers. Part 2 must therefore preserve exact
evidence identities and episode bytes, expose cap-bound traces, and use a live
reader outcome. This exploration cannot establish answer quality, transfer,
production fitness or an optimal clustering rule.

Artifact:
`artifacts/part1_exploration.json`, SHA-256
`acd6a783a8ffd949b35ebe28788ea88a9b08de3c9b19ba7139da9547d815d78f`.
Exploration script SHA-256:
`1b68a34978f858a48299f948471642c9985672ee39a2ea706226157f6881f36f`.
