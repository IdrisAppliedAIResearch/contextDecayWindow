# Pre-registration context fit resolution

The first full-population tokenizer pass found maximum native input 33,841 tokens. Initial context 32,768 fails; no reader measurement ran. Preserve artifacts/fit and native_prompts.jsonl.gz as evidence of the capacity block.

Use common context 40,960 for reader and judges: ceiling((33,841 + 4,096)/8,192)*8,192. This is arithmetic fit with the same full output allowance, not a relevance threshold or retrieval budget adjustment. Serial orchestration has ample prior measured spare VRAM; confirm full GPU allocation and at least 1,536 MiB free at startup and live calibration. Retokenize all exact native prompts at the new context and require byte identity to the first pass. Save the second fit in artifacts/fit40960 without overwriting the first. This implements the design's explicitly authorized common-context resolution before registration.
