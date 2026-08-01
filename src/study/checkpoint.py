"""Atomic, auditable checkpoints for long Study 010 runs.

The implementation moved as-is into the episodic library (CC-002);
re-exported here for the study runners that carry it.
"""

from episodic._checkpoint import (  # noqa: F401
    restore_checkpoint,
    write_checkpoint,
)
