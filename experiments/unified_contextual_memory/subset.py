"""User-authorized paired-prefix scoring; no benchmark generation."""
import json
from pathlib import Path
import sys
import time
import traceback
import run as r
from prepare import P,ROOT,read_rows,write_rows,write_json,sha
from evaluation import gate,committed,paired
from transport import Server,final

A=P/"artifacts"
R=A/"evaluation"
S=A/"subset"


def prepare():
    committed(P/"AMENDMENT_002_PAIRED_SUBSET.md")
    committed(Path(__file__))
    S.mkdir(exist_ok=False)
    status=R/"status.json"
    write_json(S/"stop.json",dict(reason="USER_DIRECTED_COMPUTE_REDUCTION",time=time.time(),
               prior_status=json.loads(status.read_text(encoding="utf-8"))))
    write_json(status,dict(status="USER_STOPPED",time=time.time(),scope="paired subset preparation"),exclusive=False)
    valid={}
    invalid={}
    hashes={p.name:sha(p) for p in (R/"reader").glob("*.json")}
    for p in (R/"reader").glob("*.json"):
        if p.name.endswith(".request.json"):
            continue
        try:
            value=json.loads(p.read_text(encoding="utf-8"))
            request=R/"reader"/(p.stem+".request.json")
            assert value["request_sha256"]==sha(request)
            req=json.loads(request.read_text(encoding="utf-8"))
            assert req["prompt_sha256"]==p.stem
            assert r.digest(req["request"]["prompt"])==p.stem
            final(value["response"])
            valid[p.stem]=True
        except Exception as error:
            invalid[p.stem]=repr(error)
    prompts=read_rows(A/"fit_v2/prompts.jsonl.gz")
    bykey={}
    for p in prompts:
        bykey.setdefault(p["key"],{})[p["arm"]]=p
    selected={key for key,arms in bykey.items() if set(arms)=={"C0","C1"} and all(p["prompt_sha256"] in valid for p in arms.values())}
    aliases=[dict(key=key,arm=arm,response_id=bykey[key][arm]["prompt_sha256"]) for key in sorted(selected) for arm in ("C0","C1")]
    assert {a["key"] for a in aliases}==selected
    excluded=[dict(key=key,completed_arms=[arm for arm,p in arms.items() if p["prompt_sha256"] in valid]) for key,arms in sorted(bykey.items()) if key not in selected]
    pending=sorted(p.name for p in (R/"reader").glob("*.request.json") if not (R/"reader"/(p.name.removesuffix(".request.json")+".json")).exists())
    write_rows(R/"reader_aliases.jsonl.gz",aliases)
    write_rows(S/"excluded.jsonl.gz",excluded)
    write_json(R/"reader_complete.json",dict(status="PASS_PAIRED_SUBSET_ONLY",occurrences=len(aliases),
               questions=len(selected),valid_persisted_responses=len(valid),hashes=hashes,
               aliases_sha256=sha(R/"reader_aliases.jsonl.gz"),invalid=invalid,pending=pending))
    write_json(S/"manifest.json",dict(status="PASS",questions=len(selected),valid_responses=len(valid),
               per_conversation={c:sum(bykey[k]["C0"]["conversation"]==c for k in selected) for c in sorted({p["conversation"] for p in prompts})},
               pending=pending,invalid=invalid,script_sha256=sha(__file__),
               complete_sha256=sha(R/"reader_complete.json"),excluded_sha256=sha(S/"excluded.jsonl.gz")))
    r.seal([R,S],"Seal user-stopped reader artifacts and complete paired subset before scoring")
    print(json.dumps(json.loads((S/"manifest.json").read_text(encoding="utf-8"))),flush=True)


def report():
    committed(R/"votes.json")
    votes=json.loads((R/"votes.json").read_text(encoding="utf-8"))
    links=read_rows(R/"measurement_links.jsonl.gz")
    primary={}
    majority={}
    for v in links:
        if v["category"]==5:
            continue
        meta=dict(key=v["key"],conversation=v["conversation"],category=v["category"],question=v["question"])
        primary.setdefault(v["key"],meta.copy())[v["arm"]]=votes[v["blind_id"]]["score"]
        majority.setdefault(v["key"],meta.copy())[v["arm"]]=votes[v["blind_id"]]["majority"]
    rows=list(primary.values())
    result=dict(status="EXPLORATORY_USER_STOPPED_SUBSET",primary=paired(rows),
                majority_sensitivity=paired(list(majority.values())),
                strata={str(c):paired([v for v in rows if v["category"]==c]) for c in sorted({v["category"] for v in rows})},
                conversations={c:paired([v for v in rows if v["conversation"]==c]) for c in sorted({v["conversation"] for v in rows})},
                adversarial={a:dict(n=sum(v["category"]==5 and v["arm"]==a for v in links),exact_abstentions=sum(v["category"]==5 and v["arm"]==a and v["answer"].strip()=="I don't know." for v in links)) for a in ("C0","C1")},rows=rows)
    write_json(S/"results.json",result)
    r.seal([S/"results.json"],"Seal exploratory paired-subset outcomes before retrieval diagnostics")
    units={u["id"]:u for u in read_rows(A/"prepared/sources.jsonl.gz")}
    selections={"C0":{v["key"]:v["selected_ids"] for v in read_rows(A/"control/selections.jsonl.gz")},
                "C1":{v["key"]:v["selected_ids"] for v in read_rows(A/"characterization_v2/selections.jsonl.gz")}}
    diagnostics=[]
    for v in links:
        if v["category"]==5:
            continue
        delivered={d for uid in selections[v["arm"]][v["key"]] for d in units[uid]["member_ids"]}
        ev=set(v["evidence"])
        diagnostics.append(dict(v,score=votes[v["blind_id"]]["score"],annotated_all=bool(ev) and ev<=delivered,
                    annotated_any=bool(ev&delivered),has_annotation=bool(ev),missing_annotation_ids=sorted(ev-delivered),delivered_ids=sorted(delivered)))
    write_rows(S/"diagnostics.jsonl.gz",diagnostics)
    cross={a:{f"all_{int(av)}_correct_{co}":sum(v["arm"]==a and v["has_annotation"] and v["annotated_all"]==av and v["score"]==co for v in diagnostics) for av in (False,True) for co in (0,1)} for a in ("C0","C1")}
    write_json(S/"availability_cross_tabs.json",cross)
    p=result["primary"]
    text=f"# Unified memory exploratory paired subset\n\nC0 {p['C0']}/{p['n']}; C1 {p['C1']}/{p['n']}. Difference {100*p['difference']:.2f} percentage points; descriptive conversation-cluster 95% interval [{100*p['ci95'][0]:.2f}, {100*p['ci95'][1]:.2f}]. {p['gains']} gains, {p['losses']} losses.\n\nGeneration was stopped at the user's request before scoring. This is a nonrandom completed-pair subset of previously exposed LoCoMo; the full registered comparison is not completed and no full-population WORKS disposition is claimed. Same native-thinking-off reader, shared source/captions/chronology, three same-model votes and a separate blinded adjudication. No human audit, transfer, or component-attribution claim. Annotation availability is diagnostic, not sufficiency.\n\n[Results](artifacts/subset/results.json), [question/gold/answer diagnostics](artifacts/subset/diagnostics.jsonl.gz), [scope amendment](AMENDMENT_002_PAIRED_SUBSET.md).\n"
    with (P/"REPORT.md").open("x",encoding="utf-8") as f:
        f.write(text)
    r.seal([S/"diagnostics.jsonl.gz",S/"availability_cross_tabs.json",P/"REPORT.md"],"Record exploratory subset report and evidence diagnostics")
    print(json.dumps({k:v for k,v in result.items() if k!="rows"}),flush=True)


def score():
    gate()
    for p in (Path(__file__),P/"AMENDMENT_002_PAIRED_SUBSET.md",S/"manifest.json",R/"reader_complete.json"):
        committed(p)
    m=json.loads((S/"manifest.json").read_text(encoding="utf-8"))
    assert m["status"]=="PASS" and sha(__file__)==m["script_sha256"]
    assert sha(R/"reader_complete.json")==m["complete_sha256"]
    server=Server(S/"runtime",context=45056,allow_generation=True)
    health=r.Health(R,server)
    try:
        r.RUN=S
        r.calibrate(server,health)
        r.RUN=R
        r.judge(server,health)
        report()
        health.close("COMPLETE",scope="EXPLORATORY_PAIRED_SUBSET")
    except BaseException:
        write_json(S/"failure.json",dict(time=time.time(),detail=traceback.format_exc()))
        health.close("FAILED",scope="EXPLORATORY_PAIRED_SUBSET")
        raise
    finally:
        r.RUN=R
        server.close()


if __name__=="__main__":
    {"prepare":prepare,"score":score}[sys.argv[1]]()
