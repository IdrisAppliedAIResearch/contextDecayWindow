# Architecture diagrams

The root README renders `how_it_works_remembering.mmd` inline using Mermaid.
It describes the 0.3.0 timeline, including optional continuity and explicit caller
boundaries. The prior CC80 PNG is retained as `legacy_cc80_remembering.png` for
historical reference; it does not describe the default release.

`how_it_works_saving.mmd` and its PNG describe the carried append path. The
pending user message is persisted separately; a completed exchange is committed
when the assistant message arrives. Source text and embeddings are preserved.
