"""Run EC-002's registered A0 replay gate or A1 K-first counterfactual."""

from __future__ import annotations

import argparse
import hashlib
import json
import shlex
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "episodic" / "src"))

from episodic import EpisodeStore, EpisodicConfig  # noqa: E402
from episodic._embedding import EMBEDDING_DIMENSION  # noqa: E402
from src.analysis.ec001_longmemeval import (  # noqa: E402
    aggregate_tier1,
    load_adaptation_record,
    load_longmemeval,
    parse_delivered_block,
    score_retrieval,
    session_cosine_ranking,
    sha256_file,
)
from src.analysis.ec002_k_first_packing import (  # noqa: E402
    EC002Error,
    build_k_first_context,
    check_reproduction_row,
    compare_score_rows,
    evaluate_reproduction,
    normalized_report,
)
from src.retrieval_bakeoff.embedding import CarriedEmbedder  # noqa: E402

REGISTRATION_SHA = "8c75d7e2"
REQUIRED_BRANCH = "ec/002-k-first-packing"
DEFAULT_ORIGINAL_RUN = (
    REPO / "experiments" / "external" / "longmemeval" / "runs" / "tier1_001"
)
CACHE_COMMIT_INTERVAL = 256


class PersistentSoloEmbedder:
    """Persist exact solo-call vectors so A1 reuses A0's values byte-for-byte."""

    def __init__(
        self,
        delegate,
        path: Path,
        *,
        mode: str,
    ) -> None:
        if mode not in {"populate", "reuse"}:
            raise EC002Error(f"Unknown embedding-cache mode: {mode}")
        self._delegate = delegate
        self.path = path.resolve()
        self.mode = mode
        self.hits = 0
        self.misses = 0
        self._closed = False

        if mode == "populate":
            if self.path.exists():
                raise EC002Error(
                    f"Refusing to overwrite embedding cache: {self.path}"
                )
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.path))
            self._conn.execute("PRAGMA synchronous=FULL")
            self._conn.execute("PRAGMA journal_mode=DELETE")
            self._conn.executescript(
                """
                CREATE TABLE cache (
                    text TEXT PRIMARY KEY,
                    embedding BLOB NOT NULL
                );
                CREATE TABLE metadata (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );
                """
            )
            self._conn.executemany(
                "INSERT INTO metadata (key, value) VALUES (?, ?)",
                (
                    ("model_sha256", self.model_sha256),
                    ("call_shape", "solo"),
                    ("dtype", "float32"),
                    ("dimension", str(EMBEDDING_DIMENSION)),
                ),
            )
            self._conn.commit()
        else:
            if not self.path.is_file():
                raise EC002Error(
                    f"Registered embedding cache is missing: {self.path}"
                )
            uri = f"file:{self.path.as_posix()}?mode=ro"
            self._conn = sqlite3.connect(uri, uri=True)
            metadata = dict(
                self._conn.execute(
                    "SELECT key, value FROM metadata"
                ).fetchall()
            )
            expected = {
                "model_sha256": self.model_sha256,
                "call_shape": "solo",
                "dtype": "float32",
                "dimension": str(EMBEDDING_DIMENSION),
            }
            if metadata != expected:
                raise EC002Error(
                    f"Embedding cache metadata differs: {metadata}"
                )

    @property
    def model_sha256(self) -> str:
        return str(self._delegate.model_sha256)

    @property
    def cache_size(self) -> int:
        return int(
            self._conn.execute("SELECT COUNT(*) FROM cache").fetchone()[0]
        )

    def __call__(self, text: str) -> np.ndarray:
        row = self._conn.execute(
            "SELECT embedding FROM cache WHERE text = ?", (text,)
        ).fetchone()
        if row is not None:
            self.hits += 1
            vector = np.frombuffer(row[0], dtype=np.float32).copy()
            return vector.reshape(EMBEDDING_DIMENSION)
        if self.mode == "reuse":
            raise EC002Error(
                "A1 requested text absent from the committed A0 embedding "
                "cache; no new model call is allowed"
            )
        vector = np.asarray(
            self._delegate(text), dtype=np.float32
        ).reshape(EMBEDDING_DIMENSION)
        self._conn.execute(
            "INSERT INTO cache (text, embedding) VALUES (?, ?)",
            (text, vector.tobytes()),
        )
        self.misses += 1
        if self.misses % CACHE_COMMIT_INTERVAL == 0:
            self._conn.commit()
        return vector

    def close(self) -> None:
        if self._closed:
            return
        if self.mode == "populate":
            self._conn.commit()
        self._conn.close()
        self._closed = True

    def __enter__(self):
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=REPO,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout.strip()


def repository_gate() -> dict:
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if branch != REQUIRED_BRANCH:
        raise EC002Error(
            f"EC-002 must run on {REQUIRED_BRANCH}, found {branch}"
        )
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", REGISTRATION_SHA, "HEAD"],
        cwd=REPO,
        check=False,
    ).returncode:
        raise EC002Error("EC-002 registration is not an ancestor of HEAD")
    status = _git("status", "--porcelain")
    if status:
        raise EC002Error(f"EC-002 refuses a dirty worktree:\n{status}")
    return {
        "branch": branch,
        "head": _git("rev-parse", "HEAD"),
        "registration_sha": _git("rev-parse", REGISTRATION_SHA),
        "worktree_clean": True,
    }


def read_jsonl(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8", newline="\n") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text(
        "".join(
            json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n"
            for row in rows
        ),
        encoding="utf-8",
        newline="\n",
    )


def load_original(run_dir: Path) -> dict:
    paths = {
        "scores": run_dir / "tier1_scores.jsonl",
        "summary": run_dir / "tier1_summary.json",
        "mechanism": run_dir / "SEALED_MECHANISM_DO_NOT_OPEN.jsonl",
        "integrity": run_dir / "source_integrity.json",
    }
    missing = [str(path) for path in paths.values() if not path.is_file()]
    if missing:
        raise EC002Error(f"Original EC-001 artifacts missing: {missing}")
    integrity = json.loads(paths["integrity"].read_text(encoding="utf-8"))
    expected = {
        "scores": integrity["scores_sha256"],
        "mechanism": integrity["sealed_mechanism_sha256"],
    }
    for name, expected_hash in expected.items():
        observed = sha256_file(paths[name])
        if observed != expected_hash:
            raise EC002Error(
                f"Original {name} hash drifted: {observed} != {expected_hash}"
            )
    return {
        "paths": paths,
        "scores": read_jsonl(paths["scores"]),
        "summary": json.loads(paths["summary"].read_text(encoding="utf-8")),
        "mechanisms": read_jsonl(paths["mechanism"]),
        "integrity": integrity,
    }


def committed_gate(path: Path) -> dict:
    if not path.is_file():
        raise EC002Error(f"A0 gate artifact does not exist: {path}")
    relative = path.resolve().relative_to(REPO.resolve()).as_posix()
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", "--", relative],
        cwd=REPO,
        check=True,
        capture_output=True,
    )
    if _git("status", "--porcelain", "--", relative):
        raise EC002Error("A0 gate artifact is dirty")
    gate_commit = _git("log", "-1", "--format=%H", "--", relative)
    if not gate_commit:
        raise EC002Error("A0 gate artifact has no commit")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", gate_commit, "HEAD"],
        cwd=REPO,
        check=False,
    ).returncode:
        raise EC002Error("A0 gate commit is not an ancestor of HEAD")
    gate = json.loads(path.read_text(encoding="utf-8"))
    if gate.get("status") != "PASS":
        raise EC002Error("A0 reproduction gate did not pass")
    if gate.get("registration_sha") != _git("rev-parse", REGISTRATION_SHA):
        raise EC002Error("A0 gate registration anchor differs")
    cache = gate.get("embedding_cache")
    if not isinstance(cache, dict):
        raise EC002Error("A0 gate does not record its embedding cache")
    return {
        "path": relative,
        "sha256": sha256_file(path),
        "commit": gate_commit,
        "embedding_cache": cache,
    }


def build_store(bundle, path: Path, embedder, config: EpisodicConfig):
    store = EpisodeStore(path, config=config, embedder=embedder)
    for episode in bundle.mechanism.episodes:
        store.append("user", episode.user_message)
        store.append("assistant", episode.assistant_message)
    return store


def run_reproduction(
    *,
    dataset,
    original: dict,
    embedder,
    config: EpisodicConfig,
    budget: int,
    output: Path,
) -> dict:
    original_scores = {
        str(row["question_id"]): row for row in original["scores"]
    }
    original_mechanisms = {
        str(row["question_id"]): row for row in original["mechanisms"]
    }
    checks: list[dict] = []
    reproduced_scores: list[dict] = []
    started = time.time()

    with tempfile.TemporaryDirectory(prefix="ec002-a0-") as temporary:
        stores = Path(temporary)
        for index, bundle in enumerate(dataset.instances, 1):
            question_id = bundle.mechanism.question_id
            with build_store(
                bundle,
                stores / f"{question_id}.db",
                embedder,
                config,
            ) as store:
                block, report = store.context(
                    bundle.mechanism.question, budget
                )
            delivered = parse_delivered_block(block)
            ranking = session_cosine_ranking(
                bundle.mechanism, bundle.measurement, embedder
            )
            score = {
                "question_id": question_id,
                "question_type": bundle.measurement.question_type,
                "stratum": bundle.measurement.stratum,
                **score_retrieval(
                    bundle.measurement, delivered, ranking
                ),
            }
            reproduced_scores.append(score)
            checks.append(
                check_reproduction_row(
                    original_score=original_scores[question_id],
                    original_mechanism=original_mechanisms[question_id],
                    reproduced_score=score,
                    reproduced_block=block,
                    reproduced_report=report,
                )
            )
            _progress(index, len(dataset.instances), started)

    summary = aggregate_tier1(reproduced_scores)
    gate = evaluate_reproduction(
        checks=checks,
        reproduced_summary=summary,
        original_summary=original["summary"],
    )
    gate["registration_sha"] = _git("rev-parse", REGISTRATION_SHA)
    write_jsonl(output / "a0_reproduction_checks.jsonl", checks)
    write_json(output / "a0_reproduction_gate.json", gate)
    write_json(output / "a0_reproduced_summary.json", summary)
    return gate


def run_counterfactual(
    *,
    dataset,
    original: dict,
    embedder,
    config: EpisodicConfig,
    budget: int,
    output: Path,
) -> dict:
    treatment_scores: list[dict] = []
    treatment_mechanisms: list[dict] = []
    started = time.time()

    with tempfile.TemporaryDirectory(prefix="ec002-a1-") as temporary:
        stores = Path(temporary)
        for index, bundle in enumerate(dataset.instances, 1):
            question_id = bundle.mechanism.question_id
            with build_store(
                bundle,
                stores / f"{question_id}.db",
                embedder,
                config,
            ) as store:
                episodes = store._all_episodes()
                query = embedder(bundle.mechanism.question)
                block, report, diagnostics = build_k_first_context(
                    episodes=episodes,
                    query_embedding=query,
                    budget=budget,
                    config=config,
                )
                rerun_block, rerun_report, rerun_diagnostics = (
                    build_k_first_context(
                        episodes=episodes,
                        query_embedding=query,
                        budget=budget,
                        config=config,
                    )
                )
            if block != rerun_block:
                raise EC002Error(
                    f"{question_id}: K-first byte-identical rerun failed"
                )
            if normalized_report(report) != normalized_report(rerun_report):
                raise EC002Error(
                    f"{question_id}: K-first report rerun drifted"
                )
            if diagnostics != rerun_diagnostics:
                raise EC002Error(
                    f"{question_id}: K-first diagnostics rerun drifted"
                )

            delivered = parse_delivered_block(block)
            ranking = session_cosine_ranking(
                bundle.mechanism, bundle.measurement, embedder
            )
            score = {
                "question_id": question_id,
                "question_type": bundle.measurement.question_type,
                "stratum": bundle.measurement.stratum,
                **score_retrieval(
                    bundle.measurement, delivered, ranking
                ),
            }
            treatment_scores.append(score)
            treatment_mechanisms.append(
                {
                    "question_id": question_id,
                    "block": block,
                    "block_sha256": hashlib.sha256(
                        block.encode("utf-8")
                    ).hexdigest(),
                    "report": asdict(report),
                    "delivered_turn_numbers": sorted(delivered),
                    "session_cosine_ranking": ranking,
                    "packing_diagnostics": diagnostics,
                    "determinism_rerun": "PASS",
                }
            )
            _progress(index, len(dataset.instances), started)

    summary = aggregate_tier1(treatment_scores)
    comparison = compare_score_rows(
        baseline_rows=original["scores"],
        treatment_rows=treatment_scores,
        treatment_mechanisms=treatment_mechanisms,
    )
    write_jsonl(output / "a1_scores.jsonl", treatment_scores)
    write_jsonl(output / "a1_mechanism.jsonl", treatment_mechanisms)
    write_json(output / "a1_summary.json", summary)
    write_json(output / "paired_comparison.json", comparison)
    return comparison


def _progress(index: int, total: int, started: float) -> None:
    if index % 10 == 0 or index == total:
        elapsed = time.time() - started
        print(
            f"{index:3d}/{total} questions; {elapsed / index:.2f}s/question",
            flush=True,
        )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--mode", choices=("reproduce", "counterfactual"), required=True
    )
    parser.add_argument("--data", type=Path, required=True)
    parser.add_argument("--embedding-model", type=Path, required=True)
    parser.add_argument("--embedding-cache", type=Path, required=True)
    parser.add_argument(
        "--original-run", type=Path, default=DEFAULT_ORIGINAL_RUN
    )
    parser.add_argument("--gate", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    script_before = sha256_file(script_path)
    repository = repository_gate()
    if args.output.exists():
        raise FileExistsError(f"Refusing to overwrite output: {args.output}")
    if args.mode == "counterfactual" and args.gate is None:
        raise EC002Error("Counterfactual mode requires --gate")
    gate_record = (
        committed_gate(args.gate)
        if args.mode == "counterfactual"
        else None
    )

    record = load_adaptation_record()
    benchmark = record["benchmark"]
    if args.data.stat().st_size != int(benchmark["dataset_bytes"]):
        raise EC002Error("Dataset byte size differs from EC-001 pin")
    dataset = load_longmemeval(
        args.data,
        expected_sha256=str(benchmark["dataset_sha256"]),
    )
    original = load_original(args.original_run)

    config = EpisodicConfig()
    decisions = record["decisions"]
    budget = int(decisions["budget"]["budget_chars"])
    if budget != 32_000:
        raise EC002Error("Registered budget is not 32,000 characters")

    carried = CarriedEmbedder(args.embedding_model)
    carried.assert_carried_model()
    if args.mode == "counterfactual":
        registered_cache = gate_record["embedding_cache"]
        if args.embedding_cache.resolve() != Path(
            registered_cache["path"]
        ).resolve():
            raise EC002Error("A1 cache path differs from the A0 gate")
        observed_cache_sha = sha256_file(args.embedding_cache)
        if observed_cache_sha != registered_cache["sha256"]:
            raise EC002Error("A1 embedding cache hash differs from A0")

    args.output.mkdir(parents=True)
    started = time.time()
    with PersistentSoloEmbedder(
        carried,
        args.embedding_cache,
        mode=("populate" if args.mode == "reproduce" else "reuse"),
    ) as embedder:
        if args.mode == "reproduce":
            result = run_reproduction(
                dataset=dataset,
                original=original,
                embedder=embedder,
                config=config,
                budget=budget,
                output=args.output,
            )
        else:
            result = run_counterfactual(
                dataset=dataset,
                original=original,
                embedder=embedder,
                config=config,
                budget=budget,
                output=args.output,
            )
        cache_entries = embedder.cache_size
        cache_hits = embedder.hits
        cache_misses = embedder.misses

    cache_record = {
        "path": str(args.embedding_cache.resolve()),
        "bytes": args.embedding_cache.stat().st_size,
        "sha256": sha256_file(args.embedding_cache),
        "entries": cache_entries,
        "hits": cache_hits,
        "misses": cache_misses,
        "call_shape": "solo",
    }
    if args.mode == "counterfactual":
        if cache_misses != 0:
            raise EC002Error("A1 made a new embedding call")
        if cache_record["sha256"] != gate_record["embedding_cache"]["sha256"]:
            raise EC002Error("Read-only A1 changed the embedding cache")
    else:
        gate_path = args.output / "a0_reproduction_gate.json"
        gate_payload = json.loads(gate_path.read_text(encoding="utf-8"))
        gate_payload["embedding_cache"] = cache_record
        write_json(gate_path, gate_payload)
        result = gate_payload

    script_after = sha256_file(script_path)
    if script_after != script_before:
        raise EC002Error("Runner changed during replay")
    if sha256_file(args.data) != dataset.source_sha256:
        raise EC002Error("Dataset changed during replay")

    integrity = {
        "status": "PASS",
        "mode": args.mode,
        "registration_sha": repository["registration_sha"],
        "dataset_sha256": dataset.source_sha256,
        "embedding_model_sha256": embedder.model_sha256,
        "script_sha256_before": script_before,
        "script_sha256_after": script_after,
        "original_scores_sha256": sha256_file(
            original["paths"]["scores"]
        ),
        "original_mechanism_sha256": sha256_file(
            original["paths"]["mechanism"]
        ),
        "original_summary_sha256": sha256_file(
            original["paths"]["summary"]
        ),
        "a0_gate": gate_record,
        "embedding_cache": cache_record,
    }
    write_json(args.output / "source_integrity.json", integrity)
    write_json(
        args.output / "run_header.json",
        {
            "record": f"EC-002 {args.mode}",
            **repository,
            "launch_command": shlex.join(sys.argv),
            "parallel": 1,
            "seed": config.seed,
            "speculative_decoding": False,
            "inference_server": None,
            "server_build_hash": None,
            "question_count": len(dataset.instances),
            "budget_chars": budget,
            "episodic_config": json.loads(config.to_json()),
            "packing_order": (
                "recency, K, A3 coverage"
                if args.mode == "reproduce"
                else "K, recency, A3 coverage"
            ),
            "started_utc": datetime.fromtimestamp(
                started, timezone.utc
            ).isoformat(),
            "finished_utc": datetime.now(timezone.utc).isoformat(),
            "elapsed_seconds": round(time.time() - started, 3),
            "embedding_cache_entries": cache_entries,
            "embedding_cache": cache_record,
            "result_status": result.get("status"),
        },
    )
    print(f"EC-002 {args.mode}: {result.get('status', 'COMPLETE')}")
    if args.mode == "reproduce" and result["status"] != "PASS":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
