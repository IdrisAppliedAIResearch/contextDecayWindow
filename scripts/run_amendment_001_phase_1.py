"""Run Amendment 001 Phase 1: the sampling-mode determinism probe.

Launches the llama.cpp server itself, one process per condition — and for
``greedy_temp0_fresh_process``, one per round — so the conditions differ
only in the sampler settings the amendment names. Everything else is the
standing runtime as recorded in Study 011's launch manifests.

The probe is resumable. Generations are appended to a checkpoint as they
complete, so a three-hour run that dies in its last condition does not
throw away the first two. The checkpoint is keyed by condition, round and
prompt, and a resumed run reuses only entries whose prompt digest still
matches.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from src.analysis.study_011_sampling_determinism import (  # noqa: E402
    CONDITIONS,
    PROMPT_COUNT,
    REPEATS,
    Prompt,
    PromptOutcome,
    build_report,
    select_prompts,
    summarize_condition,
    write_report,
)

STUDY_ROOT = REPO_ROOT / "experiments" / "study_011"
DEFAULT_OUTPUT = STUDY_ROOT / "runtime" / "phase_1_sampling_determinism.json"
DEFAULT_CHECKPOINT = STUDY_ROOT / "runtime" / "phase_1_checkpoint.jsonl"

SERVER_BINARY = Path(
    os.environ.get(
        "CDW_INFERENCE_SERVER_BINARY",
        r"C:\Users\muzaf\.unsloth\llama.cpp\build\bin\Release\llama-server.exe",
    )
)
MODEL_PATH = Path(
    os.environ.get(
        "CDW_INFERENCE_MODEL_PATH",
        r"C:\Users\muzaf\.cache\huggingface\hub\models--unsloth--Qwen3.6-27B-MTP-GGUF"
        r"\snapshots\5cb35eb3dcbf52dbce5f87dbc64df6aaffadcace"
        r"\Qwen3.6-27B-UD-Q6_K_XL.gguf",
    )
)
SERVER_URL = os.environ.get("CDW_INFERENCE_SERVER_URL", "http://127.0.0.1:8080")
SEED = 5005

# The standing runtime, transcribed from study_011_live_d_launch_manifest.json.
# Only --temp moves between conditions; everything else is held.
BASE_SERVER_ARGS = (
    "--host", "127.0.0.1",
    "--port", "8080",
    "--ctx-size", "50000",
    "--parallel", "1",
    "--cache-type-k", "q8_0",
    "--cache-type-v", "q8_0",
    "--flash-attn", "on",
    "--jinja",
    "--metrics",
    "--top-p", "0.95",
    "--top-k", "20",
    "--min-p", "0.0",
    "--presence-penalty", "0.0",
    "--repeat-penalty", "1.0",
    "--seed", str(SEED),
)

CONDITION_TEMPERATURE = {
    "standing_temp1_same_process": "1",
    "greedy_temp0_same_process": "0",
    "greedy_temp0_fresh_process": "0",
}
FRESH_PROCESS_CONDITION = "greedy_temp0_fresh_process"


class Server:
    """A llama.cpp server process, started and stopped by this script."""

    def __init__(self, temperature: str, log_dir: Path, tag: str) -> None:
        self.temperature = temperature
        self.log_dir = log_dir
        self.tag = tag
        self.process: subprocess.Popen | None = None
        self.props: dict = {}

    @property
    def command(self) -> list[str]:
        return [
            str(SERVER_BINARY),
            "-m", str(MODEL_PATH),
            *BASE_SERVER_ARGS,
            "--temp", self.temperature,
        ]

    def start(self, timeout: float = 900.0) -> "Server":
        self.log_dir.mkdir(parents=True, exist_ok=True)
        log_path = self.log_dir / f"server_{self.tag}.log"
        self._log = log_path.open("w", encoding="utf-8", errors="replace")
        self.process = subprocess.Popen(
            self.command,
            stdout=self._log,
            stderr=subprocess.STDOUT,
            cwd=str(SERVER_BINARY.parent),
        )
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError(
                    f"server exited during startup: see {log_path}"
                )
            try:
                with urlopen(f"{SERVER_URL}/props", timeout=5) as response:
                    self.props = json.loads(response.read().decode("utf-8"))
                return self
            except (URLError, OSError, json.JSONDecodeError):
                time.sleep(2.0)
        self.stop()
        raise RuntimeError(f"server did not become ready within {timeout}s")

    def assert_settings(self) -> None:
        """The sampler the server actually loaded is what gets recorded."""

        params = self.props["default_generation_settings"]["params"]
        expected = float(self.temperature)
        if abs(float(params["temperature"]) - expected) > 1e-9:
            raise RuntimeError(
                f"server temperature is {params['temperature']}, expected {expected}"
            )
        if int(params["seed"]) != SEED:
            raise RuntimeError(f"server seed is {params['seed']}, expected {SEED}")
        if params.get("speculative.types") not in (None, "none"):
            raise RuntimeError("speculative decoding is enabled")
        if int(self.props.get("total_slots", 0)) != 1:
            raise RuntimeError("server is not running --parallel 1")

    def stop(self) -> None:
        if self.process is None:
            return
        if os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", str(self.process.pid), "/T", "/F"],
                capture_output=True,
            )
        else:
            self.process.terminate()
        try:
            self.process.wait(timeout=120)
        except subprocess.TimeoutExpired:
            self.process.kill()
        self.process = None
        log = getattr(self, "_log", None)
        if log is not None:
            log.close()
        # The port takes a moment to free; a fresh-process condition that
        # reconnects to a dying server would silently stop being fresh.
        time.sleep(3.0)

    def __enter__(self) -> "Server":
        self.start()
        self.assert_settings()
        return self

    def __exit__(self, *exc_info) -> None:
        self.stop()


def _completion(prompt: str) -> str:
    """Generate through the same provider the live runs used.

    Not a hand-rolled HTTP call: the provider prefixes a closed think
    block and appends the rule-detection instruction, and a probe that
    skipped either would be measuring a call shape no study ever made.
    """
    from src.inference.provider import InferenceProvider

    os.environ["CDW_INFERENCE_SERVER_URL"] = SERVER_URL
    return InferenceProvider().complete(prompt).assistant_message


class Checkpoint:
    """Append-only record of completed generations."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.entries: dict[tuple[str, int, int], str] = {}
        self.digests: dict[int, str] = {}

    def load(self, prompts: list[Prompt]) -> int:
        if not self.path.is_file():
            return 0
        expected = {prompt.turn: prompt.sha256 for prompt in prompts}
        kept = 0
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if expected.get(int(row["turn"])) != row["prompt_sha256"]:
                continue
            self.entries[
                (row["condition"], int(row["round"]), int(row["turn"]))
            ] = row["output"]
            kept += 1
        return kept

    def record(
        self,
        condition: str,
        round_index: int,
        prompt: Prompt,
        output: str,
    ) -> None:
        key = (condition, round_index, prompt.turn)
        self.entries[key] = output
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8", newline="\n") as handle:
            handle.write(
                json.dumps(
                    {
                        "condition": condition,
                        "round": round_index,
                        "turn": prompt.turn,
                        "prompt_sha256": prompt.sha256,
                        "output": output,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    def get(self, condition: str, round_index: int, turn: int) -> str | None:
        return self.entries.get((condition, round_index, turn))


def run_same_process_condition(
    condition: str,
    prompts: list[Prompt],
    repeats: int,
    checkpoint: Checkpoint,
    log_dir: Path,
) -> tuple[list[PromptOutcome], dict]:
    outcomes = {prompt.turn: PromptOutcome(turn=prompt.turn) for prompt in prompts}
    server_record: dict = {}
    pending = [
        (round_index, prompt)
        for round_index in range(repeats)
        for prompt in prompts
        if checkpoint.get(condition, round_index, prompt.turn) is None
    ]
    if pending:
        with Server(CONDITION_TEMPERATURE[condition], log_dir, condition) as server:
            server_record = {
                "server_pids": [server.process.pid],
                "server_build_hash": server.props["build_info"],
                "server_command": " ".join(server.command),
                "temperature": float(server.temperature),
                "processes": 1,
            }
            for round_index, prompt in pending:
                output = _completion(prompt.text)
                checkpoint.record(condition, round_index, prompt, output)
                print(
                    f"  {condition} round {round_index + 1}/{repeats} "
                    f"turn {prompt.turn}: {len(output)} chars",
                    flush=True,
                )
    else:
        server_record = {"server_pids": [], "resumed_from_checkpoint": True}
    for round_index in range(repeats):
        for prompt in prompts:
            outcomes[prompt.turn].outputs.append(
                checkpoint.get(condition, round_index, prompt.turn)
            )
    return [outcomes[prompt.turn] for prompt in prompts], server_record


def run_fresh_process_condition(
    prompts: list[Prompt],
    repeats: int,
    checkpoint: Checkpoint,
    log_dir: Path,
) -> tuple[list[PromptOutcome], dict]:
    """One server process per round, so every repeat is across-process.

    §3.2.4 asks for a freshly started server process for each generation.
    A round is one generation of every prompt, so one process per round
    gives each prompt's ten generations ten distinct processes — which is
    what the clause is for — without restarting a 26 GB model two hundred
    times to obtain the same comparison.
    """
    condition = FRESH_PROCESS_CONDITION
    outcomes = {prompt.turn: PromptOutcome(turn=prompt.turn) for prompt in prompts}
    pids: list[int] = []
    build_hashes: set[str] = set()
    command = ""
    for round_index in range(repeats):
        pending = [
            prompt
            for prompt in prompts
            if checkpoint.get(condition, round_index, prompt.turn) is None
        ]
        if not pending:
            continue
        tag = f"{condition}_round_{round_index + 1:02d}"
        with Server(CONDITION_TEMPERATURE[condition], log_dir, tag) as server:
            pids.append(server.process.pid)
            build_hashes.add(server.props["build_info"])
            command = " ".join(server.command)
            for prompt in pending:
                output = _completion(prompt.text)
                checkpoint.record(condition, round_index, prompt, output)
                print(
                    f"  {condition} process {round_index + 1}/{repeats} "
                    f"turn {prompt.turn}: {len(output)} chars",
                    flush=True,
                )
    if len(pids) > 1 and len(set(pids)) != len(pids):
        raise RuntimeError("a fresh-process round reused a server PID")
    for round_index in range(repeats):
        for prompt in prompts:
            outcomes[prompt.turn].outputs.append(
                checkpoint.get(condition, round_index, prompt.turn)
            )
    return [outcomes[prompt.turn] for prompt in prompts], {
        "server_pids": pids,
        "server_build_hash": sorted(build_hashes),
        "server_command": command,
        "temperature": float(CONDITION_TEMPERATURE[condition]),
        "processes": repeats,
        "one_process_per_round": True,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--checkpoint", type=Path, default=DEFAULT_CHECKPOINT)
    parser.add_argument("--prompts", type=int, default=PROMPT_COUNT)
    parser.add_argument("--repeats", type=int, default=REPEATS)
    parser.add_argument(
        "--conditions",
        nargs="*",
        default=list(CONDITIONS),
        choices=list(CONDITIONS),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.prompts < 20:
        raise SystemExit("§3.2 registers at least 20 prompts")
    if args.repeats < 10:
        raise SystemExit("§3.2 registers 10 generations per prompt")
    if not SERVER_BINARY.is_file():
        raise SystemExit(f"server binary not found: {SERVER_BINARY}")
    if not MODEL_PATH.is_file():
        raise SystemExit(f"model not found: {MODEL_PATH}")

    prompts = select_prompts(count=args.prompts)
    checkpoint = Checkpoint(args.checkpoint)
    reused = checkpoint.load(prompts)
    if reused:
        print(f"resumed {reused} generations from {args.checkpoint}", flush=True)

    log_dir = STUDY_ROOT / "runtime" / "phase_1_logs"
    started = datetime.now(timezone.utc).isoformat()
    conditions: dict[str, dict] = {}
    servers: dict[str, dict] = {}
    for condition in args.conditions:
        print(f"condition: {condition}", flush=True)
        if condition == FRESH_PROCESS_CONDITION:
            outcomes, server_record = run_fresh_process_condition(
                prompts, args.repeats, checkpoint, log_dir
            )
        else:
            outcomes, server_record = run_same_process_condition(
                condition, prompts, args.repeats, checkpoint, log_dir
            )
        conditions[condition] = summarize_condition(condition, outcomes)
        servers[condition] = server_record
        print(
            f"  identity rate: {conditions[condition]['identity_rate']}",
            flush=True,
        )

    report = build_report(
        prompts,
        conditions,
        runtime={
            "model": str(MODEL_PATH),
            "seed": SEED,
            "parallel_slots": 1,
            "speculative_decoding": "none",
            "response_budget": __import__(
                "src.inference.provider", fromlist=["RESPONSE_BUDGET"]
            ).RESPONSE_BUDGET,
            "python": sys.executable,
            "python_version": platform.python_version(),
            "started_at": started,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "by_condition": servers,
        },
    )
    write_report(report, args.output)
    print(f"\nwrote {args.output}")
    for name, summary in report["conditions"].items():
        print(
            f"  {name}: {summary['prompts_reproducing']}/{summary['prompts']} "
            f"prompts reproduced across {summary['generations_per_prompt']} "
            f"generations"
        )
    print(f"  greedy divergence: {report['greedy_divergence_located']}")
    print(f"  sampling hypothesis: {report['sampling_amplifier_hypothesis']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
