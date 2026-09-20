"""Owned serial reader transport. Token-only sessions cannot generate."""
import json
import os
from pathlib import Path
import socket
import subprocess
import time
import urllib.request
from prepare import ROOT, write_json, sha

OLD = ROOT / "experiments/study_E/artifacts/confirmation/restart005"
BASE = dict(seed=5005, temperature=.6, top_p=.95, top_k=20, min_p=0,
            repeat_penalty=1, presence_penalty=0, cache_prompt=False,
            reasoning_format="none", n_predict=4096, id_slot=0)


def gpu():
    value = subprocess.check_output(["nvidia-smi", "--query-gpu=memory.used,memory.free,utilization.gpu",
                                     "--format=csv,noheader,nounits"], text=True,
                                    creationflags=subprocess.CREATE_NO_WINDOW, timeout=10)
    return dict(zip(("used_mib", "free_mib", "utilization"), map(int, value.strip().split(","))))


class Server:
    def __init__(self, folder: Path, *, context=40960, allow_generation=False):
        self.folder, self.context, self.allow_generation = folder, context, allow_generation
        self.calls = 0
        with socket.socket() as s:
            if s.connect_ex(("127.0.0.1", 8099)) == 0:
                raise RuntimeError("Port occupied; refusing to reuse another server")
        pins = json.loads((OLD / "runtime_pins.json").read_text(encoding="utf-8"))
        for pin in pins:
            if sha(pin["path"]) != pin["sha256"]:
                raise RuntimeError("Pinned reader runtime changed")
        command = json.loads((OLD / "launch.json").read_text(encoding="utf-8"))["command"]
        # This build assigns model-placement INFO logs to trace verbosity.
        command.extend(["--log-verbosity", "4"])
        for flag, value in (("--port", "8099"), ("--parallel", "1"), ("--ctx-size", str(context))):
            command[command.index(flag)+1] = value
        assert command[command.index("--reasoning")+1] == "off"
        assert command[command.index("--reasoning-budget")+1] == "0"
        folder.mkdir(parents=True, exist_ok=True)
        self.stdout = (folder / "server.out").open("xb")
        self.stderr = (folder / "server.err").open("xb")
        env = os.environ.copy()
        env["PATH"] = "C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v13.2/bin/x64;C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA/v12.6/bin;" + env["PATH"]
        self.process = subprocess.Popen(command, stdout=self.stdout, stderr=self.stderr,
                                        env=env, creationflags=subprocess.CREATE_NO_WINDOW)
        write_json(folder / "launch.json", dict(pid=self.process.pid, runner_pid=os.getpid(),
                   command=command, pins=pins, allow_generation=allow_generation))
        try:
            for _ in range(180):
                if self.process.poll() is not None:
                    raise RuntimeError("Owned server exited during startup")
                try:
                    props = self.post("props")
                    break
                except OSError:
                    time.sleep(1)
            else:
                raise TimeoutError("Server startup timed out")
            assert props["total_slots"] == 1
            assert "offloaded 66/66 layers to GPU" in (folder / "server.err").read_text(errors="replace")
            assert "thinking = 0" in (folder / "server.err").read_text(errors="replace")
            assert gpu()["free_mib"] >= 1536
            write_json(folder / "props.json", props)
        except BaseException:
            self.close()
            raise

    def post(self, route, data=None):
        if route == "completion":
            if not self.allow_generation:
                raise PermissionError("Token-only transport forbids generation")
            self.calls += 1
        request = urllib.request.Request("http://127.0.0.1:8099/" + route,
                  data=None if data is None else json.dumps(data).encode("utf-8"),
                  headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.load(response)

    def native(self, text):
        prompt = self.post("apply-template", dict(messages=[dict(role="user", content=text)],
                           add_generation_prompt=True, chat_template_kwargs={"enable_thinking":False},
                           reasoning_effort="none"))["prompt"]
        if not prompt.endswith("<think>\n\n</think>\n\n"):
            raise ValueError("Native thinking-off template drift")
        return prompt

    def tokens(self, prompt):
        return len(self.post("tokenize", dict(content=prompt, add_special=False))["tokens"])

    def close(self):
        if self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=20)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        self.stdout.close()
        self.stderr.close()
        write_json(self.folder / "stopped.json", dict(pid=self.process.pid,
                   exit_code=self.process.returncode, generative_calls=self.calls))


def final(response):
    if response.get("truncated") or response.get("stop_type") != "eos":
        raise ValueError("Capped or non-EOS response")
    content = response.get("content", "").strip()
    if not content or "<think>" in content or "</think>" in content:
        raise ValueError("Empty answer or exposed reasoning")
    return content
