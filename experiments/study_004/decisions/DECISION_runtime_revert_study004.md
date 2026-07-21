# Decision: Study 004 Runtime Revert

**Status:** Accepted and locked for Study 004

**Date:** July 21, 2026

**Author authorization:** Muzaffer authorized Study 004 to begin and this decision to be recorded on July 21, 2026.

## Finding

The NVFP4 quantization used for Study 003 showed measurable capability loss in offline testing relative to Q6-class quantization. Continuing to use it would risk making runtime capability, rather than the architecture under study, the limiting factor.

## Decision

Study 004 reverts the inference runtime to **Qwen3.6 27B UD-Q6_K_XL**, the strongest tested quantization that fits the 32 GB NVIDIA RTX 5090. It is served through the local llama.cpp HTTP server's `/completion` endpoint. The embedding runtime remains Qwen3-Embedding-0.6B Q8_0 GGUF with 1,024 dimensions.

This decision supersedes the earlier choice to retain NVFP4 as the standing baseline.

## Comparison consequence

The comparison chain now spans Study 002 on Q6_K, Study 003 on NVFP4, and Study 004 on UD-Q6_K_XL. Study 003's 12/13 result is therefore a soft non-regression floor rather than a same-runtime estimate.

## Gate

The Study 004 runtime must serve the requested model and exceed 30 generated tokens per second on the registered 200-token speed test before later sprints proceed.
