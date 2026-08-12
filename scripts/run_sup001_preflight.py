from __future__ import annotations

import json
from pathlib import Path
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.sup001_preflight import run


if __name__ == "__main__":
    result = run()
    print(json.dumps({"status": result["status"], "checks": len(result["checks"])}, sort_keys=True))
