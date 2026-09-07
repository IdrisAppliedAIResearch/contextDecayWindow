# Four incomplete-annotation cases: diagnosis

Plan2883ac93; implementation17918b18; raw8a16e6be. Recomputed cached cosine arrays for all30 questions with zero numerical difference; all selected identities and rendered prompts replay exactly. No model/embedding calls or selection changes. Five missing dialogue annotations across four questions map uniquely to five stored pair candidates. All five fail cosine>=.48; no ordering, context cap, cutoff or cache failure.

| Question | Missing dialogue | Pair cosine / rank | Finding |
|---|---|---|---|
| Melanie’s café sign |D16:16|.3733 /170 of214|Image caption contains the sign’s wording, but adapter drops it. Text carrier also fails threshold.|
| John patriotic? |D8:18|.3125 /283 of340|Serving my country is paired with unrelated London/home-decoration discussion. Following volunteer discussion is selected(.4834). Reader already answers Yes correctly.|
| Charity recommendation |D3:13,D3:15|.4252 /65; .4141 /89 of349|Nike/Gatorade/Under Armour details fall below threshold; generic charity aspiration is selected. Gold requires a recommendation using organization knowledge.|
| Healthy gift recommendation |D14:12|.4586 /174 of260|Missing text is supportive hiking talk, not the proposed cookbook/meal-service answer. Numerous diet/recipe passages are already selected.|

## Café: formation omission plus disconnected context

SourceD16:16 says thoughtful signs like this. Its separate blip_caption supplies a sign posted on a door stating someone is not able to leave, matching the reference. Neither that caption nor the image is in the cached pair text or renderer. Even selecting every existing text pair would not restore this annotated caption. Its pair also includes unrelated relationship discussion and scores.3733.

The immediately following pair is selected at.7661 and says that sign looks serious / The sign was just a precaution. We retrieved the reaction and omitted the thing it refers to. Recovering the prior pair alone still would not restore the missing caption. This is a concrete adapter-content problem as well as a selection discontinuity. Captions are benchmark-provided model descriptions, not verified image truth; preserve that provenance if they are admitted later.

## Patriotism: a missing supporting passage, not an observed answer failure

The omitted utterance explicitly says drawn to serving my country. Its full pair begins with the other speaker discussing London architecture and home decoration. It ranks283 at.3125 while the next pair about volunteering ranks9 at.4834 and enters. That demonstrates disconnected supporting passages; dilution by the unrelated paired text is a hypothesis, not proven without a matched representation test. Reader Yes matches gold already. Do not count this as a fourth wrong answer caused by retrieval.

## Charity: contextual prerequisites differ from the reference recommendation

The two missing pairs describe endorsement relationships and desired brands. The delivered D6:15 expresses a desire to give back through charity. The query asks which organization John might want to work with; the gold recommends Good Sports and supplies its sponsor/age/community details. Source inspection finds a generic good sports programs phrase atD26:21, not an explicit naming of that organization or those reference details. Thus retrieving endorsement passages would improve contextual coverage but does not itself put the entire gold recommendation into memory. This differs from failing to recall a stated fact; the answer-only prompt’s abstention instruction also matters. No reader rerun or external knowledge lookup performed.

The nearest selected pair to D3:13 within this audit’s two-pair neighborhood is two pairs earlier, discussing endorsements; D3:15 has no selected pair within two positions. Immediate-neighbor inclusion alone would not recover both missing prerequisites.

## Gift: annotation loss is not demonstrated missing answer support

155 of260 pairs were delivered. The single omitted annotation D14:12 says the hike will be awesome and I’m always here to support you. Adjacent hiking passages are selected, as are annotated diet improvements, healthy stir-fry, willingness to try recipes and starting a diet/exercise routine. A cookbook or meal-delivery subscription is an inferred recommendation; neither phrase occurs in the conversation. The missing supportive remark does not establish why the reader abstained or that necessary health/diet evidence was absent.

## Implication for deterministic memory

The four cases should not be treated as four equivalent retrieval-caused reader failures. We have a real caption representation omission, five mechanical threshold exclusions, disconnected references/support, and two inference-oriented reference answers. One incomplete case was answered correctly. Chronological sorting cannot reconnect records already excluded.

Prioritize source fidelity: design explicit treatment of already available captions before trying to tune relevance. Then examine deterministic linked-context completion while retaining semantic seeds and chronological presentation. This is narrower than replacing ranking with noun/subject similarity or unconditionally promoting neighbors; earlier TC009 and DA-fusion regressions remain relevant. A matched test is needed before attributing low scores to pair dilution or claiming completion improves answers. Lowering.48 to recover these five would be posthoc fitting and would not restore omitted captions.

No scores changed, no thresholds tuned, no reader reasoning mode changed, no generative dependency added. Full LoCoMo remains paused. Raw miss_audit.json contains every annotated carrier, source metadata, ranks, margins, selected-neighbor text and replay/cache hashes.
