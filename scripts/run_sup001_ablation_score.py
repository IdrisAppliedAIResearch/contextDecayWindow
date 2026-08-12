from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "episodic" / "src"))
sys.path.insert(0, str(REPO_ROOT))

from src.analysis.sup001_ablation_score import run


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"], "disposition": result["disposition"], "registered_pass": result["registered_pass"]}, sort_keys=True))
