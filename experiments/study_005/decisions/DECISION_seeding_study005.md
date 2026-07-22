# Decision: Study 005 Deterministic Seeding

**Status:** Accepted and locked for Study 005

**Date:** July 22, 2026

**Author authorization:** Muzaffer authorized Study 005 to proceed and this decision to be recorded through the July 22, 2026 execution request.

## Finding

Study 004 demonstrated a self-feedback architecture: generated responses are embedded, stored, and later retrieved. Unseeded control and treatment runs can therefore diverge from sampling noise before the component under test has a meaningful effect.

## Decision

Use fixed RNG seed **5005** for both the accepted Study 004 promotion control and the Study 005 treatment. The value was selected before implementation, model serving, or inspection of Study 005 outputs and will not be changed based on results.

Serve one slot only with `--parallel 1`, disable speculative decoding by omitting every speculative-decoding flag, and hold the registered sampling and cache settings identical across arms. Record the complete server command and llama.cpp build hash in each run header.

## Gate

Before the ablation:

1. Run the same fixed prefix twice under seed 5005 and require turn-identical responses.
2. Confirm the exact registered server flags and absence of speculative-decoding flags.
3. Exceed 30 generated tokens per second in the 120k-versus-50k context comparison.
4. Keep the faster context capacity, with 50k retained if performance is neutral.
5. Monitor estimated context and stop if any turn exceeds 80% of the selected capacity.

## Consequence

The paired comparison becomes reproducible through the shared prefix and attributes post-transition divergence to the different memory-formation paths, subject to the pre-registered residual floating-point nondeterminism limitation.
