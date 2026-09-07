"""Generation-disabled verification of the required common context."""
import json
from prepare import P,read_rows,write_json,sha
from transport import Server,gpu


def main():
    a=P/"artifacts"
    out=a/"capacity"
    out.mkdir(exist_ok=False)
    fit=json.loads((a/"fit_v2/fit.json").read_text(encoding="utf-8"))
    prompts=read_rows(a/"fit_v2/prompts.jsonl.gz")
    chosen=sorted(prompts,key=lambda p:(-p["tokens"],p["prompt_sha256"]))[:20]
    server=Server(out/"runtime",context=fit["required_context"],allow_generation=False)
    try:
        for p in chosen:
            assert server.native(p["text"])==p["prompt"]
            assert server.tokens(p["prompt"])==p["tokens"]
            assert p["tokens"]+4096<=server.context
        write_json(out/"result.json",dict(status="PASS",context=server.context,
                   gpu=gpu(),generative_calls=server.calls,checked_longest_prompts=20,
                   fit_sha256=sha(a/"fit_v2/fit.json")))
    finally:
        server.close()


if __name__=="__main__":
    main()
