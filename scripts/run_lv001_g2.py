"""LV-001 gate G2: byte-identical seeded-prefix rerun.

Registered in `LV_001_pre_registration.md` §4. Binding: failure blocks inference.

The surrogate audit in §5 names the way this gate can pass while the property is
false — a rerun that reproduces because nothing stochastic was measured. So the
comparison is over **generated tokens**, using the same `/completion` call shape
the study runner uses (`src/inference/provider._complete_server`), on a prompt
long enough to spend a real share of the response budget.

    python scripts/run_lv001_g2.py
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
OUT = REPO / "experiments/components/live_validation/gates/g2.json"
SERVER = "http://127.0.0.1:8080"
RESPONSE_BUDGET = 2048
REPEATS = 3

# Drawn from the corpus so the prompt exercises the same domain vocabulary the
# run will, rather than a synthetic string the model may treat differently.
PROMPT = (
    "You are a research assistant with a long conversational memory.\n\n"
    "<retrieved_stm>\n"
    "<episode turn=\"55\">\n"
    "<user>Tell me about the painting known as The Annunciation of Forli.</user>\n"
    "<assistant>It was completed in 1483 by Melozzo da Forli, under the "
    "patronage of Cardinal Giuliano della Rovere.</assistant>\n"
    "</episode>\n"
    "</retrieved_stm>\n\n"
    "Summarise every fact you have about this painting, then explain in detail "
    "how patronage shaped fifteenth-century Italian religious commissions."
)


def complete(prompt: str) -> dict:
    payload = json.dumps({
        "prompt": f"{prompt}\n<think>\n</think>\n",
        "n_predict": RESPONSE_BUDGET,
        "reasoning_format": "none",
        "stream": False,
    }).encode("utf-8")
    request = Request(f"{SERVER}/completion", data=payload,
                      headers={"Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=900) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    runs = []
    for index in range(REPEATS):
        result = complete(PROMPT)
        content = result.get("content", "")
        runs.append({
            "run": index + 1,
            "chars": len(content),
            "tokens_predicted": result.get("tokens_predicted"),
            "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        })
        print(f"  run {index + 1}: {len(content)} chars, "
              f"{result.get('tokens_predicted')} tokens, "
              f"{runs[-1]['sha256'][:16]}")

    digests = {r["sha256"] for r in runs}
    identical = len(digests) == 1
    # A gate that passes on an empty or trivial generation certifies nothing.
    substantive = all(r["tokens_predicted"] and r["tokens_predicted"] >= 128
                      for r in runs)

    record = {
        "gate": "G2",
        "certifies": "the same prompt under the registered seed produces a "
                     "byte-identical generation across repeated calls",
        "server": SERVER,
        "repeats": REPEATS,
        "compared": "generated content only, not the prompt or retrieval block",
        "runs": runs,
        "distinct_digests": len(digests),
        "identical": identical,
        "generation_substantive": substantive,
        "min_tokens_required": 128,
        "status": "PASS" if identical and substantive else "FAIL",
    }
    OUT.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")

    print(f"\nG2: {record['status']}"
          f"  ({len(digests)} distinct digest(s) over {REPEATS} runs)")
    if not substantive:
        print("  generation too short to certify anything")
    return 0 if record["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
