# Invalid Ablation Attempt

**Status:** INVALID_SHARED_SERVER_RNG_STREAM  
**Stopped after:** 11 completed turns

This attempt reused server PID `19072` after `tier6_ablation_a`. Although turn
1 had the same constructed prompt, its answer differed immediately:

- Ablation A answer SHA-256:
  `265ddd79f2cb6f029fcf1d116780285731d228ceaa06e0646d0c5baecc2953f4`
- This attempt answer SHA-256:
  `9675ab02bc05cf3fd2f8e73e5d406b4e4a14ed1a03eea5b79979d8d5877198ad`

The fixed seed initializes a server-lifetime RNG stream; it does not reset that
stream between sequential runs on one process. The attempt was terminated as
soon as the divergence was localized. It is retained only as blocker evidence
for Amendment 008 and is excluded from every gate and result.
