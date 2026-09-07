# Preliminary temporal–DA fusion implementation and preflight

Status: exploratory Part 1, authorized by the user's September 6 request to draft the fusion and run a preflight. Existing exposed results are development evidence, never a new confirmation. Parent: 8d18ee7c. No reader or embedding calls. No production changes.

## Question and draft mechanism

Does DA-style temporal adjacency improve evidence selection after Study E has protected its temporal block? This is a preliminary adaptation of DA-001's TEMPORAL traversal, not the full DA-098/101 compressed allocator. Historical DA-098 availability does not establish this adaptation's efficacy or reader value.

Keep Study E C1's protected temporal ids, 8,000-character temporal allowance, 32,000-character serialized retrieval allowance, exact whole-episode renderer, CC80 ranks and additive last-32 continuity. On queries containing `before` with an anchored route, put the protected ids first, then traverse the CC80 stream: each original seed followed by its previous and next source-session neighbor, skipping duplicate emissions. Every original ranked candidate is a seed (no fitted seed-count cutoff); linked emissions do not create recursive seeds. Append any remaining direct candidates. Exclude continuity from retrieval as before. Other queries are byte-identical to C1.

The DA-001 TEMPORAL function is reused by extracting its exact function AST from the clean historical worktree at de20ac79. Study E episodes map to DA pairs; one synthetic history is one source session. This mapping and all-seed traversal are new adaptations. There is no effective-update parser, learned link, compression, member extraction, score fusion, or completion threshold. Previous/next links are adjacency, not proof of a state relationship. Original semantic candidates can include later events, as in C1; this draft adds no eligibility filter to hide that risk.

Budget retention is a comparison control, not an endorsement of character limits as a sustainable stopping policy. No resource-limit sweep. No threshold or parameter search on the 19 known misses.

## Preflight

Part 1: execute all 192 existing Study E histories, including 128 before questions and 64 latest/absence guards. Characterize added, displaced, linked-selected and total records; full serialized lengths; complete required-source delivery; carrier gains/losses; all per-question traces and distributions. Record source links for additions. Matched counts and characters will show whether any apparent gain merely admits more records, but cannot alone establish causal selectivity.

Part 2, enforced before measurement:

- PF1: hash/count sources, vectors, traces, prompts, prior curve data and historical DA source; verify clean pinned external checkouts.
- PF2: execute the original DA function; verify deterministic permutation, source-session boundaries, one-hop links and no-link identity. State the actual mapping above; do not call this DA-098.
- PF3: extraction/replay and structural gate must succeed and be committed before label-based analysis. Negative fixture must reject a failed gate.
- PF4: no efficacy disposition thresholds. Show both gain and loss measurement fixtures and active/inert traversal fixtures; a zero-change treatment is characterized, not called a negative efficacy result.
- PF5: compare exact ordered source ids anchored to content and query SHA-256; no transient generated ids or path-based joins.
- PF6: reproduce all 192 C1 context bytes against committed original prompts and selected-id sequences before fusion. No-link fusion must reproduce the same bytes. Load C1 from a separate clean checkout pinned to 8d18ee7c.
- PF7: finite traversal over a frozen seed stream, at most one emission per source; demonstrate on every full 140-record history and a two-session fixture. No persistent retrieval feedback.
- PF8: full-length replay covers these histories only; cannot test long conversational feedback or transfer. No live ablation is entered.
- PF9: evidence presence can pass while answers remain wrong; additive reach can pass by volume; exact identity may omit unlabeled alternative evidence. Report all three. No smoothness/completion claim from a sorted stream.
- PF10: a later reader-enabled comparison with a common verified prompt/runtime, full reasoning capture if requested, completeness gate and scored final answers is needed for success. This preflight cannot authorize adoption.

## Deliverables and interpretation

Draft mechanism, runnable preflight, committed label-free outputs/gate, then separate descriptive analysis and readable report. Availability improvements/regressions are diagnostics without WORKS or signal dispositions. Discuss precisely which prior precedents carry: link feasibility, reader displacement risk, compressed-versus-reader-visible budget mismatch. Preserve prior studies and scores. A full DA-098 port and fresh reader test remain separate decisions after this draft is reviewed.
