# Current chronological arm: thirty-question LoCoMo probe

Plan68df803d; inputs f8f34ecd; calibration7cccc37e; reader raw1607cbba; judge raw6f9140e7; original votes a454fa8f; Amendment001 at254c6fdb; corrected votes2e9548ec. September7,2026. Descriptive used-corpus reader evaluation, no causal chronology test or full-population estimate.

| Group | Correct final judge majority | Annotated evidence complete |
|---|---:|---:|
| Broad sample: two primary questions per conversation |13/20 (65%)|16/20|
| Additional temporal sample: one per conversation |5/10 (50%)|10/10|

Sampling is deterministic lowest content keys, no gold or historical outcomes. Broad20 contains11category4,5category2,3category3,1category1; supplemental10 allcategory2 and disjoint. Do not pool into an unbiased LoCoMo estimate. Only30 one-shot answers were generated; full LoCoMo remains paused.

Memory is fully deterministic: existing cosine>=.48 full pairs, chronological, uncapped, no recent block or anchor activation; exact previously frozen native prompts. One reader call/question, seed5005,thinkingOFF,serial,HH001 brief-answer prompt,40960context/4096output. No anchor instructions, model-assisted selection or feedback. Reader calls took89.35seconds,223output tokens. Broad median input7,387,max22,810; temporal median5,455,max16,934. Three local judge passes per answer plus15 synthetic judge and2 arithmetic calibrations; judges are evaluation only, not architecture calls. All outputs persisted, no capped/empty call, server stopped.

## What the reader did

It answered natural temporal questions correctly without a deterministic anchor: John started surfing in2018; Nate had the turtles3years; Caroline's picnic was the week before the dated July6conversation. It also failed on other natural temporal questions even with their annotated evidence delivered.

Examples of misses:
- Jon's fair: source dated April25 says yesterday; answer April25, gold April24. A concrete relative-date error.
- John's online support group: source dated January1 says joined last week; reader abstained.
- Audrey's dog adoption interval: both annotated passages delivered; reader abstained instead of3years.
- Dave's jam session: source dated September15 says last night; reader said last Friday before September15, against September14gold.

Some temporal discrepancies are answer/scoring-interface issues rather than plainly failed event understanding. Jolene's mother: reader copied last year from a January2023passage; gold2022. Park visit: reader said Last Sunday; gold Sunday before March2,2023. These lack an explicit reference date in the final answer. Harry Potter trivia is credited2/3 for Last August versus August2023, while one judge rejects its ambiguity; the positive rationales assume an unstated current date. The source supports August2023, but the answer-only judge does not see those dates. This inconsistency is disclosed; no posthoc normalization or score adjustment is applied.

Another corpus limitation: Sam's gym gold July28,2023 derives from a July27statement of intent, Starting tomorrow, I will go to the gym. The question asks when he started. The reader abstains. That does not prove inability to reason about sequence: the annotated source states a plan, not completion. Benchmark score remains as registered, with this evidentiary caveat.

## Scoring repair and limits

The carried parser initially produced4/10supplemental temporal. For James's cooking classes, answer Two days before4September,2022 equals the September2gold. All three judges initially wrote INCORRECT, then explicitly corrected to CORRECT. The original parser retained the first verdict. Amendment001 applies the last explicit verdict plus final reason to every90response, in both directions, after positive/negative/correction fixtures. It changes3votes for1question; final temporal5/10, broad unchanged. A fourth repeated-verdict response stays INCORRECT. Original raw/scores preserved; no new calls or rubric changes.

All90judgments are parseable with the repaired rule; one question has inter-pass disagreement. Single-agent review of disagreements and conspicuous errors is qualitative, not independent human adjudication. Primary is local three-pass final majority. Do not present50%as a finely calibrated temporal ability estimate given sample size, relative-date ambiguity, and benchmark plan/completion mismatch.

Complete annotation delivery is26/30, including all10supplemental temporal. Four broad cases are incomplete(three partial,one none); one partial case is answered correctly. Annotations are not exhaustive oracles of sufficiency. No evidence is added/removed based on scores.

This establishes that the current deterministic chronological arm can answer some natural temporal questions in a single LLM call; it does not establish that chronological ordering caused the successes or that it is sufficient. No relevance-order/full-context comparator was run. The next discussion can focus on the observed date conversion, answer ambiguity and abstention cases without adding a model dependency to memory. No additional run is started automatically.

## All questions and answers

| Group | Question | Reference | Reader answer | Majority | Evidence |
|---|---|---|---|---:|---|
| broad20 | What precautionary sign did Melanie see at the café? | A sign stating that someone is not being able to leave | I don't know. | 0 | none |
| broad20 | Why did Melanie choose to use colors and patterns in her pottery project? | She wanted to catch the eye and make people smile. | To catch the eye and make people smile. | 1 | complete |
| broad20 | What advice does Gina give to Jon about running a successful business? | build relationships with customers, create a strong brand image, stay positive | Brand identity is key, build relationships with customers, stay positive, and motivate others. | 1 | complete |
| broad20 | What did Gina design for her store? | the space, furniture, and decor | The space | 0 | complete |
| broad20 | When did John go to a convention with colleagues? | March 2023 | Last month (relative to 18 April, 2023) | 1 | complete |
| broad20 | Would John be considered a patriotic person? | Yes | Yes | 1 | partial |
| broad20 | When did Nate attend a cooking show? | The Monday before 14September, 2022 | Last Monday (relative to 14 September, 2022) | 1 | complete |
| broad20 | What kind of films does Joanna enjoy? | Dramas and emotionally-driven films | Dramas and romcoms | 0 | complete |
| broad20 | What year did John start surfing? | 2018 | 2018 | 1 | complete |
| broad20 | What is a prominent charity organization that John might want to work with and why? | Good Sports, because they work with Nike, Gatorade, and Under Armour and they aim toprovide youth sports opportunities for kids ages 3-18 in high-need communities. | I don't know. | 0 | partial |
| broad20 | How long does Audrey typically walk her dogs for? | about an hour | About an hour | 1 | complete |
| broad20 | What is a skill that Audrey learned to take care of her dogs? | Grooming | Dog grooming | 1 | complete |
| broad20 | What has John mostly found with the metal detector so far? | bottle caps | Bottle caps | 1 | complete |
| broad20 | What project did John work on with a game developer by 7 November, 2022? | An online board game | An online board game | 1 | complete |
| broad20 | When did Jolene`s mother pass away? | in 2022 | last year | 0 | complete |
| broad20 | How old is Max? | 8 years old | 8 years old | 1 | complete |
| broad20 | In light of the health and dietary changes discussed, what would be an appropriate gift for both Evan and Sam to encourage their healthy lifestyles? | a cookbook with healthy recipes or a subscription to a healthy meal delivery service. | I don't know. | 0 | partial |
| broad20 | What did Evan start doing a few years back as a stress-buster? | watercolor painting | Watercolor painting | 1 | complete |
| broad20 | When did Dave have a great jam session with his band? | September 14, 2023 | Last Friday (before 15 September, 2023) | 0 | complete |
| broad20 | What type of content does Dave post on his blog that inspired others to start their own DIY projects? | How he made his car look like a beast | How he made a car look like a beast | 1 | complete |
| temporal10 | When did Caroline have a picnic? | The week before 6 July 2023 | Last week (relative to the conversation on 6 July, 2023) | 1 | complete |
| temporal10 | When did Jon go to a fair to get more exposure for his dance studio? | 24 April, 2023 | 25 April, 2023 | 0 | complete |
| temporal10 | When did John join the online support group? | The week before 1 January 2023 | I don't know. | 0 | complete |
| temporal10 | How long has Nate had his first two turtles? | three years | 3 years | 1 | complete |
| temporal10 | When did John attend the Harry Potter trivia? | August 2023. | Last August | 1 | complete |
| temporal10 | How many years passed between Audrey adopting Pixie and her other three dogs? | three years | I don't know. | 0 | complete |
| temporal10 | When did James start taking cooking classes? | September 2, 2022 | Two days before 4 September, 2022 | 1 | complete |
| temporal10 | When did Jolene take Seraphim to the park? | Sunday before 2 March, 2023 | Last Sunday | 0 | complete |
| temporal10 | When did Sam start working out at the gym? | July 28, 2023 | I don't know. | 0 | complete |
| temporal10 | Which hobby did Dave pick up in October 2023? | photography | Photography | 1 | complete |
