"""Run C0 from its isolated checkout, not a disabled treatment."""
import gzip
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
CONTROL = Path("C:/Users/muzaf/contextDecayWindow-unified-control")
sys.path.insert(0, str(CONTROL / "src"))
from unified_memory import source, control

P = ROOT / "experiments/unified_contextual_memory/artifacts"


def rows(path):
    with gzip.open(path, "rt", encoding="utf-8") as f:
        return [json.loads(line) for line in f]


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f, "sha256").hexdigest()


def main():
    assert Path(source.__file__).resolve().is_relative_to(CONTROL)
    assert Path(control.__file__).resolve().is_relative_to(CONTROL)
    assert not subprocess.check_output(["git", "status", "--porcelain"], cwd=CONTROL, text=True).strip()
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=CONTROL, text=True).strip()
    assert commit.startswith("946c373d")
    data = json.loads(Path("C:/Users/muzaf/Downloads/locomo10.json").read_text(encoding="utf-8"))
    units = {str(row["sample_id"]):source.adapt(row["conversation"], str(row["sample_id"])) for row in data}
    prepared = rows(P / "prepared/sources.jsonl.gz")
    for unit in [u for group in units.values() for u in group]:
        assert source.canonical(unit.serialize()) == source.canonical(next(r for r in prepared if r["id"] == unit.id))
    treatment = {r["key"]:r for r in rows(P / "characterization_v2/selections.jsonl.gz")}
    output = []
    with np.load(P / "prepared/vectors.npz") as vectors:
        matrices = {c:{u.id:vectors["d_" + u.id] for u in group} for c,group in units.items()}
        for q in rows(P / "prepared/questions.jsonl.gz"):
            group = units[q["conversation"]]
            ids = [u.id for u in group]
            selected = control.select(ids, [matrices[q["conversation"]][key] for key in ids], vectors["q_" + q["key"]])
            ordered = [key for key in ids if key in selected]
            assert ordered == treatment[q["key"]]["direct_ids"]
            block = source.render(group, selected)
            output.append(dict(key=q["key"], selected_ids=ordered, evidence_sha256=source.digest(block)))
    folder = P / "control"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / "selections.jsonl.gz").open("xb") as f:
        with gzip.GzipFile(filename="", fileobj=f, mode="wb", mtime=0) as g:
            for row in output:
                g.write((source.canonical(row) + "\n").encode("utf-8"))
    result = dict(status="PASS", questions=len(output), source_parity=True,
                  direct_ids_exact=True, control_commit=commit, generative_calls=0,
                  imported_modules={str(p):sha(p) for p in [Path(source.__file__), Path(control.__file__)]},
                  selections_sha256=sha(folder / "selections.jsonl.gz"), script_sha256=sha(Path(__file__)))
    with (folder / "manifest.json").open("x", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
