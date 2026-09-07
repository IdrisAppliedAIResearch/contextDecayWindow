"""Executable frozen-input gates, no generative calls."""
import ast
import json
from pathlib import Path
import subprocess
import numpy as np
from prepare import ROOT,P,read_rows,write_json,sha
from unified_memory.source import Unit,render,digest
from evaluation import committed

A=P/"artifacts"


def main():
    committed(P/"PRE_REGISTRATION.md")
    assert not (A/"preflight.json").exists()
    hashes={}
    def pin(path):
        committed(path)
        hashes[str(path.relative_to(ROOT))]=sha(path)
    for path in list((ROOT/"src/unified_memory").glob("*.py"))+list(P.glob("*.py")):
        pin(path)
    pin(P/"PRE_REGISTRATION.md")
    pin(P/"AMENDMENT_001_SCORING.md")
    pin(ROOT/"src/analysis/hh001_prompt.py")
    for folder in ("prepared","references","calibration","characterization_v1","characterization_v2","control","fit_v2","capacity"):
        for path in (A/folder).glob("*"):
            if path.is_file():
                pin(path)
    for folder,manifest_key in (("prepared","files"),("references","files")):
        manifest=json.loads((A/folder/"manifest.json").read_text(encoding="utf-8"))
        if manifest_key in manifest:
            for name,h in manifest[manifest_key].items():
                assert sha(A/folder/name)==h
    assert sha(Path("C:/Users/muzaf/Downloads/locomo10.json"))=="79fa87e90f04081343b8c8debecb80a9a6842b76a7aa537dc9fdf651ea698ff4"
    # Retrieval/formation import closure is a small allowlist, with no measurement module.
    allowed={"__future__","dataclasses","heapq","numpy","control","source","hashlib","json","re","xml"}
    imports={}
    for name in ("source","control","retrieval","references"):
        path=ROOT/"src/unified_memory"/f"{name}.py"
        tree=ast.parse(path.read_text(encoding="utf-8"))
        names=[]
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):
                names.extend(x.name.split(".")[0] for x in node.names)
            elif isinstance(node,ast.ImportFrom):
                names.append((node.module or "").split(".")[0])
        assert set(names)<=allowed,(name,names)
        imports[name]=names
    test=subprocess.run([str(ROOT/".venv/Scripts/python.exe"),"-X","utf8","-m","pytest",
                         str(P/"test_mechanism.py"),str(P/"test_evaluation.py"),"-q"],
                         cwd=ROOT,text=True,capture_output=True)
    assert test.returncode==0,test.stdout+test.stderr
    rows=read_rows(A/"characterization_v2/selections.jsonl.gz")
    control={r["key"]:r for r in read_rows(A/"control/selections.jsonl.gz")}
    sources=[Unit(**r) for r in read_rows(A/"prepared/sources.jsonl.gz")]
    groups={c:[u for u in sources if u.conversation==c] for c in {u.conversation for u in sources}}
    prompts=read_rows(A/"fit_v2/prompts.jsonl.gz")
    promptmap={(p["key"],p["arm"]):p for p in prompts}
    assert len(rows)==len(control)==1986 and len(promptmap)==3972
    for r in rows:
        assert r["operations"]<=r["bound"]
        assert r["direct_ids"]==control[r["key"]]["selected_ids"]
        assert set(r["direct_ids"])<=set(r["selected_ids"])
        units=groups[r["conversation"]]
        for arm,ids in (("C1",r["selected_ids"]),("C0",r["direct_ids"])):
            p=promptmap[(r["key"],arm)]
            assert digest(render(units,set(ids)))==p["evidence_sha256"]
            assert digest(p["prompt"])==p["prompt_sha256"]
    v1=json.loads((A/"characterization_v1/summary.json").read_text(encoding="utf-8"))
    v2=json.loads((A/"characterization_v2/summary.json").read_text(encoding="utf-8"))
    assert v1["full_corpus"]>0 and v2["full_corpus"]==0
    assert v2["finite"] and v2["direct_retained"] and v2["cached_replay_exact"]
    assert all(len({tuple(r["selected_ids"]) for r in rows if r["conversation"]==c})>1 for c in groups)
    fit=json.loads((A/"fit_v2/fit.json").read_text(encoding="utf-8"))
    assert fit["generative_calls"]==0 and sha(A/"fit_v2/prompts.jsonl.gz")==fit["prompt_sha256"]
    ratios=[p["tokens"]/p["full_tokens"] for p in prompts if p["arm"]=="C1"]
    selective=float(np.median(ratios))<.75 and sum(r>=.9 for r in ratios)/len(ratios)<.1
    assert selective,"Readiness guard failed; no inference"
    assert fit["maximum_input_tokens"]+4096<=fit["required_context"]
    capacity=json.loads((A/"capacity/result.json").read_text(encoding="utf-8"))
    assert capacity["status"]=="PASS" and capacity["context"]==fit["required_context"]
    # Independent control and historical behavioral identity have separate anchors.
    history=json.loads((A/"prepared/historical_replay.json").read_text(encoding="utf-8"))
    assert history["groups"]==1986 and history["exact_ids"] and history["exact_payloads"] and history["exact_scores"]
    checkout=Path("C:/Users/muzaf/contextDecayWindow-unified-control")
    assert subprocess.check_output(["git","rev-parse","HEAD"],cwd=checkout,text=True).strip()=="946c373d5edfe9d954391bdbafaed6646607659e"
    assert not subprocess.check_output(["git","status","--porcelain"],cwd=checkout,text=True).strip()
    write_json(A/"preflight.json",dict(status="PASS",hashes=hashes,context=fit["required_context"],
               tests=test.stdout,imports=imports,questions=len(rows),generative_calls=0,
               checks={"PF1":"Pinned inputs, complete pair key universe",
                       "PF2":"Route fixtures, cached real trace identity, caption fidelity",
                       "PF3":"Missing gate and token-only negative tests; runtime calibrated before reader; seals before scoring",
                       "PF4":"Strong/weak/loss and guard-failure synthetic outcomes reachable",
                       "PF5":"Content and payload identities verified across all arms",
                       "PF6":"1986 exact historical groups, independently frozen C0",
                       "PF7":"Every real queue finite; v1 full-corpus positive control; v2 query variation",
                       "PF8":"All 1986 full-source questions plus 30-link weak chain; no live endurance claim",
                       "PF9":"Residuals documented in registration; self-support and forbidden-context negatives",
                       "PF10":"Paired native-off reader required, never availability verdict"},
               selective_guard=dict(median=float(np.median(ratios)),near_full_fraction=sum(r>=.9 for r in ratios)/len(ratios))))
    print("PREFLIGHT PASS; live calibration remains mandatory")


if __name__=="__main__":
    main()
