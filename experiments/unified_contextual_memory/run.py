"""Serial registered evaluation; durable raw calls and ordered sealing."""
import json
import os
from pathlib import Path
import statistics
import subprocess
import threading
import time
import traceback
from prepare import ROOT, P, read_rows, write_rows, write_json, sha
from unified_memory.source import digest, canonical
from analysis.hh001_prompt import render_judge_prompt
from transport import Server, BASE, final, gpu
from evaluation import gate, verdict, committed, paired, disposition

A = P / "artifacts"
RUN = A / "evaluation"


def seal(paths, message):
    subprocess.run(["git", "add", "--", *map(str, paths)], cwd=ROOT, check=True)
    subprocess.run(["git", "commit", "-m", message], cwd=ROOT, check=True)
    for path in paths:
        committed(path)


class Health:
    def __init__(self, folder, server):
        self.folder, self.server = folder, server
        self.phase, self.done, self.total = "calibration", 0, 17
        self.active_since = None
        self.durations = []
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self.watch, daemon=True)
        self.thread.start()

    def event(self, kind, **fields):
        with (self.folder / "events.jsonl").open("a", encoding="utf-8") as f:
            f.write(canonical(dict(time=time.time(), kind=kind, **fields))+"\n")
            f.flush()
            os.fsync(f.fileno())

    def state(self, status="RUNNING", **extra):
        value = dict(status=status, phase=self.phase, done=self.done,total=self.total,
                     time=time.time(),runner_pid=os.getpid(),server_pid=self.server.process.pid,
                     median_call_seconds=statistics.median(self.durations[-100:]) if self.durations else None,
                     **extra)
        temp = self.folder / "status.tmp"
        temp.write_text(canonical(value), encoding="utf-8")
        os.replace(temp,self.folder / "status.json")

    def watch(self):
        low = 0
        warned = False
        while not self.closed.wait(15):
            try:
                memory = gpu()
                age = time.monotonic()-self.active_since if self.active_since else 0
                low = low+1 if memory["free_mib"]<1024 else 0
                if self.server.process.poll() is not None or low>=2:
                    self.event("FAILURE", reason="owned server exited or sustained low VRAM", gpu=memory)
                    if self.server.process.poll() is None:
                        self.server.process.terminate()
                    return
                if age>120 and not warned:
                    self.event("SLOW_CALL", seconds=age,gpu=memory)
                    warned=True
                if age<120:
                    warned=False
                self.state(gpu=memory,active_seconds=age)
            except BaseException:
                self.event("MONITOR_ERROR",detail=traceback.format_exc())
                if self.server.process.poll() is None:
                    self.server.process.terminate()
                return

    def close(self,status,**fields):
        self.closed.set()
        self.thread.join(timeout=20)
        self.state(status,**fields)
        self.event(status,**fields)


def call(server, health, folder, identifier, prompt, **settings):
    folder.mkdir(parents=True, exist_ok=True)
    pending = folder / f"{identifier}.request.json"
    target = folder / f"{identifier}.json"
    # Never retry uncertain requests, and never overwrite an existing answer.
    request = dict(BASE,prompt=prompt,**settings)
    write_json(pending,dict(request=request,prompt_sha256=digest(prompt),time=time.time()))
    health.active_since=time.monotonic()
    try:
        response=server.post("completion",request)
        elapsed=time.monotonic()-health.active_since
        write_json(target,dict(response=response,seconds=elapsed,request_sha256=sha(pending)))
        answer=final(response)
        health.durations.append(elapsed)
        health.done+=1
        return answer
    finally:
        health.active_since=None


def calibrate(server,health):
    folder=RUN/"calibration"
    prompt=server.native("What is 17 + 28? Answer only the number.")
    answers=[call(server,health,folder,f"arithmetic_{i}",prompt,n_predict=64) for i in range(2)]
    assert answers==["45","45"],"Thinking-off/reader calibration failed"
    fixtures=[("Where did Jo move?","Paris","",False),
              ("What did Jo buy?","a red bicycle","A bike that is red.",True),
              ("Where did Jo move?","Paris","Rome",False),
              ("When did Jo move?","May 2024","May 2023",False),
              ("Where did Jo move?","Paris","Jo moved to Rome, not Paris.",False)]
    for i,(q,g,a,expected) in enumerate(fixtures):
        native=server.native(render_judge_prompt(q,g,a))
        for seed in (9100,9101,9102):
            text=call(server,health,folder,f"judge_{i}_{seed}",native,seed=seed,temperature=.2,top_p=.9)
            assert verdict(text)[0]==expected,"Judge calibration failed"
    write_json(folder/"complete.json",dict(status="PASS",calls=17,native_thinking=False,
               hashes={p.name:sha(p) for p in folder.glob("*.json")}))
    seal([folder],"Seal unified-memory reader and judge calibration")


def reader(server,health,fit_folder):
    gate()
    committed(RUN/"calibration/complete.json")
    prompts=read_rows(fit_folder/"prompts.jsonl.gz")
    keys=sorted({p["key"] for p in prompts})
    # Fixed two questions per conversation first; no outcomes used in ordering.
    by_key={p["key"]:p for p in prompts}
    early=set()
    for c in sorted({p["conversation"] for p in prompts}):
        early.update([k for k in keys if by_key[k]["conversation"]==c][:2])
    order={k:i for i,k in enumerate(sorted(early)+[k for k in keys if k not in early])}
    prompts.sort(key=lambda p:(order[p["key"]],(0 if p["arm"]==("C0" if order[p["key"]]%2==0 else "C1") else 1)))
    health.phase,health.done,health.total="reader",0,len({p["prompt_sha256"] for p in prompts})
    seen,aliases={},[]
    for p in prompts:
        h=p["prompt_sha256"]
        assert digest(p["prompt"])==h
        if h not in seen:
            assert server.native(p["text"])==p["prompt"]
            assert p["tokens"]+4096<=server.context
            call(server,health,RUN/"reader",h,p["prompt"])
            seen[h]=True
        aliases.append(dict(key=p["key"],arm=p["arm"],response_id=h))
    write_rows(RUN/"reader_aliases.jsonl.gz",aliases)
    write_json(RUN/"reader_complete.json",dict(status="PASS",occurrences=len(aliases),calls=len(seen),
               aliases_sha256=sha(RUN/"reader_aliases.jsonl.gz"),
               hashes={p.name:sha(p) for p in (RUN/"reader").glob("*.json")}))
    seal([RUN/"reader",RUN/"reader_aliases.jsonl.gz",RUN/"reader_complete.json"],
         "Seal all unified-memory reader responses before scoring")


def judge(server,health):
    committed(RUN/"reader_complete.json")
    complete=json.loads((RUN/"reader_complete.json").read_text(encoding="utf-8"))
    for name,h in complete["hashes"].items():
        assert sha(RUN/"reader"/name)==h
    assert sha(RUN/"reader_aliases.jsonl.gz")==complete["aliases_sha256"]
    # Gold enters measurement only, after reader completeness is committed.
    corpus=json.loads(Path("C:/Users/muzaf/Downloads/locomo10.json").read_text(encoding="utf-8"))
    raw={str(c["sample_id"]):c["qa"] for c in corpus}
    questions={q["key"]:q for q in read_rows(A/"prepared/questions.jsonl.gz")}
    aliases=read_rows(RUN/"reader_aliases.jsonl.gz")
    blind,links={},[]
    for a in aliases:
        q=questions[a["key"]]
        item=raw[q["conversation"]][q["source_index"]]
        assert item["question"]==q["question"]
        answer=final(json.loads((RUN/"reader"/f'{a["response_id"]}.json').read_text(encoding="utf-8"))["response"])
        category=int(item["category"])
        b=None
        if category!=5:
            text=render_judge_prompt(q["question"],str(item["answer"]),answer)
            b=digest(text)
            blind[b]=dict(id=b,text=text)
        links.append(dict(a,conversation=q["conversation"],question=q["question"],category=category,
                          blind_id=b,answer=answer,gold=item.get("answer"),evidence=item.get("evidence",[])))
    write_rows(RUN/"blind_surface.jsonl.gz",[blind[k] for k in sorted(blind)])
    write_rows(RUN/"measurement_links.jsonl.gz",links)
    seal([RUN/"blind_surface.jsonl.gz",RUN/"measurement_links.jsonl.gz"],"Seal arm-blind unified-memory judge surface")
    health.phase,health.done,health.total="judge",0,len(blind)*3
    for b in sorted(blind):
        native=server.native(blind[b]["text"])
        assert server.tokens(native)+4096<=server.context
        for seed in (9100,9101,9102):
            text=call(server,health,RUN/"judges",f"{b}_{seed}",native,seed=seed,temperature=.2,top_p=.9)
            verdict(text) # Fail immediately on malformed final vote, without interpretation.
    write_json(RUN/"judge_complete.json",dict(status="PASS",calls=health.done,
               hashes={p.name:sha(p) for p in (RUN/"judges").glob("*.json")}))
    seal([RUN/"judges",RUN/"judge_complete.json"],"Seal all unified-memory judgments before vote aggregation")
    votes={}
    for b in sorted(blind):
        values=[verdict(final(json.loads((RUN/"judges"/f"{b}_{seed}.json").read_text(encoding="utf-8"))["response"])) for seed in (9100,9101,9102)]
        votes[b]=dict(votes=values,score=int(sum(v[0] for v in values)>=2),disagreement=len({v[0] for v in values})>1)
    write_json(RUN/"votes.json",votes)
    seal([RUN/"votes.json"],"Seal unified-memory blind scores before paired outcomes")


def report():
    committed(RUN/"votes.json")
    votes=json.loads((RUN/"votes.json").read_text(encoding="utf-8"))
    links=read_rows(RUN/"measurement_links.jsonl.gz")
    rows={}
    for r in links:
        if r["category"]==5:
            continue
        item=rows.setdefault(r["key"],dict(key=r["key"],conversation=r["conversation"],category=r["category"],question=r["question"]))
        item[r["arm"]]=votes[r["blind_id"]]["score"]
    rows=list(rows.values())
    assert len(rows)==1540
    overall=paired(rows)
    strata={str(c):paired([r for r in rows if r["category"]==c]) for c in (1,2,3,4)}
    fits=json.loads((A/"fit_v2/fit.json").read_text(encoding="utf-8"))
    ps=[p for p in read_rows(A/"fit_v2/prompts.jsonl.gz") if p["arm"]=="C1"]
    selective=fits["arms"]["C1"]["median_paired_full_ratio"]<.75 and sum(p["tokens"]/p["full_tokens"]>=.9 for p in ps)/len(ps)<.1
    unique={}
    for r in rows:
        unique.setdefault((r["conversation"],r["question"]),r)
    result=dict(primary=overall,strata=strata,disposition=disposition(overall,strata,selective),
                selective=selective,deduplicated_sensitivity=paired(list(unique.values())),
                adversarial={a:dict(n=446,exact_abstentions=sum(r["answer"].strip()=="I don't know." for r in links if r["category"]==5 and r["arm"]==a)) for a in ("C0","C1")},
                judge_disagreements=sum(v["disagreement"] for v in votes.values()),rows=rows)
    write_json(RUN/"results.json",result)
    seal([RUN/"results.json"],"Seal paired unified-memory development outcomes")
    print(json.dumps({k:v for k,v in result.items() if k!="rows"}),flush=True)


def main():
    manifest=gate()
    RUN.mkdir(exist_ok=False)
    write_json(RUN/"run_header.json",dict(preflight_sha256=sha(A/"preflight.json"),
               registration_sha256=sha(P/"PRE_REGISTRATION.md"),pid=os.getpid(),time=time.time()))
    server=None
    health=None
    try:
        server=Server(RUN/"runtime",context=manifest["context"],allow_generation=True)
        health=Health(RUN,server)
        calibrate(server,health)
        reader(server,health,A/"fit_v2")
        judge(server,health)
        report()
        health.close("COMPLETE")
    except BaseException:
        write_json(RUN/"failure.json",dict(time=time.time(),detail=traceback.format_exc()))
        if health:
            health.close("FAILED")
        raise
    finally:
        if server:
            server.close()


if __name__=="__main__":
    main()
