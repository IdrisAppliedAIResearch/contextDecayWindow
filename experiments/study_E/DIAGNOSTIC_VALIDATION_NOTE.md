# Diagnostic validation note

2026-09-06. Registration 2e047c41c80748b16f0e6df15dcc70ac54145598. Descriptive analysis only, after score lock ad97703a; no criterion or score change.

The first diagnostic export (`diagnostics.json` and `diagnostics_rows.json` in restart005) treated a missing Study E before-order field as an empty candidate list on unchanged latest routes. Review against the frozen Study D implementation identified this as an extraction error. It did not affect primary counts, final-source presence, reader scores or the disposition. These preliminary exports are retained solely for provenance and are nonauthoritative.

The verified exports reconstruct latest candidate order from the existing recency-route eligible indices, descending source turn with identity tie breaking. `diagnostics_verified.json` and `diagnostics_rows_verified.json`, committed at e48fe4e8, are authoritative. No model, embedding or retrieval-selection call was made. All final selected episodes were checked byte-for-byte inside the sealed rendered prompts; all temporal and retrieval blocks met their registered caps, and evidence totals match the unsealed primary cross-tab. Required carrier ranks retain null for absent stages rather than assigning a favorable rank.
