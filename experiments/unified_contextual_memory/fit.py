"""Build paired prompts and exact tokenizer fit, without generation."""
import json
import argparse
from pathlib import Path
import sys
import time
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from unified_memory.source import Unit, render, digest
from analysis.hh001_prompt import render_reader_prompt
from prepare import read_rows, write_rows, write_json, sha
from transport import Server

P = Path(__file__).parent / "artifacts"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", default="fit")
    args = parser.parse_args()
    out = P / args.output
    assert not out.exists(), "No overwriting fit artifacts"
    out.mkdir()
    sources = [Unit(**row) for row in read_rows(P / "prepared/sources.jsonl.gz")]
    conversations = {c:[u for u in sources if u.conversation == c] for c in {u.conversation for u in sources}}
    selections = {
        "C0":{r["key"]:r for r in read_rows(P / "control/selections.jsonl.gz")},
        "C1":{r["key"]:r for r in read_rows(P / "characterization_v2/selections.jsonl.gz")},
    }
    server = Server(out / "runtime", allow_generation=False)
    prompts, full = [], {}
    started = time.monotonic()
    try:
        for i, question in enumerate(read_rows(P / "prepared/questions.jsonl.gz")):
            key, conversation, text = question["key"], question["conversation"], question["question"]
            units = conversations[conversation]
            full_prompt = server.native(render_reader_prompt(text, render(units, {u.id for u in units})))
            full[key] = server.tokens(full_prompt)
            for arm in ("C0", "C1"):
                selected = set(selections[arm][key]["selected_ids"])
                block = render(units, selected)
                assert digest(block) == selections[arm][key]["evidence_sha256"]
                body = render_reader_prompt(text, block)
                native = server.native(body)
                tokens = server.tokens(native)
                prompts.append(dict(question, arm=arm, text=body, prompt=native,
                                    prompt_sha256=digest(native), tokens=tokens, full_tokens=full[key],
                                    evidence_sha256=digest(block)))
            if (i+1) % 250 == 0:
                print(json.dumps(dict(questions=i+1, total=1986)), flush=True)
        assert server.calls == 0
    finally:
        server.close()
    write_rows(out / "prompts.jsonl.gz", prompts)
    maximum = max(p["tokens"] for p in prompts)
    context = max(40960, int(np.ceil((maximum + 4096)/4096))*4096)
    result = dict(status="TOKENIZED", questions=1986, prompts=len(prompts),
                  maximum_input_tokens=maximum, required_context=context, output_reserve=4096,
                  native_thinking=False, generative_calls=0, seconds=time.monotonic()-started,
                  inputs={str(p.relative_to(P)):sha(p) for p in [P / "control/manifest.json", P / "characterization_v2/manifest.json", P / "prepared/manifest.json"]},
                  prompt_sha256=sha(out / "prompts.jsonl.gz"),
                  arms={a:dict(median_tokens=float(np.median([p["tokens"] for p in prompts if p["arm"]==a])),
                               median_paired_full_ratio=float(np.median([p["tokens"]/p["full_tokens"] for p in prompts if p["arm"]==a]))) for a in ("C0", "C1")})
    write_json(out / "fit.json", result)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
