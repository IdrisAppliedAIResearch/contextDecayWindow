# AGENTS.md - Operating Manual

Read this file before doing anything in this repository. It carries the program's history, standing rules, and workflow in a form that is cheap to load.

**If this file and a study's pre-registration disagree, the pre-registration governs. Stop and flag the conflict rather than reconciling it silently.**

## 1. Program

This repository contains ten pre-registered studies testing whether a language model can sustain a long conversation by rebuilding a small, relevant context each turn rather than carrying the whole transcript. Each study adds one component and addresses the previous study's documented failures.

The coding agent implements the registered design. Do not design studies, choose parameters, reinterpret criteria, or silently repair conflicts.

**This program is building something that does not exist yet.** Read §9 before reporting any result. Discipline is what makes a finding trustworthy; it is not a licence to report every stop as a dead end.

## 2. Study Digest

**Cap: 400 characters per entry.** Rewrite entries to stay below the cap; never expand the cap. Scores below are post-audit corrected values.

**001 - Retrieval baseline.** Recency (N) plus similarity (K), 32 turns. PARTIAL (2/3); iterative 8.0/10. K fired once at 0.70. Thirty topics formed for 32 episodes, so the topic layer compressed nothing. Iterative context exceeded full context.

**002 - Scale and consolidation.** 120 turns, four domains, topic consolidation, rule pinning. PARTIAL (3/4); C 8.5/13. K recovered buried middle-domain facts. Consolidation failed with 52 topics. Context stayed about 10:1 smaller than full context. Last Q6_K run.

**003 - LTM write path.** STM-to-LTM promotion with four filters. PARTIAL (2/3); 11.5/13. The weighted route was unreachable because novelty and association were complementary values from one centroid, capped below threshold. All promotion used the bypass, making it a novelty-spike detector.

**004 - LTM read path.** Parallel STM/LTM retrieval, arbitration, dedup, tagged blocks. PARTIAL (1/3); 6.5/13. LTM retrieval ran on all 90 eligible turns with zero displacement but the store lacked later-domain planted facts. Formation, not retrieval, was the constraint.

**005 - The inversion.** Permissive raw storage with extractive dreaming. PARTIAL; 11.0/13. Formation was faithful and junk-free, but absolute entity and number counts selected long responses. The salience metric was a verbosity detector; only 2/4 domains formed.

**006 - Span selection.** Sentence spans, density-normalized salience, source weighting. PARTIAL (1/3); 9.0/13. Formation reached 4/4 domains with faithful, junk-free records. Records shrank about 28x while retrieval remained count-budgeted, so delivery collapsed.

**007 - Retrieval budget.** Character budget, domain diversity floor, containment dedup. PARTIAL (2/3); 12.0/13. It delivered all four domains at the breadth probe but scored 0 there. Post-run review found the model used all 10 available facts without invention; seven required facts were absent.

**008 - Rendering by floor factorial.** Registered 2x2 over rendering unit and floor policy. STOPPED AT PRE-RUN GATES. No fill cap from 1-50 passed breadth and targeted-retrieval gates jointly. The gates prevented four invalid 121-turn runs. Count caps cannot substitute for character allocation.

**009 - Null test.** Pure STM versus best LTM at one seed, plus topic digest. PARTIAL; null decisive. S 9.0 versus L 12.0: the memory tier beat plain retrieval by 3.0 at 120 turns. The digest failed every offline setting through d=50/50,000 chars and was dropped pre-run.

**010 - Endurance.** Confirmatory STOPPED AT G2. Post-stop L beat S 14-12 on breadth only; targeted tied; scores unaudited. L's Q13/Q14 blocks violated 32k by 67.9%/68.2%, so the compact-store conclusion is withdrawn. Bar 3 NOT EVALUABLE. TopicManager and rule persistence failed at scale.

**Scoring integrity audit (2026-07-26).** Re-scored 222 items across 001-009; 19 changed. Study 002 A fell 8.0->5.5, C 13.0->8.5; Study 001 lost VALIDATED. The residual 16.5/about-20 figure extrapolates 3/26 control disagreements over 143 unreviewed items. Study 010 is unaudited. See `ERRATA.md`.

**Retrieval bakeoff (2026-07-29).** MIXED. Widened STM delivered 6/6 formation-blind facts, used 5. S/W/L: 9/11/12; Q4 is gap. Turn-55 ranked N=27/32; K=.120<.48. Exact compact packing needs 108,432 chars to reach it. This is a joint rank/packing/budget boundary, not a distinct primacy result. T6 6.5 invalid; no 1,000-turn run.

**DR-001 rendering fix (2026-07-29).** PASS. Q13/Q14 were 53,726/53,839 chars: 67.9%/68.2% over 32k, not saturated. Compact, content-identical tags reduce them to 37,619/37,545; exact cost is now authoritative. All 2,000 context estimates match serialized prompts; L peak 27,154 survives as chars/4. AS-001 owns Q4.

**AS-001 Q4 packing (2026-07-29).** DIAGNOSTIC. Branch D's primacy verdict was invalidated post-result: its null could not fire, and no branch interpreted exact charging reducing 15 fitted episodes to 9. Rank 27 enters only at 108,432 chars under N-first packing. This identifies a joint rank/packing/budget boundary; no pinned-tier study is authorized.

**E005 diversity selection (2026-08-01).** PROMOTION_ELIGIBLE offline. Set-level selection beats A0 6/17 in all 146 configs; best gate-passing 12/17 at 4/4 domains, 16/16 targeted, 4/5 oracle episodes. Facility location led on count (13/17) but gave monetary 0/4 and passed nothing. Escalations: r not inert (greedy fills budget); deployed pool yields 0 four-domain configs. No live run.

**DX-001 turn-90 miss (2026-08-01).** NO CHANGE. E005's whole remaining oracle gap is one in-pool episode at cosine rank 112 with 4 monetary items; 0/146 configs take it. Cluster collision refuted: its cluster is never entered, so diversity paid in full and it still lost by .169. Needed cosine .225, has .056. 12/17 ships with the miss characterized; objective escalates to unauthorized E006.

**RD-001 rarity diagnostic (2026-08-03).** STOP: measurement not identifiable. Full 119-rank replay passes; rarity covers 6/76 episodes across 3 non-primary variants. Mean IDF is worse than density on 5/5 eligible plants, but max improves 2 and sum/word 1, so the IDF-family claim is withdrawn. No coefficient; Part 2 unauthorized.

**E006 Part 2 chained retrieval (2026-08-10).** Rev5 COMPLETE offline, CHARACTERIZED. Corrected Gram recurrence passes PF11 12/12 at 9.5e-15; PF1-PF10 and PF7 48/48 pass. Chaining raises single-shot top-m 3/17 and X0 6/17 to 9/17 at D2/D3, but uses 15-20 candidates, selects 12, misses art 0/4, and trails E005 12/17. No targeted traces; no promotion or live run.

**E006 Part 3 associative frontier (2026-08-10).** COMPLETE offline, NO_DIFFERENTIATED_CUE; CHARACTERIZED. At D2,m5 all arms admit 15 candidates, but A2 has 5/17 candidate and packed facts in civil only, versus A0 9 candidate/7 packed and A1 9/9. Best A2 is 6/17; art 0 throughout. PF1-PF10 pass; no targeted/live run, promotion, or adoption.

**E006 Part 3 Rev4 autoassociation (2026-08-10).** STOP at Part 1, PATTERNS_NOT_STORED; CHARACTERIZED. Hebbian 1024-bit recurrence passes synthetic reachability but stores 0/119 real episode codes as fixed points. All converge into 6 spurious attractors; G4 and Q11 not entered. Balanced marginals did not provide pattern separation. Original P3 result unchanged.

**BA-001 benchmark causal audit (2026-08-11).** COMPLETE, CHARACTERIZED. At matched 15 candidates, fixed query and chain contain identical 9/17 facts; the chain's 7->9 gain is packing only. Radius-1 adjacency reaches turn 55 and all 4 art facts (oracle only). Span vs whole episode gives 10 gains/0 losses. Art was stored/directly recalled; prior-conflict cause unidentified. No live run.

**TA-001 temporal adjacency (2026-08-11).** G5 FAIL; TARGETED_REGRESSION, CHARACTERIZED. Matched 15 candidates/32k: Q11 candidate 9->10, packed 7->9, art 0/4->4/4. Across 24 targeted queries: 2 gains, 6 losses, 16 ties; enumeration .3125->.125. The bridge trades semantic seeds for neighbours. No ablation, live run, promotion or adoption.

**SR-001 extractive spans (2026-08-11).** G3 FAIL; NO_BROAD_GAIN, CHARACTERIZED. With identical full source ranks/32k, source-grouped spans reduce Q11 8/17->4/17 and targeted facts 19->17: 0 gains, 2 losses, 22 ties; enumeration stays .0625. BA's 10-gain signal required span reranking, not representation alone. No ablation/live run.

**SAL-001 surprisal proximity (2026-08-11).** G2 FAIL; NO_INDEPENDENT_PROXIMITY. On 92 held-out sessions, adjusted neighbor AUC=.416 (95% .351-.484; p=.991), raw=.300; prior=.399, next=.477, 5/6 strata below .50. Posthoc self AUC=.621: surprise stays local, not transferred. P1-P4 capture killed; no accessibility/ablation/live.

**SUP-001 explicit supersession (2026-08-11).** FACTUAL PASS; byte-identity criterion withdrawn. Binary accessibility makes current-only 0/64->64/64, unchanged 32/32, histories 64/64, zero stale natural selections. Value interpretation gives C0 8/9, T1 9/9; `$35`=`$35.00`. Zero regressions. No 120-turn run or adoption is automatic.

**DMR deterministic multi-route arc (2026-08-13).** DMR-002/003 upstream-cleared, NOT RUNNABLE. DMR-001B supplies the frozen former and DMR-001C confirms transfer, but both specs remain DESIGN ONLY with no Part 1 or pre-registration. DMR-005 is blocked by DMR-004; DMR-006 by DMR-005. Dependency clearance is not execution authorization.

**DMR-001 event-context formation (2026-08-12).** G3 FAIL; DEGENERATE_FORMATION. On the 2,000-episode holdout 52/74 events close on the size cap (.703 vs bar .35). All 20 drift boundaries match an annotation, precision 1.000; the 52 forced ones match none. Threshold .70 is above holdout drift's p95 but fires on 18.5% of dev: no transferable scale. G1/G2, PF1-PF10 pass.

**Study 010 corpus composition (2026-08-12).** Found by DMR-001. The 1,000-turn endurance script holds only 156 distinct user/assistant pairs: about 11 substantive turns per topical block plus ~70 exact repeats of a stay-on-thread filler. 844/1,000 episodes are exact duplicates. No published number changes; DX-002's saturation reading is qualified.

**DMR-001B adaptive drift formation (2026-08-12).** PASS, CHARACTERIZED. A percentile-of-recent-drift bar holds fire-rate swing at 1.42-1.65x where fixed swung 9x-inf; cap 128 never binds. Worst family .419->.487, but 1,000-turn falls .733->.583. DEVIATION_001. Its frozen former clears DMR-002/003's upstream dependency, not their missing registrations.

**DMR-001C sealed holdout (2026-08-12).** G5 FAIL; NO_BOUNDARY_EVIDENCE, but G4 CONFIRMS transfer. On 50 unread LongMemEval haystacks, 11,453 episodes, 2,128 real seams, the frozen relative rule holds fire-rate p95/p05 at 1.67x. Precision .837 vs .186 base rate, but recall .253 (min_event_size 5 vs 6-exchange sessions), so F1 .387 loses to C_PERIODIC_4's .606. F1 on a dense corpus rewards firing.

**DMR-004 query obligations (2026-08-12).** STOP; NO_MECHANICAL_SUFFICIENCY_SIGNAL. 180 sealed queries, two blind raters (finite kappa .770). Youden J .320 vs .50 and false-finite .188 vs .15 fail; LOOKUP recall .800, spans 1.000, 0/48 internal-only markers pass. Always-OPEN accuracy .650 vs .706. 12/31 misses are "which happened first, A or B", flagged pre-lock, not patched.

**NF-002 candidate granularity (2026-08-12).** CARRIES_SIGNAL; CHARACTERIZED. Registered session-touch rose 380->396/470; holdout 14 gains/6 losses, p=.058. Posthoc strict audit on 465 labelled items retains a smaller 375->388, 17 gains/4 losses. Formal disposition unchanged. Novelty null: 0/90.

**NF-003 ranking granularity (2026-08-13).** PREFLIGHT SURROGATE FAIL; UNREGISTERED. Session-touch said 396->445 (49/0), but 94 treatment hits carried no `has_answer` episode. Strict delivery fell 388->351: 26 gains/63 losses. Five unflagged items were never ranked. Proposed registration closed; LoCoMo successor stays sealed.

**NF-003 three-arm synthesis (2026-08-13).** CHARACTERIZED. Same 465 items/32k/strict measure: session-rank/session-pack 375, session-rank/episode-pack 388, episode-rank/episode-pack 351. Fine packing +13; fine ranking -37. The 63 coarse-rank rescues have median own-cosine rank 46 vs 10 for 26 fine-rank gains. Rule: rank coarse, pack fine.

**LoCoMo ranking development (2026-08-13).** DEVELOPMENT ONLY. On 871 unique questions, strict evidence delivery rose 820->855, 44 gains/9 losses, p=1.22e-6; complete evidence 773->826, 71/18. All four conversations were positive. Session-touch hid all 9 losses. No bars or disposition at this stage; NF-004 later opened the holdout.

**Ranking-budget controls (2026-08-13).** COMPLETE dev-only. LoCoMo source/session/pair at 32k: 279/773/826 all-evidence; pair beats session at every truncated 4k-80k budget. LongMem all-evidence crosses +8 at 16k to -14 at 24k, but overlapping corpus ratios have opposite signs. Binding ratio alone does not transfer.

**NF-004 LoCoMo confirmation (2026-08-13).** WORKS, availability only. On 1,098 sealed QAs at 16k, pair rank raises complete evidence 843->935 vs session inheritance: 140 gains/48 losses, ratio 2.92, p=6.19e-12. All 6 conversations net positive; source order 258, and 32k stays positive 961->1,024. G0-G7 pass, byte-identical replay, zero measurement calls. No live/adoption claim.

**NF-004 item anatomy (2026-08-29).** POSTHOC; NO_STABLE_PREDICTOR. Fifty-eight blind features on 188 discordances give grouped OOF AUC .576, permutation p=.139; 2/6 conversations reverse. Session rescues occur despite pair rank packing +6 candidates median. Packing contrast carries weak anatomy, not a selector. No calls/adoption.

**DA-001 linked context (2026-08-29).** POSTHOC LOCAL_LINK_SIGNAL. One-hop temporal expansion raises NF-004 complete delivery 935->950/951/956/959/963 across 1/2/4/8/16 seeds; all gains are link-carried, all losses displaced. Conv-44 regresses throughout. Full-event expansion falls to 845. Proxies only; no selector/reader/adoption.

**DA-002 link mechanism (2026-08-29).** POSTHOC. Temporal gains transfer rank: evidence rank p50 113-120, seed rank 1-4, about 44-60 ranks beyond direct capacity; prior/next are balanced. Shallow losses hit pack tail p50 .96-.98. Event depth adds few gains and 15-120 unique losses. Conv-44 has one rescue but two tail losses at m1. No selector/adoption.

**DA-003 edge utility (2026-08-29).** STOPPED_AT_CAUSAL_ACCOUNTING. Of 25,941 primary edges, 48 gains were neighbor-carried, but 9 came from downstream skip-on-overflow changes; 40 harmed. An edge insertion perturbs later fit decisions, so edge-local utility assigns wrong causal credit. No model/gate ran. A successor must score the whole pack perturbation.

**DA-004 pack perturbation (2026-08-29).** BENEFIT_SIGNAL_ONLY. Whole-pack blind features predict 57 helpful edges with grouped OOF AUC .823; all 6 conversations .800-.960. Added-set query coverage AUC .831. Harm model is chance at .504 and reverses on conv-44; harms occur in only 3/6 conversations. No safe gate, threshold, reader or adoption.

**DA-005 displacement guards (2026-08-29).** STOPPED_AT_PF4, label-blind. At fixed 16k, 0/26,100 edges add a candidate with zero displacement; the only structurally safe guard admits nothing. Count<=1 admits 4,285 but cannot protect the one displaced item. No labels opened. Useful protection requires compact links or prospectively reserved headroom.

**DA-006 reserved compact links (2026-08-29).** STOPPED_AT_CAUSAL_ACCOUNTING. Repacking direct under 16k-R is not a subset: skip-overflow created 1 non-link gain. Poststop, pair/turn gains peak 48/35 while reserve losses rise 73/123/220/456. TURN helps only at R256 (30 vs 10 gains), still 73 losses. Next core must be immutable DIRECT prefix.

**DA-007 immutable prefix reserve (2026-08-29).** NO_PROTECTED_CAPACITY_SIGNAL. Pair/turn gains vs suffix losses at R256/512/1024/2048: 10/30 vs73, 43/35 vs123, 48/35 vs220, 45/33 vs456. Best TURN_R256 net -43. Fixed reserve is often unused; direct tail carries evidence. No reserve/renderer/adoption.

**DA-013 cross-corpus compact links (2026-08-30).** SPENT STRESS TEST; RANKING NULL. On 465 LongMem items at 16k, immutable compact temporal fallback raises complete evidence 164->171, 7/0, p=.015625; oracle 250. All 7 gains are singleton turns. DA-004 transfer and temporal orders are identical on 465/465: protected-pack features saturate. No reader/fresh/adoption claim.

**DA-014 reachable-gap audit (2026-08-30).** CAPACITY_BLOCKER. Of DA-013's 86 one-hop-reachable direct misses: 7 rescued, 49 payload too large initially, 12 conjunction, 12 prior consumption, 6 wrong member, 0 unaccounted. Initial-size deficit p50 91 chars (p90 223). More ranking addresses at most 18; the ceiling is reversible representation capacity. No selector/reader/adoption.

**DA-015 phrase dictionary (2026-08-30).** TRANSFERABLE_CAPACITY_SIGNAL, mechanical only. Exact phrase references save median +448.5 chars on 1,104 NF-004 contexts and +863 on 465 LongMem contexts; zero expansion, byte-identical replay. Added slack clears 47/49 DA-014 initial-size oracle thresholds. Codec is slow and reader use is untested. No delivery/fresh/adoption claim.

**DA-016 phrase-coded links (2026-08-30).** PHRASE_LINK_DELIVERY_SIGNAL, spent availability. Frozen 16k temporal links raise LongMem complete 171->188, 17/0, p=1.53e-5; direct 164, oracle 250. Allocation pairs/turns 51/507->358/1046. All gains are singleton-carried, seed ranks 1-13. Exact dictionaries preserve direct evidence; reader use/runtime/fresh transfer unvalidated.

**DA-017 NF-004 phrase-link transfer (2026-08-30).** NO_CROSS_CORPUS_PHRASE_LINK_SIGNAL. Frozen phrase coding raises DA-010 970->973, 3/0, p=.25, below +5 bar; direct 935, ceiling 986. Conv-43/49/50 gain one, none regress. Capacity transfers mechanically, delivery is strong only on LongMem (+17). DA-004 ranking remains non-general. No tuning/reader/adoption.

**DA-018 frozen-query carrier utility (2026-08-30).** NO_CROSS_CORPUS_CARRIER_UTILITY_SIGNAL. NF control/cosine/cost/marginal = 970/952/944/960; LongMem = 188/179/189/191. Marginal trades 1/11 on NF and 6/3 on LongMem. Frozen-query rescoring avoids TC-012 drift but local relevance/cost cannot replace corpus-specific whole-pack or temporal priors. No tuning/reader/adoption.

**DA-025 LongMem atomic additions (2026-08-30).** NO_LONGMEM_ATOMIC_ADDITION_SIGNAL. Pair-first atomic fallback raises DA-023 202->211 but trades 17 gains/8 losses; temporal reasoning is +1/-5. It rescues 15/20 wrong-member residuals, proving the operation useful but the order unsafe. DA-023 remains strongest; successor must replay it exactly and use residual capacity only. No calls/adoption.

**DA-026 protected atomic tail (2026-08-30).** PROTECTED_ATOMIC_TAIL_SIGNAL. Replaying DA-023 fully, then adding missing members in frozen order, raises LongMem 202->207, +5/0 (p=.0625); all types nonnegative. Four gains are wrong-member residuals. 574 admissions use fragmented tail slack; strongest order is immutable. Spent availability only; no reader/runtime/adoption claim.

**DA-027 compact relative backrefs (2026-08-30).** STOPPED_AT_BLIND_NO_EXPANSION. Codec gates pass 9/9, but a LongMem immutable pack expands when compact pointers are forced, so no allocation artifact or outcomes. DA-023 already retains control rendering on 16/465 rows. Universal codec is closed; evidence-blind shortest-exact-codec fallback is the successor. Zero calls.

**DA-028 shortest exact codec (2026-08-30).** PARTIAL_SHORTEST_EXACT_CODEC_SIGNAL. Exact fallback selects compact on NF 1098/1098 and Long 461/465, saving median 591/556 chars with immutable order. NF 976->977 (+1/0) despite 2,599 additions; Long 202->208 (+6/0, p=.03125), 5 prior-consumption rescues. Capacity works where traversal reaches dependencies; no reader/adoption.

**DA-029 compact residual audit (2026-08-30).** MIXED. Remaining NF 9 = prior consumption 5, wrong member 3, conjunction 1; Long 42 = wrong member 24, prior 10, conjunction 5, initial size 3. No class reaches 60%; no shared successor. Protected atomic completion after DA-028 is the strongest composition, while prior consumption needs a separate dependency representation. Zero calls.

**DA-030 compact+atomic composition (2026-08-30).** PARTIAL_COMPACT_ATOMIC_SIGNAL. Full DA-028 packs stay immutable; post-pack members raise Long 208->213 (+5/0), all wrong-member residuals, but NF stays 977 (+0/0) despite 567 admissions. NF members fit at earlier arrival, not after the protected suffix: remaining limit is representation capacity through the sequence. Zero calls/reader/adoption.

**DA-031 varint relative pointers (2026-08-30).** PARTIAL_VARINT_RELATIVE_SIGNAL. Self-delimiting exact coordinates save median +1066 NF/+889 Long chars beyond DA-028 with immutable order. NF 977->983 (+6/0, p=.03125), rescuing all 5 prior-consumption plus 1 conjunction; Long 208->211 (+3/0). NF is 3 below one-hop ceiling. Zero calls; reader/runtime/adoption unvalidated.

**DA-032 varint residual audit (2026-08-30).** CORPUS-SPECIFIC. NF's final 3 are all wrong-member but 0/3 fit postpack: median slack 9 vs cost 108, so atomic completion is not protected. Long 39 = wrong 21, prior 12, conjunction 5, initial 1; 17 fit postpack. Long supports protected atomic composition; NF needs further exact representation capacity. Zero calls.

**DA-033 LongMem varint+atomic (2026-08-30).** LONGMEM_VARINT_ATOMIC_SIGNAL. Full DA-031 pack stays immutable; postpack members raise Long 211->222, +11/0 (p=.0009766), all types nonnegative. Gains are 9 wrong-member and 2 conjunction residuals. 842 members admitted at median cost 113. Capacity plus atomic dependency identity composes safely; reader/runtime/adoption unvalidated.

**DA-034 NF sentinel varint (2026-08-30).** NO_NF_SENTINEL_VARINT_SIGNAL. Opcode-free exact pointers save median +823 chars beyond DA-031 and add 389 frozen-order actions, but NF stays 983 (+0/0). Capacity goes to late full-pair/frozen-member carriers, not the final 3 alternate members. Codec-only extension closes; successor must spend recovered capacity at atomic member granularity with DA-031 immutable. Zero calls.

**DA-035 NF sentinel+atomic (2026-08-30).** NF_SENTINEL_ATOMIC_SIGNAL. Same sentinel capacity as DA-034, but independent member allocation raises NF 983->986 (+3/0), reaching the frozen one-hop ceiling. DA-034 carrier unit gained 0; atomic unit gains all 3 wrong-member residuals. 3,401 members admitted; immutable DA-031 control, zero calls. Availability only; reader/runtime/adoption unvalidated.

**DA-036 LongMem atomic residual audit (2026-08-30).** DOMINANT_INITIAL_ATOMIC_SIZE. Of 28 reachable misses after DA-033, 18 are too large before the tail, 9 lose fit to prior blind atomic additions and 1 needs multiple carriers; 0 unaccounted, 0 fit postpack. Initial/final slack p50 87.5/23 vs missing-member cost 253. Next signal is stronger exact representation under immutable order, not rescoring. Zero calls.

**DA-037 LongMem sentinel+atomic (2026-08-30).** NO_LONGMEM_SENTINEL_ATOMIC_SIGNAL. Sentinel saves median 723 chars and gives 230 vs DA-033 222: 9 gains/1 loss, net +8, p=.0215; DA-031 211 has 0 losses. Gains hit 6 initial-size, 2 prior-consumption, 1 multi-carrier. Zero-loss bar fails: independently reallocating the tail does not protect strongest DA-033 order. Next must freeze DA-033 then append. Zero calls.

**DA-038 protected DA-033 sentinel tail (2026-08-30).** PROTECTED_DA033_SENTINEL_SIGNAL. Exact re-encoding freezes every DA-033 member, saves median 739 chars, then appends atomic members: Long 222->232, +10/0, p=.001953. Gains resolve 6 initial-size, 3 prior-consumption, 1 multi-carrier; all types nonnegative. Protecting the strongest tail removes DA-037's loss. Ceiling 250; reader/runtime/fresh unvalidated. Zero calls.

**DA-039 protected sentinel residual audit (2026-08-30).** DOMINANT_PRIOR_SENTINEL_ATOMIC_CONSUMPTION. Of 18 reachable misses after DA-038, 17 fit in initial sentinel slack then lose fit to earlier append-only payloads; 1 is initially too large, 0 unaccounted, 0 fit postpack. Initial/final slack p50 765/41.5 vs missing cost 239. Next signal is compact dependency references before materialization, not rescoring. Zero calls.

**DA-040 compact dependency frontier (2026-08-30).** COMPACT_DEPENDENCY_FRONTIER_SIGNAL, resolver only. Five-char local member refs append after immutable DA-038: 3,325 fit/4,730 overflow; 7/18 residual sets become fully externally reachable (6 prior-consumption, 1 initial-size), 11 remain. Per-member metadata still scales linearly; next signal is one range/head ref to the deterministic frontier. References are not delivered facts; no reader/runtime/fresh claim. Zero calls.

**DA-041 frontier head (2026-08-30).** FRONTIER_HEAD_SIGNAL, resolver only. One 3/5-char head names the deterministic absent-member list after immutable DA-038: 436/465 heads fit, resolving 7,551 targets; 17/18 residual sets become reachable (all multi-session), zero mutation. DA-040 reached 7/18 with linear refs. One miss lacks even 3 chars, locating the next boundary in out-of-band control-plane metadata. Not delivered evidence; zero calls.

**DA-042 control-plane head (2026-08-30).** CONTROL_PLANE_HEAD_SIGNAL, addressability only. A typed out-of-band head preserves DA-038 prompt bytes/charge exactly and resolves 8,055 absent members; all 18 residual sets become graph-reachable, zero rendered chars/mutations. Flat refs reached 7/18 and rendered head 17/18. This separates immutable payload nodes from dependency graph metadata. Delivery remains 232; dereference/materialization, reader/runtime/fresh transfer unvalidated. Zero calls.

**DA-043 dereference burden (2026-08-30).** SHALLOW_SINGLETON_DEREFERENCE. All 18 DA-042 residuals map uniquely to one frontier node; no conjunctions. Required depth p50 15, p90 21.9, max 30. Rendered payload chars p50 351, p90 463.5, max 1,906; 16/18 fit 512, 17/18 fit 1,024, all fit 2,048. A fixed first-32 auxiliary page is the next blind materialization probe; reader/delivery untested. Zero calls.

**DA-044 auxiliary frontier page (2026-08-30).** WEAK_AUXILIARY_FRONTIER_PAGE_SIGNAL. Separate 16k prefix pages raise Long 232->237, +5/0, p=.0625, but p50 page is 14,817 chars and only 7 nodes. Population adds 6.54M chars, 1.31M/gain; no multi-session or temporal residual gains. This directly confirms inefficient token flooding. Fixed pages close; next signal is replaceable one-node traversal with bounded peak and explicit cumulative cost. Zero calls.

**DA-045 replaceable node stream (2026-08-30).** REPLACEABLE_NODE_STREAM_SIGNAL, exposure only. Fixed depth-32 traversal exposes all 18 residual payloads with immutable DA-038 and <=2,048 peak chars. Through target: cumulative chars p50 5,569/p90 17,692; frames 7/16; peak 1,851.5/2,037.1. This removes simultaneous flood, not cumulative work. Reader recognition, retention and stopping remain untested; another offline score cannot answer them. Zero calls.

**DA-046 single retained frame (2026-08-31).** ORACLE_SINGLE_REGISTER_SUFFICIENT. Sealed current/retained contract plus evidence-aware KEEP raises Long 232->250, +18/0, p=7.63e-6, reaching the one-hop ceiling with immutable DA-038. Oracle path peak <=2,047 chars; retained p50 355, cumulative traversal p50 5,569. Proves bounded retention if recognized; recognition/stopping/reader remain untested. Zero calls.

**DA-047 protected boundary substitution (2026-08-31).** REGISTERED blind contract. DA-038 order and DA-046 retained frame stay immutable; only transient current may be atomically replaced by an exact hash-verified frame of no greater cost within 2,048 chars. Rejection rolls back byte-for-byte. No outcome, utility, reader or adoption claim; zero calls.

**DA-048 directional continuation (2026-08-31).** SECOND_HOP_CAPACITY_SIGNAL. Continuing each frozen temporal edge one episode in direction raises protected Long availability 250->295, +45/0 (p=5.68e-14). Gains: temporal 27, multi-session 9; useful frame ordinal p50 5, frame 309 chars, cumulative p50 1,361. Immutable payload; evidence-aware KEEP only; reader untested. Zero calls.

**DA-049 directional residual audit (2026-08-31).** FARTHER_DIRECTIONAL_SIGNAL. After DA-048, 170 misses split into 37 singleton targets farther on frozen rays, 78 multi-member, and 55 off-ray. Directional distances are d3=18, d4=10, d5=9; all 37 fit a 2,048-char frame. Next probe is a frozen cursor through distance 5, then grouped retention. Evidence-aware anatomy only; zero calls.

**DA-050 directional cursor (2026-08-31).** FAR_DIRECTIONAL_CAPACITY_SIGNAL. A replaceable distance-3-to-5 cursor raises protected Long availability 295->332, +37/0 (p=1.46e-11), recovering every farther-ray singleton. Useful ordinal p50 7, frame p50 285 chars, cumulative p50 3,190/p90 9,909.6. Fixed 2,048 peak; evidence-aware KEEP, reader/stopping untested. Zero calls.

**DA-051 grouped residual audit (2026-08-31).** DISTRIBUTED_DEPENDENCY_SIGNAL. Remaining 133 split into 55 one-member, 2 one-episode multi-member, 6 same-session multi-episode and 70 multi-session. Both grouped episodes overflow 2,048. Distributed cases need 2/3/4/5 episodes in 47/18/8/3 rows. Grouping closes; next is a protected exact retained set up to five. Zero calls.

**DA-052 protected retained set (2026-08-31).** RETAINED_SET_CAPACITY_SIGNAL. Five append-only exact slots over sealed streams raise protected Long availability 332->363, +31/0 (p=9.31e-10). Gains need k2/3/4/5 frames=24/4/1/2; retained p50 646 chars, peak p50 2,223. Traversal p50 27,333 chars, so recognition/stopping now dominate. Evidence-aware KEEP; zero calls.

**DA-053 retained-set residual audit (2026-08-31).** ADDRESSABILITY_BLOCKER. Of 102 residual questions, 100 are all-absent from sealed temporal streams and 2 all-overflow; 134/136 missing members are absent and 2 overflow at distance 2. Compression can address at most two. Next separate farther evidence in seeded sessions from unseeded-session evidence. Evidence-aware anatomy; zero calls.

**DA-054 session address audit (2026-08-31).** UNSEEDED_SESSION_BLOCKER. Of 134 absent members, 133 are in sessions untouched by the complete direct pack; 1 is in a top-16 session at distance 3 and 0 are direct-tail-only. Questions: 99 untouched, 1 seeded, 2 overflow-only. Longer rays close; next is an out-of-band deterministic session directory. Evidence-aware anatomy; zero calls.

**DA-055 session directory (2026-08-31).** SESSION_DIRECTORY_ADDRESSABILITY_SIGNAL. An out-of-band sidecar links 22,182 sessions, 106,412 episodes and 212,824 members with zero rendered chars, resolving all 134/134 absent members unambiguously. Target session ordinal p50 27.5, but episode order p50 0/p90 2 and pointer hops p50 3. Session choice, not local depth, is next. Zero calls.

**DA-056 session-local materialization (2026-08-31).** SESSION_LOCAL_CAPACITY_SIGNAL. Exact directory dereference plus five retained slots raises protected Long availability 363->459, +96/0 (p=2.52e-29). Gains open p50 1 session, use p50 4 pointer hops, retain p50 409.5 chars and peak p50 2,029.5. Six misses remain, all 2,488-3,094-char exact-member overflow. Head choice oracle-only; zero calls.

**DA-057 episode derivative codec (2026-08-31).** NO_EPISODE_DERIVATIVE_CAPACITY_SIGNAL. Frozen DA-031 user->assistant backrefs select coded form for 104,084/106,412 episodes and save 14.4M chars, but residual frames remain 2,589-3,399 (savings 29-286); Long stays 459, +0/0. Premise backrefs close; next is exact retained chunk chaining. Zero calls; reader interpretation untested.

**DA-058 exact chunk chain (2026-08-31).** EXACT_CHUNK_CAPACITY_SIGNAL. Deterministic 1,984-char contiguous chains raise protected Long availability 459->465, +6/0 (p=.03125), reaching the full mechanical ceiling. All six use 2 chunks; total retained slots 2-3, retained/peak p50 2,814, max 3,111. Capacity is solved mechanically; session choice and reader reconstruction remain oracle-only. Zero calls.

**DA-059 sparse session postings (2026-08-31).** BROAD_SPARSE_SESSION_SIGNAL. Exact query-token unions cover required sessions 465/465 but route p50 44 sessions, fraction p50 .918/p90 .960; first/last required rank p50 13/28. It is score-free control-plane flooding, not selective head choice. Singleton union closes; next is exact token-pair postings. Zero calls; no delivery/reader claim.

**DA-060 token-pair postings (2026-08-31).** BROAD_TOKEN_PAIR_SESSION_SIGNAL. Exact unordered query-pair unions retain required-session coverage 465/465 but route p50 43 sessions, fraction p50 .909/p90 .957; only one median session better than singleton union. Pair co-occurrence remains control-plane flooding. Next is exact contiguous bigram postings. Zero calls; no delivery/reader claim.

**HH-004 DA-098 decoded benchmark (2026-09-01).** CHARACTERIZED. On 842 matched LoCoMo items, decoded DA-098 scored 606 (.720): episodic 655, aspect 670, CDW 655, RAG 383, full 622. Paired net: -49/-64/-49/+223/-16; full p=.271. Mechanical evidence ceiling did not transfer to answer accuracy. One watchdog restart recovered; zero failed/malformed. No adoption.

**HH-005 semantic+DA aspect-v2 (2026-09-02).** NO_ASPECT_V2_IMPROVEMENT. On 842 matched items, DA-v2 16k/32k scored 649/654 vs ASPECT-v1 670. Versus v1: 26/47 (p=.0186) and 32/48 (p=.0929); 32k vs 16k 27/22 (p=.568). Preserving semantic restored HH-004's loss, but DA order still trades useful contexts. Zero failures; no adoption.

**DA-061 contiguous bigram postings (2026-08-31).** NO_CONTIGUOUS_BIGRAM_SESSION_SIGNAL. Exact adjacent query phrases cover required sessions 401/465 (.862), below .90, while routing p50 21 sessions/.447 of corpus, above .25. Phrase order narrows DA-060 but is neither reliable nor selective enough for protected substitution. Strongest order stays immutable. Zero calls; no delivery/reader claim.

**DA-062 pack-activated heads (2026-08-31).** NO_PACK_ACTIVATED_HEAD_SIGNAL. Immutable represented episodes route p50 8 session heads/.170 and place present required heads at p50 1/2, but complete coverage is 350/465 (.753), below .90. Posthoc DA-061 union reaches 438/465 but floods p50 .509. Next is descriptive replaceable head streaming, not a late rescue. Zero calls; no traversal/delivery.

**DA-063 replaceable head stream (2026-08-31).** POSTHOC. DA-062 then unseen DA-061 heads reach required sessions 438/465 with one head/frame and zero displacement. Last required head p50 3/p90 14.3; traversal p50 32 members/p90 168. Peak is bounded at 2,048 chars, but cumulative scan remains. Next is exact occurrence coordinates. Zero calls; no reader/delivery.

**DA-064 occurrence coordinates (2026-08-31).** NO_OCCURRENCE_COORDINATE_SIGNAL. Immutable episodes plus exact query-bigram occurrences reach required episodes 382/465 (.822), any 440/465. Complete rows finish at p50 18.5/p90 71; coordinates are efficient when present but miss .90 coverage. Next is fixed-radius local expansion. Zero calls; no reader/delivery.

**DA-065 local occurrence frontier (2026-08-31).** NO_LOCAL_OCCURRENCE_FRONTIER_SIGNAL. Radius-5 expansion lifts episode reachability 382->416/465 (.8946), just below .90; p50/p90 completion 24.5/129. All 72 misses are session-unreachable (35) or lack any lexical anchor in a reached session (37); none are beyond radius. Larger radii close; next use immutable pack episodes as anchors. Zero calls.

**DA-066 dual-anchor frontier (2026-08-31).** DUAL_ANCHOR_LOCAL_FRONTIER_SIGNAL. Pack plus lexical radius-5 anchors raise reachability 416->438/465 (.942), matching DA-063's ceiling; p50/p90 completion 21/78.3. All 35 residual episodes are in unreached sessions; zero miss remains within reached sessions. Next append unigram occurrences after the protected order. Zero calls; no reader/delivery.

**DA-067 hierarchical unigram frontier (2026-08-31).** HIERARCHICAL_UNIGRAM_FRONTIER_SIGNAL. Append-only unigram neighborhoods reach 465/465 with one frame and zero displacement, but median stream is 228 episodes. The 27 gains need p50/p90 62/128 additions and finish p50 158: simultaneous capacity becomes cumulative flooding. Next is query-pair witness intervals. Zero calls; no reader/delivery.

**DA-068 minimum pair witnesses (2026-08-31).** NO_MINIMUM_PAIR_WITNESS_SIGNAL. Deterministic minimum pair intervals retain 465/465 and cut median stream 228->227, but 27 gain cases still need p50 62 additions, exactly tying rather than beating DA-067's `<62` bar; p90 125.4. Pair witnesses do not reduce central work-to-target and close. Next is maximal conjunctive session signatures. Zero calls.

**DA-069 maximal conjunctive signatures (2026-08-31).** NO_MAXIMAL_CONJUNCTIVE_SIGNATURE_SIGNAL. Maximal session sets add 2,335 episodes and recover 8/27 residuals at p50 1 addition, but complete is 446/465 (.959), below .98; median stream 141. Specificity is efficient, but pruning loses 19 needed subset sessions. Next descend explicit signature-lattice edges. Zero calls; no reader/delivery.

**DA-070 signature-lattice descent (2026-08-31).** SIGNATURE_LATTICE_DESCENT_SIGNAL. Hasse BFS reaches 465/465; residual p50 additions fall 62->37 (p90 113.6), passing both bars. Full stream p50 is 228. Posthoc, all 35 DA-066-missing episodes lie at lattice depth 0-3 (median 1); none need d4-7. Depth-3 replay is descriptive only. Zero calls; no reader/delivery.

**DA-071 bounded lattice replay (2026-08-31).** POSTHOC. Outcome-informed depth<=3 preserves 465/465 and residual p50/p90 work 37/113.6, while saving 2,549 entries and reducing median full stream only 228->224. Deep nodes are unnecessary here, but burden remains among shallow siblings. Next separate equal-signature collisions from unique-node branch ambiguity. Zero calls; no transfer/reader claim.

**DA-072 lattice identifiability (2026-08-31).** POSTHOC. Of 31 target sessions, 16 share an exact signature with others and 15 are unique shallow branches; questions split 13/13 plus 1 mixed. Group size p50/p90 2/8; BFS position 7/24. Burden has two mechanisms. Next enrich signatures with exact adjacent query bigrams; branch choice remains separate. Zero calls; no selector/transfer claim.

**DA-073 ordered-feature lattice (2026-08-31).** NO_ORDERED_FEATURE_LATTICE_SIGNAL. Exact unigram+bigram signatures retain 465/465 and reduce target collisions 16->13, but residual p50 work worsens 37->38 (p90 130.4), failing the joint bar; full stream p50 228. Adjacency improves identity, not branch order. Next role-type exact features for source provenance. Zero calls; no reader/delivery.

**DA-074 role-typed feature lattice (2026-08-31).** ROLE_TYPED_FEATURE_LATTICE_SIGNAL. User/assistant provenance retains 465/465, cuts residual p50 work 37->31 (p90 114.6), and target collisions 13->5, passing all bars with zero displacement. Full stream p50 remains 228, so exhaustive traversal is broad. Next audit residual collisions and role-lattice depth. Zero calls; no reader/delivery.

**DA-099/100 indexed codec runtime (2026-09-01).** Exact 1,098-row LoCoMo replay fell from hours to 4.94 min with unchanged SHA. DA-100 p50/p95/max=75.7/216.5/242.1 ms; replay p95=265.8. Equivalence and zero calls pass, but the <=200 ms p95 tier fails. Fusion alone closes; Python suffix-state overhead remains.

**DA-101 flat suffix runtime (2026-09-01).** RUNTIME_SIGNAL. Flat state preserves the exact 1,098-row allocation and cuts first-pass p50/p95/max to 59.9/76.9/85.9 ms; replay max 95.9. Double replay is 153.4 s, zero calls. The <=200 ms runtime tier passes; the <=25 ms median production tier does not. Reader use remains untested.

**DA-098 frozen NF budget replay (2026-09-01).** SIGNAL. Pair16/32=935/1024; protected arch16/32=986/1068. ARCH32 gains 44/loses 0 vs pair32 and is positive in all 6 conversations. It recovers all 57 pair32-only items while preserving 19 arch16-only. 209,257 additions show broad compressed exposure; 30 misses are fit overflow. Reader/fresh untested.

**DA-075 role-lattice anatomy (2026-08-31).** POSTHOC. Provenance splits 11/16 collisions: 26/31 targets are unique, 5 collide; all 15 prior unique stay unique. Target depth p50/p90 1/2, but width grows to 14/22 and BFS position 7->15. Identity improves while branches widen. Next test ordered episode-feature sequences on five residual collisions. Zero calls; no selector/transfer claim.

**DA-076 sequence separability (2026-08-31).** POSTHOC. Exact ordered episode-feature sequences split all 5 residual role-union collisions; every target becomes unique within groups of 2/4/5/6/7. Length alone splits 3; ordered contents are needed for 2. This supplies deterministic carrier identity, not replacement safety, traversal, or delivery. Byte-identical replay; zero calls.

**DA-077 sequence-prefix witness (2026-08-31).** POSTHOC. All 5 residual carriers become unique after 1-2 episodes (p50 1), versus full length 5-6. Exact witness cost is 36-236 chars, p50 135, versus full-sequence p50 594. Prefix provenance is compact enough for branching, but remains metadata and cannot replace evidence. Byte-identical replay; zero calls.

**DA-078 optimal sentinel parse (2026-08-31).** PROTECTED_OPTIMAL_PARSE_SIGNAL. Exact DP re-encoding preserves DA-038 and saves p50 273 chars, admitting 618 append-only members. LongMem complete rises 232->237, +5/0 (p=.0625); all gains resolve prior consumption and all types are nonnegative. Double replay took ~25 min/1.2 GB. Reader/runtime/transfer unvalidated; zero calls.

**DA-079 optimal residual audit (2026-08-31).** POSTHOC. Of 13 misses after DA-078, 9 fit initially then lose fit to earlier immutable admissions; 4 are initially too large, with deficits 23/98/143/1391 chars; 0 fit postpack. Prior-consumption arrival deficits are 28-245. The dominant boundary is lazy materialization/scheduling, not another parse score. Byte-identical replay; zero calls.

**DA-080 protected stream crosswalk (2026-08-31).** COMPLETE. All 13 DA-079 residuals map to one exact DA-045 replaceable node with zero DA-078 mutation. Peak frame p50/p90 is 1968/2040.6 chars, but target work is 13/16 frames and 5781/19264 chars. Offline capacity is structurally available; reader recognition, retention and stopping remain unknown. Byte-identical replay; zero calls.

**DA-081 frame-state anatomy (2026-08-31).** POSTHOC. Of 13 required frames, 7 add role/query features at arrival and 6 are redundant. Earlier state changes are p50 0/p90 1.8, so novelty is locally clean but not universal. Only 1/13 carriers has a sibling in DA-078. Lexical transitions and sibling completion cannot solve stopping alone. Byte-identical replay; zero calls.

**DA-082 unary-edge anatomy (2026-08-31).** POSTHOC. Twelve of 13 residuals are branch-ambiguous, 1 is a present sibling and 0 have a unary represented seed. Each target has one seed; represented branch degree is p50 2/p90 4, and 5 seeds are absent. The sibling overlaps lexical novelty, so union coverage stays 7/13. Payload-only frames omit parent provenance. Byte-identical replay; zero calls.

**DA-083 provenance paths (2026-08-31).** POSTHOC. Seven residual carriers have a directed prompt-root path, 1 is a root and 5 have orphan parents. Linked depth is always 1; child degree p50/p90 1/2. Provenance plus lexical novelty descriptively covers 11/13; the two uncovered rows are redundant orphan-parent cases. Next signal is a transient parent-child bridge. Byte-identical replay; zero calls.

**DA-084 orphan parent bridge (2026-08-31).** POSTHOC. All 5 bridges are partial: parent user and child fit, but every parent assistant overflows at 2215-3304 chars. Peak/cumulative p50 is 284/539 chars with zero DA-078 mutation. Parents add 0 query features, so provenance creates no lexical stop. Next signal is exact chunked parent materialization. Byte-identical replay; zero calls.

**DA-085 chunked parent bridge (2026-08-31).** CHUNKED_PARENT_BRIDGE_SIGNAL. Fixed 1900-char chunks make all 5 orphan bridges complete with zero DA-078 mutation. Each uses 2 chunks/4 frames; peak p50/p90 is 1916/1919.2 chars and cumulative 2804/3984.6. Overflow is solved, but cross-frame retention is not. Next signal is a simultaneous endpoint edge frame. Byte-identical replay; zero calls.

**DA-086 endpoint coframe (2026-08-31).** ENDPOINT_COFRAME_SIGNAL. Five exact parent-user/child coframes fit at p50/p90 549/724 chars with zero DA-078 mutation. Four frames and peak p50 1916 are unchanged; endpoint repeat adds p50 265 chars, cumulative 3072. Endpoints are simultaneous; assistant context stays separate. Next anchors endpoints around each chunk. Byte-identical replay; zero calls.

**DA-087 anchored edge slices (2026-08-31).** ANCHORED_EDGE_SLICE_SIGNAL. All 5 orphan bridges become self-contained edge slices with zero DA-078 mutation. Frames fall to p50/p90 2/3; peak is 1771/1946 chars and cumulative 3362/5474. Repeating endpoints costs p50 +306 chars vs DA-086, but every frame carries parent, context chunk, child and direction together. Byte-identical replay; zero calls.

**DA-088 protected dependency envelope (2026-08-31).** PROTECTED_DEPENDENCY_ENVELOPE_SIGNAL. All 13 residuals get exact envelopes, zero mutation: 7 linked, 1 sibling, 5 slices. Frames p50/p90 1/2.8; peak 555/1908 chars; cumulative 555/4872. Offline capacity/representation closes for this set; reader recognition, retention, stopping/use remain untested. Replay identical; zero calls.

**DA-089 full-frontier stress (2026-08-31).** PARTIAL_FRONTIER_ENVELOPE_SIGNAL. Blind DA-088 transfer completes 4556/8055 (56.6%), with 2701 full-child and 798 anchored overflows; assistants cause 2672/732. Deficit p50 is 488/1454 chars. The 13-item renderer does not generalize; next needs exact component packetization, not route scoring. Zero DA-078 mutation, byte-identical replay, zero calls.

**DA-090 exact packet fallback (2026-08-31).** EXACT_PACKET_FALLBACK_SIGNAL. Fixed 1800-char packets make all 8055 blind frontier targets exact with zero DA-078 mutation and preserve 4556 DA-089 rows. Fallbacks: 2701 child, 798 edge. Frames p50/p90 1/3; peak 1812/1819 chars; cumulative 2033/3537. Full-frontier capacity closes; reader use remains untested. Replay identical; zero calls.

**DA-091 typed edge child stream (2026-08-31).** TYPED_EDGE_CHILD_STREAM_SIGNAL. Control-plane edges replace parent payloads on all 798 eligible DA-090 rows; exact child streams save p50 2220.5 chars, every row saves, peak never rises. Other 7257 rows and DA-078 stay fixed. Dependency representation improves; reader use remains untested. Replay identical; zero calls.

**DA-092 content-addressed nodes (2026-08-31).** NO_CONTENT_ADDRESSED_NODE_REUSE_SIGNAL. The 8055 frontier references contain 7659 exact nodes: 396 reuse (4.92%), below 10%. Shared storage saves 788890/12593382 chars (6.26%); median/p90 reuse are one. Exact collision-free identity is viable, but dedup is too sparse for capacity. DA-091 exposure is unchanged; replay identical; zero calls.

**DA-093 prompt-relative child stream (2026-08-31).** PROMPT_RELATIVE_CHILD_CAPACITY_SIGNAL. All 3499 linked child streams use exact pointers into immutable DA-078 history; cumulative savings p10/p50/p90 are 13.73/22.50/35.05%. Median exposure is 2 frames/1895 chars. Other 4556 rows and DA-078 stay fixed; exact decode and replay pass. Reader decoding/use remain untested; zero calls.

**DA-094 prompt dependency topology (2026-08-31).** FRAGMENTED_PROMPT_DEPENDENCY_TOPOLOGY. DA-093 children use p50 123 pointers across 24 prior members; the largest supplies only 23.43% of referenced chars. P90 is 162 pointers/29 members; median distance 23. DA-093 is strong compression, not a sparse dependency graph. Exact accounting/replay pass; zero calls. Next: exact node-local encoding.

**DA-095 node-local child stream (2026-08-31).** NODE_LOCAL_CHILD_CAPACITY_SIGNAL. All 3499 children stay smaller than literal while referencing one prompt node. Savings p10/p50/p90 are 2.50/6.36/14.83%; p50 retains 27.87% of DA-093's gain. Pointer count falls 123->25 median. This is a sparse dependency edge with exact decode and protected controls; reader use untested. Replay passes; zero calls.

**DA-096 bound-node span stream (2026-08-31).** NO_BOUND_NODE_SPAN_CAPACITY_SIGNAL. One header plus local spans improves 3458/3499 rows; incremental savings vs DA-095 are p10/p50/p90 .44/.956/2.13%, missing the 1% median bar. Absolute savings vs literal reach 3.09/7.30/16.54%. Exact one-source decode and replay pass. Rendered binding overhead closes; next is control-plane binding. Zero calls.

**DA-019 protected boundary substitution (2026-08-30).** STOPPED_AT_PF4 unopened. The blind rule executes 571 NF and 188 LongMem swaps, with fit/lexical/semantic rejections 8,631/359/6,786, but zero required duplicate rejections because parent edges are already deduped. No evidence outcomes opened. A successor must test duplicates synthetically; no in-study repair.

**DA-020 boundary substitution continuation (2026-08-30).** NO_PROTECTED_BOUNDARY_SUBSTITUTION_SIGNAL. One guarded final-payload swap changes NF 970->966 (0/4) and LongMem 188->188 (2/2). Replacements are smaller and more query-similar, yet remove answer evidence. Unique query-token preservation plus cosine dominance is not a protection invariant. Keep strongest orders immutable; no tuning/reader/adoption.

**DA-021 immutable-pack dictionary (2026-08-30).** STOP unopened; cross-corpus mechanical bar fails. Joint exact coding preserves every baseline payload and recovers median 480.5 chars on NF (1,544 pairs +1,038 turns) but only 32 on already phrase-coded LongMem (2+104), below 64. Zero expansion/calls. Frozen NF-only continuation is eligible; LongMem needs a different representation.

**DA-022 NF immutable-pack continuation (2026-08-30).** NO_NF_IMMUTABLE_PACK_CAPACITY_SIGNAL. Joint coding raises 970->973, 3/0, p=.25, below +5. Median +480.5 chars admits 2,582 actions, but only 6 carry missing evidence. Zero losses are structural; one-hop gap remains 13. Phrase capacity is no longer the main NF bottleneck. No reader/tuning/adoption.

**DA-023 backward span references (2026-08-30).** BACKREFERENCE_DELIVERY_SIGNAL. Immutable exact references raise NF 970->976 (+6/0,p=.03125) and LongMem 188->202 (+14/0,p=.000122); all groups nonnegative. Median slack +1,028.5/+546 chars. Arbitrary prior spans beat declared phrases without displacement. Ceilings 986/250; reader/runtime unvalidated, no adoption.

**DA-024 backreference residual audit (2026-08-30).** NF residual 10: prior consumption 7, wrong member 2, conjunction 1; prior consumption dominates. LongMem residual 48: wrong member 20, prior consumption 17, initial size 6, conjunction 5; mixed. No unaccounted or shared successor. Next: LongMem additive atomic fallback; NF whole-additive-pack allocation. Evidence-aware audit only.

**DA-008 reversible direct rendering (2026-08-30).** RANKED_COMPACT_SIGNAL, spent availability. Exact speaker dictionaries save median 504 chars with direct fixed at 935. Benefit links reach 961 (+26/0; all 6 positive) vs coverage/temporal 956. Model contrasts p=.227/.332, not differentiated. One-hop oracle 986. No reader/adoption.

**DA-009 role-pattern compression (2026-08-30).** INCREMENTAL_COMPACT_SIGNAL, spent availability. Exact modal speaker-order encoding saves another median 147 chars and raises frozen benefit links 961->966 (+31/0 vs direct); all conversations nondecrease. Incremental 7/2, p=.180. Oracle 986; 20 gains remain. No reader/adoption.

**DA-010 link payloads (2026-08-30).** COMPACT_PAYLOAD_SIGNAL, spent availability. Full/best-turn/atomic/fallback complete 966/962/970/970. Atomic and overflow-only fallback add 4/0 (p=.125), +35/0 vs direct; global best-turn loses 10 to full. Atomic and fallback complete sets match. Oracle 986 leaves 16. No reader/adoption.

**DA-011 residual blockers (2026-08-30).** PRIOR_CONSUMPTION_DOMINATES, spent audit. Of 16 reachable fallback misses, 13 are prior-consumption and 3 multi-pair conjunction; none are wrong-member/base-capacity. Initial/arrival/required chars p50 623/45/192; carrier rank p50 7. Oracle member +0; carrier-first +16/0, p=3.05e-5. Nondeployable.

**DA-012 carrier ranking (2026-08-30).** NO_CARRIER_RANK_SIGNAL. Grouped carrier AUC .765, all 6 .660-.929, but carrier/benefit both complete 970 with 3/3 trades (p=1); conv-50 regresses. Coverage gives 966. Carrier rank p50 stays 2, p90 11.5->10.5. Stable pooled prediction does not improve within-question allocation. No tuning/adoption.

**NF-005 information dilution (2026-08-13).** SUPPORTED; CHARACTERIZED. Same 465 LongMemEval items/32k/turn packing: own-turn rank raises any exact evidence 361->461, 100 gains/0 losses, p=7.89e-31; all 208->454. Evidence turns p50 298 chars vs parent episodes 2,550. Supports localization/dilution moderator, not raw-length causality or reader value.

**NF-006 internal statement ranking (2026-08-13).** INTERNAL_DILUTION_RESCUES_Q11; CHARACTERIZED. At 32k, episode/inherited-statement/own-statement availability is 12/7/14 of 17. T1 restores monetary 4/4; targeted ties 21/21 with 0 losses. No T1 statement is from turn 90: store-level dilution is supported, but DX-001's exact carrier remains unresolved. No live/adoption.

**NF-007 hard cluster floor (2026-08-13).** STOP; FLOOR_INERT. T1 touches 16/16 clusters, but selects 30/91 from civil-heavy cluster 0 versus 9/168 across five art-majority clusters. Floor=1 forces 0 admissions. Candidate scarcity and region entry are eliminated; similarity under-samples broadly uncued art. The carried coverage-count family is closed on this store.

**NF-008 live reader validation (2026-08-13).** DESIGN ONLY; NOT REGISTERED OR RUNNABLE. Proposed comparison: frozen NF-006 C0 12/17 vs T1 14/17 using 17 item-level fact-use counts and >=5 replicates/arm. Reader, exact prompt, schedule, scorer, targeted scope, statistic and bars remain open. No implementation or inference authorized.

**TC-001 tiered vs flat (2026-08-22).** D3 FLAT_WINS, REGISTERED-OFFLINE. Identical candidates/vectors/renderer/packer, 16k, 868 LoCoMo dev questions: complete evidence 749 flat vs 314 tiered, 8 gains/443 losses, p=6.98e-120 vs band 4; 32k narrows to -177. Recency takes 32/32 and 61% of chars; coverage carries evidence on 8/871. K filters by cosine, delivers in store order. Availability only.

**TC-001B dual arm (2026-08-22).** Escalated from TC-001 Amendment 001. C1 D3 FLAT_WINS: A_DUAL (recency_window_n=0) 472/868 vs flat 749, net -277, p=8.23e-69. C2: recency cost 158. C4: ranking the K tier is worth 276, so TC-001's -435 = 158+276. C3 (ranked 748 vs 749) carries no bar - PF4 found 3 discordant pairs pre-lock, predicted 3, observed 3. Characterization only.

**TC-002 fill-order transfer (2026-08-22).** C1 D1 K_FIRST_WINS, REGISTERED-OFFLINE. EC-002's K-first replayed unmodified on LoCoMo dev at its own 32k/any endpoint: 732 vs 687 of 871, +45, p=1.64e-5 vs band 7. Still 110 behind flat; ranking the K tier is worth 111 and its 118 gains are C2's 118 losses exactly, disjoint from C1's 80. Band 7 at 32k, 4 at 16k. Does not ship.

**TC-003 reserved floors (2026-08-22).** C1 D1 FLOORS_WINS but C5 D3 RANKED_WINS; REGISTERED-OFFLINE. At 16k complete evidence floors/N-first/K-first/flat = 656/314/461/749; dual floors/dual/ranked = 718/472/748. C1 +342 is contested on 351/357 gains, so contest key—not reservation—carries it. I1 service order 871/871; I2 ownership 0/871 shipped. No ship.

**TC-004 candidate granularity (2026-08-23).** NO_PREDICTIVE_SIGNAL; REGISTERED-OFFLINE. At 16k, embedding-localization vs length AP is 21/31/1 over 53 positive-label questions, p=.937; mean .102/.054 but median .0145/.0213. There are 96 beneficial vs 235 harmful splits. A 1% rate gives +3 descriptively; full split 749->687. 2,661 embedding calls, zero LLM calls. No ship.

**TC-005 relevance efficiency (2026-08-23).** Hybrid CARRIES_SIGNAL, not WORKS: targeted complete dense->hybrid 593->624 at 8k (+31; 58/27, p=.000508) but 643->657 at 16k (+14; 36/22, p=.0435). Full eligible +6/-6 at 16k/32k. BM25 -36/-62. Frozen TC-007 fallback is dense. Zero run calls/misses; availability only.

**TC-007 protected spread (2026-08-23).** NO_SPLIT_SELECTED; REGISTERED-OFFLINE. A3 vs dense complete at 16k/32k: combined 739/812 vs 749/810, breadth 13/27 vs 16/27, targeted 637/681 vs 643/680; MIXED. Facility loses 57/36 combined and 7 breadth at both budgets; CONTROL_WORKS. A3 adds/loses 5/14 evidence ids at 16k, 7/3 at 32k. Dense fallback; availability only.

**TC-008 session-gated spread (2026-08-23).** DENSE_CARRIES_SIGNAL; REGISTERED-OFFLINE. Session vs dense complete at 16k: combined 728/749, breadth 13/16, targeted 629/643; at 32k all tie. Breadth identities add/lose 1/5 at 16k, 0/1 at 32k. It reaches 30 sessions but loses evidence; 15/27 discordances are worse than A3 due grouping. Dense fallback; no answers.

**TC-009 dynamic session penalty (2026-08-23).** DENSE_WORKS; REGISTERED-OFFLINE. Dynamic vs dense complete at 16k: combined 713/749, breadth 12/16, targeted 624/643; at 32k 794/810, 21/27, 674/680. No breadth-complete gains. The penalty uniquely loses 34/22 evidence ids at 16k/32k. Count-based session exposure closes; dense fallback; no answers.

**TC-009 safe-substitution probe (2026-08-23).** NO_POSITIVE_SIGNAL. At 32k, 7 identity gains/23 losses/838 ties; complete 4/20. None of 15 blind features passes. Best margin AUC=.708 but reverses to .30 on conv-41 and finds 1 gain in top 20. Novelty/redundancy AUC=.47-.54. No selector, threshold, reader or TC-010 authorized.

**TC-009 syntactic spans (2026-08-23).** NO_POSITIVE_SIGNAL. At 32k, dense/noun/subject complete = 810/443/659; breadth 27/10/13; targeted 680/391/580. Both regress all 4 conversations. Lost evidence has dense-rank median 5/14. Parser extraction works, but max span cosine is unsafe. 10,320 embedding texts, 0 LLM calls; no TC-010.

**TC-009 dependency graphs (2026-08-23).** NO_POSITIVE_SIGNAL. At 32k dense/lexical/dep-PR/subject/subject-PPR complete = 810/727/677/316/344; breadth 27/15/10/3/3. Every arm loses in all 4 conversations; dep-PR loses 50 to lexical. Subject arms tie 261-295 candidates at zero. 204,409 PPR runs, 0 embedding/LLM calls; no TC-010.

**TC-009 convex fusion (2026-08-23).** NO_POSITIVE_SIGNAL; semantic-arm signal. Dense/RRF/80:20 combined is 749/755/771 at 16k and 810/804/819 at 32k; targeted 643/657/666 and 680/682/689. All 4 conversations gain, but 32k breadth falls 27->24 (1 gain/4 losses), all enumeration. Score fusion beats RRF but does not replace protected breadth; no TC-010.

**TC-009 convex+A3 (2026-08-23).** NO_POSITIVE_SIGNAL; budget-dependent. At 32k CC80+A3 gives combined/targeted/breadth 818/686/27 vs dense 810/680/27 and CC80 819/689/24, repairing all 4 prior breadth losses. At 16k it gives 757/653/14 vs dense 749/643/16 and CC80 771/666/17. Components are compatible; fixed 50/50 does not transfer. No share tuning/TC-010.

**TC-009 convex+A3 miss audit (2026-08-23).** POSTHOC. Misses are 111 at 16k, 50 at 32k; 61 are rescued and none regress. CC80 associates with 17/20 and 6/9 gains over dense. At 32k targeted misses are 18/18 zero-evidence; 31/32 non-targeted misses are partial. Multi-session misses 26/126 vs single-carrier 18/704. Tail lookup plus set completion remain; no architecture claim.

**TC-010 qualified bottom spread (2026-08-23).** NO_SPLIT_SELECTED. CC80/qualified/global complete = 771/752/706 at 16k and 819/818/771 at 32k; breadth 17/13/8 and 24/24/17. At 16k diversity displaces evidence; at 32k sets are identical on 765/871 because the top-quarter pool already fits. Global bottom is harmful. CC80 fallback; no tuning/reader.

**TC-011 four spread objectives (2026-08-24).** NO_CANDIDATE. At 16k/32k combined: CC80 771/819, logdet 726/797, aspect 749/810, anchored chain 717/780, pure chain 717/778. Aspect is least harmful but breadth 15/23 vs 17/24. Both chains regress sharply. Four exact 50/50 routes close; CC80 fallback, no answers/tuning.

**TC-012 dynamic ASPECT (2026-08-24).** NO_DYNAMIC_PROMPT_SIGNAL. CC80/static/dynamic combined = 771/749/720 at 16k and 819/810/787 at 32k; breadth 17/15/8 and 24/23/20. Growing-context recomparison amplifies drift. Residual arm 753/810 is BINDER_LIMITED: only 146/71 sets differ from static. CC80 fallback; no tuning/answers.

**TC-013 CC80-parent ASPECT fan-out (2026-08-25).** CHARACTERIZED; BUDGET_SPECIFIC_SIGNAL. Each half-budget CC80 admission gets one singleton-seeded ASPECT child attempt. Fanout/CC80 complete = 763/771 at 16k and 821/819 at 32k; breadth 16/17 and 26/24; targeted 654/666 and 689/689. 32k gains breadth while tying targeted, but 16k regresses. CC80 fallback; no answers/tuning.

**TC-014 traversal ablation (2026-08-25).** CHARACTERIZED. Vs TC-013, opportunity HELPS at 16k (+7 combined/targeted,+3 breadth) but loses 1 breadth at 32k despite +5 combined. Utility-order HELPS only at 32k (+1 combined/breadth, 0 losses). Parent binding, global matching and T234 are NO_HELP. Descriptive opportunity total is 826 at 32k vs CC80 819. No answers/adoption.

**LV-002/003 TC-014 reader instruments (2026-08-26).** STOPPED. LV-002 exposed raw thinking, then lost a truncated unpersisted batch. Closed-think prompts passed with floor 0/16. LV-003 persisted all 170 answers but stopped on 2 balanced 512-token truncations. No outcome was opened; LV-004 alone owns the repair and verdict.

**LV-004 TC-014 live reader (2026-08-26).** REGRESSES. On 16 offline-discordant items, opportunity/full CC80 both score 5: 1 targeted gain, 1 breadth loss, net 0; breadth guardrail fires. Two LV-003 truncations were prefix-identically completed; 170 answers and 480 blind judgments pass. Selected LoCoMo dev only; no adoption/tuning.

**LV-005/006 context organization (2026-08-26).** WEAK_SIGNAL. Same frozen opportunity evidence: flat/grouped/chrono/guided score 5/6/6/6 on 16 selected items. Guided vs flat has 1 breadth gain, 0 losses; guidance vs chrono ties, so only the bundle carries signal. Median block grows 31,983->42,542 chars. No adoption/transfer.

**LV-007 compact communities (2026-08-26).** STOP before judging. Fixed evidence stayed exact; median block fell 42,542->32,973 chars. One COMMUNITY answer among 255 hit the locked 2,048-token cap, so G-COMPLETE failed. No blind surface, scoring or result. A common-cap continuation requires new Part 1 and registration.

**LV-008 Qwen3.8 compact communities (2026-08-26).** REGISTERED STOP; POSTSTOP DESCRIPTIVE. One of 255 answers hit 4,096 but was judged correct 3/3. Pairwise/community/question-both = 4/5/8 of 16; full gains 4, loses 0 (breadth +3, targeted +1). Seven capped judge calls cause 0 majority flips when forced wrong. Promising signal; no adoption claim.

**LV-009 full-LoCoMO renderer validation (2026-08-27).** PAIRWISE_RETAINED. On 1,540 primary QAs, pairwise/community/QB/QEACH = 907/876/914/920. QB vs pairwise net +7 (82/75), transfer -1; QEACH vs QB +6 (44/38). Neither co-primary clears practical or statistical bars. Question repetition recovers community loss but does not beat control. Internal Qwen3.8 result only; no port.

**BEAM-001 parent-opportunity ASPECT (2026-08-28).** CHARACTERIZED; diagnostic NO_DEMONSTRATED_GAIN. On 360 balanced questions/90 conversations, T1-C0=.00518 (95% CI -.01757,.02765; p=.658); T1-A0=-.00698 (lower -.02293), failing non-inferiority. Three runtime/judge deviations; all 1,080 answers and 360 judgments sealed. No confirmatory claim.

**PS-001 pattern-separated engram formation (2026-08-11).** CHARACTERIZED. Nine deterministic sparse cells on 119 episodes; only D=4096,K=41 passed G3-G5: 119/119 fixed points and exact 1/10/30/50% swap recovery. Six of seven degenerates reached stored codes; the union-biased cue cycled. Code-space result only; no natural cue, retrieval, live run, promotion, or adoption.

**PS-002 natural-language cue binding (2026-08-11).** STOP AT PART 1; NATURAL_CUES_NOT_BOUND, CHARACTERIZED. Nine label-blind cells ran 24 sealed queries x8 rounds. Best M=4,tau=.025 reached stored codes 190/192 but one cue cycled and one reached a spurious fixed point; no cell emitted 8 clean ids/query. Labels, PF1-PF10, answers, live run, promotion and adoption not entered.

**PS-003 ambiguous cue resolution (2026-08-11).** G3 FAIL; LOOKUP_BINDING_INSUFFICIENT, CHARACTERIZED. Five-probe/four-swap consensus emits 8 safe ids for all 24 queries after rejecting 3 cyclic, 1 spurious and 1 disagreeing family. Lookup stays 7/12 vs cosine and PS-002; monetary 1/3. G4/G5, stress, answers, live run, promotion and adoption not reached.

**CC-002 library extraction (2026-08-01).** The deployable component now lives in the installable `episodic` package; the harness imports it. T1-T7 pass: clean-venv import, leakage grep + import-graph, byte-identical reproduction of 132 committed A3 payloads and 3 rendered blocks, call-shape sentinel fails loudly, 804 tests green, two-process purity. H1/H2 ship as config-pinned gates, not docs.

**DX-002 context growth (2026-08-02).** BRANCH B. LTM saturates ~52-54k from turn 500 (H-A confirmed); retrieved_stm never does: p95 +23,238 L / +28,701 S over the last five buckets, still setting records at turn 1,000. Rule pinning added 0 but was disabled, not cleared. Blocks CC-003. A slope-CI-only rule first said Branch A; the interval measured power, not flatness.

**CC-003/004/005 closeout (2026-08-02).** CLOSED. G-E0 clears DX-002's block: episodic's block is bounded, +18 chars p95/1,000 turns, so the leak is the runner's. The ceiling no longer raises at tiny budgets; truncated carries dropped ids; drop order named (amendment 001); E6 inert at 132/132 SHAs. CC-004 kills real processes. CC-005: 190 ms at 1,000 candidates, no eviction. Suite 1,007.

**CC-006 vector cache (2026-08-05).** PASS. Exact solo-call float32 vectors are persisted and bound by file plus canonical text-to-vector SHA-256; read-only misses fail. C1-C9 pass. EC-002 adopts 96,585 entries with 0 model calls. Protection begins with retained caches; EC-001 remains permanently non-bit-replayable. Suite 1,028.

**CC-007 episodic-chat adoption (2026-08-24).** PASS. Distribution renamed; public read path is additive last-32 continuity plus 32k CC80. Static ASPECT ships optional/off with tested 50/50 protection and slack return. Package port reproduced 4,355/4,355 frozen order/selection/payload groups exactly. No reader, transfer or latency claim.

**LV-001 (2026-08-02).** RUN. B1 WEAK, B2 FAIL, **promotion killed on its own pre-registered bar**. The 6-item offline availability gap became +1 correctly attributed item live; targeted fell 3.5->1.5 against a 0.5 tolerance. A3 dropped turns 1-2 and could not state the formatting rules; offline it preserved 16/16. Availability is not the answer. Both arms fabricated the unretrieved art domain.

**EC-001 LongMemEval (2026-08-03).** COMPLETE, Codex-substituted only. On 470 answerable items, top-4 held no evidence for 14.7%; exact-turn availability was 16.8%. Tier 2: 28/140 raw, 12.22% post-stratified; gap -2.54 pp. Multi-session and temporal 0/20; abstention 17/20 despite 0 component signals. Not an official benchmark score.

**EC-002 K-first packing (2026-08-05).** COMPLETE offline. Same-store K-first raises any-session recall 109/470->261/470: 152 gains, 0 losses. Exact-turn-any 79->196: 119 gains, 2 losses. K deliveries 26->476; all blocks still truncated. Confirms recency-first budget exhaustion as a causal gate. No production/Tier 2 promotion authorized.

**IC-001 internal packing (2026-08-06).** BRANCH A. K-first replay from frozen candidate identities; 0 model calls. B0 reproduces the deployed 6/17 at 31,946 chars exactly. Under the deployed order K delivered 0 episodes at 8/8 probes; K-first gives 9. Q11 6/17->7/17, targeted 14/21->18/21, zero losses. No CC-006 cache here; Amendment 001 authorized, enforced as a gate.

**011 - Tier isolation.** RUN; B1 FAILS. Four live 121-turn arms behind the first binding pre-test (G1-G7, T=6/13). Deployed arm 8.0 = STM-only 8.0 on all 13 questions: the LTM tier is inert as shipped. K-first delivers 13 K episodes vs 1, raises Q11 to 10/17 and targeted to 10/21, scores 7.0. Not adopted. Same prompt, same seed, different answer: -1.0 sits in unmeasured noise.

**N-tier mislabel (2026-08-08).** The tier the arc calls a recency window is a least-recently-delivered rotation over the whole store; replay matches the live ranking 120/120 turns per arm. Overlap with a real window 0.29, 36% of deliveries older than the cap, reaches all 120 episodes. Three rules carry the name; the only real window is in `episodic`, which no scored live study ran. B1 unchanged.

**Carried N rule was a locked prefix (2026-08-08).** Every live run through Study 010 ranked freshest-delivery-first and refreshed what it delivered, so the block re-selected itself: from turn 11 it held source turns 1-9 plus turn t-1, for 111 turns in Study 009 and 999 in Study 010. Replay exact on 17 runs, 12 lock. Overlap with a real window 0.205. Read the key AND what touches it.

**Instrument band is 3.0 (2026-08-09).** Amendment 001 run. Five arm-D replicates, identical everything: four score 8.0, one 11.0. Not a spread but a switch - four are byte-identical across 121 turns; the one meeting an empty server slot diverges at turn 1. Study 009's 3.0, LV-001's -2.0 and 011's -1.0 are NOT DEMONSTRATED. Offline counts untouched. B1 stays fired.

**PAPER-001 (2026-08-07).** DRAFT, revised through Study 011. The pool/objective/floor decomposition stands, but Â§5's 6/17 is packing-conditioned: new Â§5.2.2 records that the internal K path delivered nothing at 8/8 probes. Naturalistic ranking lacks the dominant internal inversion. Corpus-artifact cause unresolved. Source is `paper/PAPER_001.md`; figures/PDF are generated.

**Retrieval mechanism ledger (2026-08-03).** CLOSED. E002 KILL but exact-32k segmentation improved 6/17->10/17. AR-001 proves exact 14/17 costs 5,058 chars. E001 best-found .1204->.2103; 0/714 reached K=.48. F2 closed. EC-001 measures F3 externally: 0/500 component absence signals, but reader abstention 17/20. E003 unauthorized.

## 3. Failure Pattern

The recurring failure class is a surrogate that can pass without the property it claims to certify: record count for information, novelty for importance, density for factual value, or a rubric score for a correct answer.

Before implementing any gate or criterion, ask whether it can pass while the certified property is false. Flag that possibility before writing code.

## 4. Standing Rules

### Pre-registration

- Commit the design before implementation; its SHA is the integrity anchor.
- Pre-registration commits contain no implementation files.
- Never edit a locked pre-registration. Record changes in standalone amendments.
- Parameters live in one authoritative place: the pre-registration.

### Preflight — required in every spec, before any run

**No spec is complete without a Preflight section, and no run begins before
Preflight passes.** Studies, analyses, counterfactuals, diagnostics, engineering
specs and benchmark adoptions alike. A spec without Preflight is returned, not
run. Full wording and the failing precedent behind each check: `PREFLIGHT.md`.

Two parts, in order.

**Part 1 — Exploration.** Characterize the mechanism empirically before designing
a test of it. Not by reading the code, not by trusting its name, not by citing a
prior study. Run it and record what it does; findings may change the design
before anything is locked. Minimum, for any spec touching an existing component:
behavioral identity in one falsifiable sentence; a name-to-behavior check on
every named component, block, tier and variable; the distribution rather than a
summary; and degenerate or absorbing states demonstrated on a real trace.

**Part 2 — Checklist.** Every item answered explicitly. *"Assumed" is not an
answer; "verified at `<SHA>`" is.*

| # | Check |
|---|---|
| **PF1** | Inputs exist — present, readable, hash-identified, counted |
| **PF2** | Mechanism identity verified against its name and description, on committed data |
| **PF3** | Gate ordering enforced, not assumed — proven to execute before what it gates |
| **PF4** | Thresholds achievable — every bar and kill condition checked reachable before locking |
| **PF5** | Comparison keys stable — content hashes, never generated ids, timestamps or paths |
| **PF6** | Reproduction anchor — a replay reproduces a known result by identity and digest, not by count |
| **PF7** | Absorbing-state proof for any mechanism with feedback, on a real trace of the intended length |
| **PF8** | Ablation length adequate — state what it can and cannot detect |
| **PF9** | Surrogate audit — can this pass while the property it certifies is false? Record residuals |
| **PF10** | Live-evaluation requirement stated — availability is not a verdict |

**Ticked boxes are not Preflight.** Each check names the artifact or the executed
test that answers it.

### Gates and ablation

- Offline gates are binding and run before full inference.
- A gate is trusted to stop only after showing that its tested population and
  its non-stopping alternative were capable of existing. Record population
  counts and a positive control before interpreting a stopping branch; an empty
  join, vocabulary mismatch, or inert treatment is an instrument failure, not
  a mechanism result.
- Before artifact lock, mechanically verify that every rubric-required fact is planted in a scripted user turn strictly before its probe. Any unavailable fact blocks lock and inference.
- Run at least a 35-turn ablation before a 120-turn run.
- Commit calibrated settings before the ablation.
- Replay harnesses must reproduce a known result exactly before producing evidence.
- Revalidate every carried subsystem at the study's maximum planned scale. A pass at 120 turns does not make infrastructure settled at 1,000 or 10,000 turns.

### Runtime and determinism

- Use a fixed seed, `--parallel 1`, and no speculative decoding.
- Saturate available hardware for CPU-bound offline exploration, replay,
  preprocessing, sealing and scoring whenever deterministic independent shards
  exist. Measure worker count and aggregate utilization early; do not leave a
  long study job on one core by default. Registered serial inference and gate
  ordering still govern. When they prevent full utilization, record the exact
  constraint and use the maximum safe concurrency it permits.
- Record the launch command and server build hash in every run header.
- Require a byte-identical seeded prefix rerun.
- Assert the script SHA after decoding and use explicit UTF-8 encoding.

### Controls

- Run controls from checked-out prior code in a separate worktree, never by disabling features in the current runner.
- Reject dirty worktrees, unexpected diffs, wrong script hashes, import escapes, or current-study engine leakage.
- Record module paths, server properties, command, and PID before inference.

### Leakage

- Retrieval, formation, ranking, and gating code must not read or depend on `q_facts_key.md` or rubric artifacts.
- Measurement may use the plant key; mechanism may not.
- Enforce the boundary with grep, import-graph checks, and a planted test violation.

### Scoring

Full rules are in `experiments/audits/scoring_integrity/PROTOCOL_scoring_integrity.md`.

- Only content outside reasoning blocks is scoreable. No final answer is `NO_ANSWER` and scores 0.
- Commit completeness and fact-presence checks before accepting scores.
- Every score needs a rationale; conflicts block the commit.
- Calibrate AI raters on a planted `NO_ANSWER`, then use three blind passes and registered human-adjudication triggers.
- Commit every arm's scores before anyone opens mechanism logs; git order is the evidence.
- Keep rubrics byte-identical. Resolve ambiguities from criterion text before reading affected answers.

### Scope

- Add one new component per study.
- Stop if implementation would alter a carried subsystem.
- Diff-review carried subsystems to prove they are unchanged.

## 5. Amendments

Amendments are permitted for genuine blockers. Add a standalone file at `experiments/study_NNN/amendments/AMENDMENT_NNN_short_name.md`; never edit the locked pre-registration. Include the trigger and evidence, change, rationale, exclusions, and author authorization.

Legitimate amendments correct measurement units, repair protocol contradictions, and do not make a criterion easier after results are known. Adding a factor, policy level, or budget is a new study and must be escalated.

## 6. Workflow

- Use one branch per study: `study/NNN-short-name`.
- Work sprint by sprint and commit at task granularity.
- Preserve commit order for gates, ablations, scoring, and mechanism analysis.
- Close every study with its own pull request.

The PR body must state the outcome, bars, findings, amendments, artifact links, and checklist status.

### Blocking Study Close Checklist

1. Commit the report with the pre-registration SHA in its header.
2. Update the root `README.md` (see *README structure* below).
3. Add or update the root `AGENTS.md` digest entry, keeping it at most 400 characters.
4. Update `ERRATA.md` when any published number changes.
5. Update memory files.
6. Commit all run logs, gate reports, and scoring artifacts.
7. Open the study PR.

Items 2 and 3 are mandatory. A study is not closed and its PR must not merge without them.

### README Structure

The root `README.md` has two halves and they have different readers. Everything
above the `# For LLM Context` divider is written for a person deciding whether
this work is worth their time; everything below it is written for an agent
picking the work up with no prior context.

**Above the divider — keep it short.** Paper link, executive summary, how it
works, current state of work, next steps. Closing a study means:

- Leave *How It Works* alone unless the deployed read path actually changed. It
  is the mermaid graph of the shipped architecture in plain language, and it is
  the only place a newcomer learns what the system does before meeting a result.
  Node labels carry no identifiers by deliberate choice; the field names, values
  and provenance live below the divider under *Deployed Settings*. If a study
  changes a setting, the graph stays and the table moves.

- Update *Current State of Work* — its date, its arc table row, its constraints.
  Replace what is stale rather than appending to it. This section describes the
  present, not the history.
- Rewrite *Next Steps* so the top item is what a reader should do next. A step
  that has been taken is deleted, not marked done.
- Touch the *Executive Summary* only when a finding changes what the program
  claims. It is four findings and a stated limit; it does not grow by one
  paragraph per study.

**Below the divider — this is where detail belongs.** Add the study's status
blockquote to the ledger and its row to *What Has Been Tested*, with numbers
and artifact paths. Density is correct here. If a result needs more than a
blockquote, give it a section, as the arcs have.

Never resolve a length problem by moving detail above the divider or by
compressing a status blockquote until its numbers are gone. The two halves fail
in opposite directions: the top becomes unreadable, the bottom becomes
unciteable.

## 7. Never

- Let implementation precede pre-registration.
- Edit locked registrations, committed scores, or run artifacts.
- Add a second new component.
- Change criteria after observing results.
- Score an answerless item above zero.
- Expose rubric artifacts to mechanism code.
- Run unseeded or use a flag-disabled control.
- Run any spec without a passing Preflight (§4, `PREFLIGHT.md`).
- start a 120-turn run without a passing 35-turn ablation.
- Reopen a stopped study or bypass a binding gate without a new, authorized design.
- Report a result that cannot be traced to a committed artifact.
- Introduce a lower disposition bar, or a "this carries signal" reading, after a number is on the table. Both tiers are registered before the run or neither exists (§9).
- Report `STOPPED` without saying whether the mechanism failed or the instrument could not test it (§9).

## 8. Repository Map

```text
README.md                                      current front door
AGENTS.md                                      this operating manual
ERRATA.md                                      corrections to published results
PREFLIGHT.md                                   mandatory preflight; §4 carries the mandate
experiments/audits/scoring_integrity/          scoring protocol and 2026 audit
experiments/study_NNN/
  pre_registration.md                          locked design and SHA anchor
  study_NNN_sprint_plan.md                     execution plan
  amendments/                                  authorized standalone changes
  decisions/                                   authorized decisions
  q_facts_key.md                               measurement only
  runs/                                        logs and analyses
  study_NNN_report.md                          result and limitations
experiments/probes/                            exploratory work outside the arc
experiments/internal/packing_priority/         IC-001 packing-order counterfactual on the internal corpus
experiments/comparisons/hh_001/
  HH_001_DEVELOPMENT_PLAN.md                   head-to-head against Mem0, local substrate; PLAN ONLY, not built
  HH_001_PRE_REGISTRATION.md                   its confirmatory stage; DRAFT, NOT LOCKED, blocked on the above
paper/
  PAPER_002.md                                 terminal research document; the source of truth
  PAPER_001.md                                 RETIRED 2026-08-18; superseded by PAPER_002.md
  Rank_Fine_Pack_Fine_Call_Nothing.pdf         typeset build of the above; generated, never authored
  notes/EVIDENCE_SPINE.md                      every admissible number, with artifact and standing
  notes/DO_NOT_WRITE.md                        withdrawn claims; never restate one
  notes/COMPETITIVE_LANDSCAPE.md               published competitor results; none were run here
  CLAIM_TO_ARTIFACT.md                         every claim with its committed artifact and hash
  REPRODUCTION.md                              Appendix E; clean-environment check of one headline number
  reproduce_headline.py                        that check; reader-facing, runs against the installed library
  figures/                                     generated SVG/PNG plus figure_manifest.json
  notes/EVIDENCE_INDEX.md                      spec-versus-artifact reconciliation
  reviews/                                     two adversarial cycles, slop audit, three-reader review
experiments/components/live_validation/
  LV_001_pre_registration.md                   live validation of the shipping selector; PRE-REGISTERED, NOT RUN
experiments/components/biological_memory/deterministic_retrieval/
  DMR_ARC_IMPLEMENTATION_ROADMAP.md            design-only six-stage deterministic retrieval arc
scripts/generate_paper_002_figures.py          rebuilds paper/figures/ from committed artifacts
scripts/check_paper_002_claims.py              gates every number against the spine and landscape
scripts/build_paper_pdf.py                     rebuilds the PDF from PAPER_002.md; needs `pip install typst`
```

### The paper is generated, not authored

`paper/PAPER_002.md` is the only place a claim in the paper may be edited. The
figures and the PDF are build outputs of the two scripts above.

- Edit `PAPER_002.md`, then re-run **both** scripts, then `check_paper_002_claims.py`.
  Hand-editing a figure, the
  PDF, or `paper/build/` is a defect, not a shortcut.
- Figure numbering lives in the Markdown, not in the typesetter, so a renumber
  means editing the Markdown and the generator together. The build places each
  figure at the paragraph that first cites it; if citation order and figure
  order disagree, fix the numbering rather than the placement.
- Every figure caption carries its artifacts' SHA-256 prefixes. If an artifact
  changes, the caption and `figure_manifest.json` change with it.

## 9. Reading a Result

Nobody has built this. A memory layer whose formation, ranking, routing and
stopping are all deterministic does not exist in the field; the industry
comparison — Mem0 and its neighbours — spends a language-model call on exactly
this layer. So the question is rarely *does the deterministic version win*. It
is **how much of that layer survives without the call.** A mechanism that
recovers most of it and still loses head-to-head is a finding. Reporting it as
a failure throws the finding away.

Three habits follow. They are obligations, not encouragement.

### 9.1 A stop closes a design, not a question

DMR-001 stopped on an absolute drift threshold. DMR-001B replaced it with a
relative one and passed every gate. DMR-001C confirmed the operating point on a
sealed holdout. The blocking claim written the day DMR-001 stopped was carried
forward through two more stages after the evidence beneath it had changed, and
it wrongly blocked two runnable stages.

When a stage stops, write down **what exactly is closed** — this rule, this
instrument, this corpus, this parameter — and never more than that. When new
evidence lands, re-read every downstream blocking claim against it. A blocking
claim inherits no authority from age.

### 9.2 Separate an instrument failure from a mechanism failure

NF-001 stopped because `NEVER_STOP` scored zero regret on 32-candidate streams:
the rig could not make stopping cost anything, so it could not rank a stopping
rule. DMR-004's span gate was unfalsifiable because the extracted span covered
a median 0.91 of the query. In both cases **the mechanism was never tested.**

A report that says `STOPPED` without saying which of the two happened is not a
finding, it is a tombstone. Say which. If the instrument failed, name the
instrument that would work.

### 9.3 A weak signal is a result when it was registered as one

Register **two dispositions before the run**:

- the bar for *this works*, and
- a separate, lower, explicitly numbered bar for *this carries signal worth a
  successor*.

Both fixed in advance, both in the pre-registration, both reachable in each
direction under PF4. A result landing between them is reported as signal, with
its margin, its sample size, and the successor it justifies — not rounded down
to a failure and not rounded up to a pass.

Weak means weak. Say so: NF-001's novelty rule beat matched fixed depth 11 times
in 14 by under one fact on 16 streams, and "suggestive, not demonstrated" is the
honest description of that.

### 9.4 The guardrail

None of this licenses reinterpreting a result after seeing it.

The lower bar counts **only if it was registered before the run**. The moment a
"carries signal" reading is applied to a number already on the table, it stops
being research and becomes rescue — and rescue is the exact failure this
program's pre-registration discipline exists to prevent. §3's question has a
mirror image, and both must be asked:

- Can this gate **pass** while the property it certifies is false?
- Can this gate **fail** while the property it certifies is true?
- Did the gate's tested population exist, and was its non-stopping branch
  mechanically possible on the frozen input?

§7 forbids introducing either tier late. That prohibition is what makes the
lower tier worth anything.
