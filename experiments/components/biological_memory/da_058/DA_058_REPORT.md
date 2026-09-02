# DA-058 Report

**Disposition:** `EXACT_CHUNK_CAPACITY_SIGNAL`

DA-058 preserves all 169,714 fitting DA-056 frames and converts 43,110 overflow
members into contiguous, self-delimiting exact chunk chains. Across 212,824
members, 257,278 frames replay byte-identically and none exceeds 2,048 chars.

Appending only the residual chains raises complete availability from 459 to
465: six gains, zero losses, two-sided exact p=.03125. Every residual requires
two chunks. Existing plus new retained slots total two or three; retained and
peak auxiliary characters have p50 2,814 and max 3,111.

This reaches the full mechanical evidence-availability ceiling without
displacement or a larger frame. Session-head selection and reader reconstruction
remain oracle operations. No model, embedding, or cache call occurred.
