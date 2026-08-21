"""An OpenAI-shaped `/v1/embeddings` endpoint backed by the carried embedder.

Mem0 reaches its embedder over HTTP. The local llama-server is started without
`--embeddings` and answers `/v1/embeddings` with 501, and its start script is
not ours to change. Pointing Mem0 at its own default embedder instead would
break the one thing `HH_001_DEVELOPMENT_PLAN.md` §4 fixes across arms: every
arm that embeds uses the pinned `Qwen3-Embedding-0.6B-Q8_0`, so the contrast is
memory architecture and not embedder quality.

So this serves that embedder, and nothing else.

**One text per model call, always.** The batch endpoint loops rather than
batching, because the same text embedded in a different call shape comes back
as a different vector — close enough to look identical (cosine 0.999837 in the
case this programme measured) and different enough to flip selections. Every
arm must see the vector the sealed cache holds.

Run it, note the port, and point Mem0 at it:

    python scripts/hh001_embedding_shim.py --port 8100
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))


def _load_env() -> None:
    path = REPO_ROOT / ".env"
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, value = line.partition("=")
            os.environ.setdefault(key.strip(), value.strip())


_load_env()

_LOCK = threading.Lock()
_EMBED = None
_CALLS = {"texts": 0, "requests": 0}


def _embedder():
    global _EMBED
    if _EMBED is None:
        from retrieval_bakeoff.embedding import CarriedEmbedder

        model_path = Path(os.environ["CDW_EMBEDDING_MODEL_PATH"])
        delegate = CarriedEmbedder(model_path)
        delegate.assert_carried_model()
        _EMBED = delegate
    return _EMBED


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, *args) -> None:  # noqa: A003
        pass

    def _send(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:  # noqa: N802
        if self.path.rstrip("/") in ("/v1/models", "/models"):
            self._send(200, {
                "object": "list",
                "data": [{"id": "carried-qwen3-embedding", "object": "model"}],
            })
            return
        if self.path.rstrip("/") == "/health":
            self._send(200, {"status": "ok", "calls": dict(_CALLS)})
            return
        self._send(404, {"error": {"message": f"no route {self.path}"}})

    def do_POST(self) -> None:  # noqa: N802
        if self.path.rstrip("/") not in ("/v1/embeddings", "/embeddings"):
            self._send(404, {"error": {"message": f"no route {self.path}"}})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            request = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError as error:
            self._send(400, {"error": {"message": f"bad JSON: {error}"}})
            return

        raw = request.get("input")
        if isinstance(raw, str):
            texts = [raw]
        elif isinstance(raw, list) and all(isinstance(t, str) for t in raw):
            texts = raw
        else:
            self._send(400, {"error": {"message": "input must be a string or list of strings"}})
            return

        try:
            with _LOCK:
                embedder = _embedder()
                # One text per model call. Never a batch. See the module
                # docstring for why this is not an optimization to make later.
                vectors = [embedder(text) for text in texts]
                _CALLS["texts"] += len(texts)
                _CALLS["requests"] += 1
        except Exception as error:  # noqa: BLE001
            self._send(500, {"error": {"message": f"{type(error).__name__}: {error}"}})
            return

        self._send(200, {
            "object": "list",
            "model": request.get("model", "carried-qwen3-embedding"),
            "data": [
                {
                    "object": "embedding",
                    "index": index,
                    "embedding": [float(value) for value in vector],
                }
                for index, vector in enumerate(vectors)
            ],
            "usage": {"prompt_tokens": 0, "total_tokens": 0},
        })


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--host", default="127.0.0.1")
    args = parser.parse_args()

    _embedder()  # fail loudly at startup, not on the first request
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"carried-embedder shim on http://{args.host}:{args.port}/v1", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
