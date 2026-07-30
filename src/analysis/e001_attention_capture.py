from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np

from src.retrieval_mechanism_ledger.e001 import (
    assert_mechanism_path_allowed,
    calibration_cases,
    overlapping_token_indices,
    score_retrieval_heads,
)
from src.retrieval_mechanism_ledger.seal import verify_mixed_source_seal


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
RUN_ROOT = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
)
TURN_LOG = RUN_ROOT / "logs" / "turns.jsonl"
PROTOCOL = COMPONENT_ROOT / "E001_attention_term_selection_protocol.md"
MECHANISM_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "e001.py"
CAPTURE_SOURCE = Path(__file__).resolve()
SEAL_SOURCE = REPO_ROOT / "src" / "retrieval_mechanism_ledger" / "seal.py"
EXPECTED_MODEL_REVISION = "6a9e13bd6fc8f0983b9b99948120bc37f49c13e9"
EXPECTED_TRACK1_COMMIT = "15338a4"
PROBE_TURN = 115
HEAD_THRESHOLD = 0.1
SEED = 0


def run_capture(output_dir: Path, model_path: Path, track1_repo: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(f"Refusing to overwrite E001 capture: {output_dir}")
    output_dir.mkdir(parents=True)

    source_paths = [
        PROTOCOL,
        MECHANISM_SOURCE,
        SEAL_SOURCE,
        CAPTURE_SOURCE,
        TURN_LOG,
    ]
    before = _hash_paths(source_paths)
    seal = verify_mixed_source_seal(REPO_ROOT, RUN_ROOT)
    if seal["status"] != "PASS":
        raise RuntimeError("Corrected Tier 6 mechanism seal failed")
    leakage = leakage_audit()
    if leakage["status"] != "PASS":
        raise RuntimeError("E001 capture leakage audit failed")
    track1 = track1_manifest(track1_repo)
    if track1["commit"] != EXPECTED_TRACK1_COMMIT:
        raise RuntimeError("Track 1 reference commit changed")
    if model_path.name != EXPECTED_MODEL_REVISION:
        raise RuntimeError("Pinned Qwen3.6 revision path changed")

    import accelerate
    import bitsandbytes
    import torch
    import transformers
    from transformers import (
        AutoTokenizer,
        BitsAndBytesConfig,
        Qwen3_5ForConditionalGeneration,
    )

    np.random.seed(SEED)
    torch.manual_seed(SEED)
    torch.cuda.manual_seed_all(SEED)
    config = json.loads((model_path / "config.json").read_text(encoding="utf-8"))
    layer_types = config["text_config"]["layer_types"]
    full_layer_ids = [
        index for index, layer_type in enumerate(layer_types)
        if layer_type == "full_attention"
    ]
    if len(full_layer_ids) != 16:
        raise RuntimeError("Pinned model no longer has 16 full-attention layers")

    quantization = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        local_files_only=True,
        trust_remote_code=True,
        use_fast=True,
    )
    model = Qwen3_5ForConditionalGeneration.from_pretrained(
        model_path,
        quantization_config=quantization,
        device_map="cuda:0",
        dtype=torch.bfloat16,
        attn_implementation="eager",
        local_files_only=True,
        trust_remote_code=True,
    )
    model.eval()
    collector = AttentionCollector(model, full_layer_ids)

    cases = calibration_cases()
    first_scores, first_observations, case_rows = calibrate(
        model, tokenizer, collector, cases
    )
    second_scores, second_observations, second_case_rows = calibrate(
        model, tokenizer, collector, cases
    )
    if first_observations != second_observations:
        raise RuntimeError("Calibration observation count changed")
    if not np.array_equal(first_scores, second_scores):
        raise RuntimeError("Calibration head scores changed on rerun")
    if case_rows != second_case_rows:
        raise RuntimeError("Calibration token mappings changed on rerun")

    head_scores = first_scores / first_observations
    retrieval_heads = [
        (layer_slot, head_index)
        for layer_slot in range(head_scores.shape[0])
        for head_index in range(head_scores.shape[1])
        if float(head_scores[layer_slot, head_index]) >= HEAD_THRESHOLD
    ]
    if not retrieval_heads:
        raise RuntimeError("No independently calibrated retrieval head passed")

    query = probe_query()
    q4_attention, tokenization = capture_query(
        model, tokenizer, collector, query
    )
    q4_rerun, tokenization_rerun = capture_query(
        model, tokenizer, collector, query
    )
    if tokenization != tokenization_rerun:
        raise RuntimeError("Q4 tokenization changed on rerun")
    if not np.array_equal(q4_attention, q4_rerun):
        raise RuntimeError("Q4 attention changed on rerun")

    collector.close()
    model_manifest = hash_model_snapshot(model_path)
    after = _hash_paths(source_paths)
    source_status = "PASS" if before == after else "FAIL"
    determinism = {
        "status": "PASS",
        "calibration_score_sha256": _array_sha256(head_scores),
        "q4_attention_sha256": _array_sha256(q4_attention),
        "q4_rerun_sha256": _array_sha256(q4_rerun),
        "retrieval_head_ids_sha256": _json_sha256(retrieval_heads),
    }
    environment = {
        "python": sys.version,
        "platform": platform.platform(),
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "transformers": transformers.__version__,
        "accelerate": accelerate.__version__,
        "bitsandbytes": bitsandbytes.__version__,
        "gpu": torch.cuda.get_device_name(0),
        "gpu_total_bytes": torch.cuda.get_device_properties(0).total_memory,
        "gpu_peak_allocated_bytes": torch.cuda.max_memory_allocated(0),
        "seed": SEED,
        "parallelism": 1,
        "speculative_decoding": False,
    }
    result = {
        "entry": "E001",
        "stage": "attention_capture",
        "status": (
            "PASS"
            if source_status == "PASS"
            and determinism["status"] == "PASS"
            and seal["status"] == "PASS"
            and leakage["status"] == "PASS"
            else "FAIL"
        ),
        "design_commit": "fd880d88",
        "execution_commit": _git("rev-parse", "HEAD"),
        "probe_turn": PROBE_TURN,
        "query": query,
        "model_revision": EXPECTED_MODEL_REVISION,
        "quantization": "bitsandbytes NF4 4-bit double-quant BF16 compute",
        "full_attention_layer_ids": full_layer_ids,
        "heads_per_full_attention_layer": int(head_scores.shape[1]),
        "calibration_case_count": len(cases),
        "calibration_observations": first_observations,
        "retrieval_head_threshold": HEAD_THRESHOLD,
        "retrieval_head_count": len(retrieval_heads),
        "forward_passes": len(cases) * 2 + 2,
        "inference_generation_calls": 0,
        "source_integrity_status": source_status,
        "source_hashes_before": before,
        "source_hashes_after": after,
        "mechanism_seal": seal,
        "leakage_audit": leakage,
        "track1_reference": track1,
        "model_manifest": model_manifest,
        "environment": environment,
        "determinism": determinism,
    }

    np.savez_compressed(
        output_dir / "q4_attention.npz",
        attention=q4_attention,
        full_layer_ids=np.asarray(full_layer_ids, dtype=np.int64),
    )
    _write_json(output_dir / "q4_tokenization.json", tokenization)
    _write_json(output_dir / "calibration_cases.json", case_rows)
    _write_head_scores(
        output_dir / "head_scores.csv",
        head_scores,
        full_layer_ids,
        set(retrieval_heads),
    )
    _write_json(
        output_dir / "retrieval_heads.json",
        {
            "threshold": HEAD_THRESHOLD,
            "heads": [
                {
                    "layer_slot": layer_slot,
                    "model_layer": full_layer_ids[layer_slot],
                    "head": head_index,
                    "score": float(head_scores[layer_slot, head_index]),
                }
                for layer_slot, head_index in retrieval_heads
            ],
        },
    )
    _write_json(output_dir / "capture_manifest.json", result)
    return result


class AttentionCollector:
    def __init__(self, model, full_layer_ids: list[int]) -> None:
        self.weights = {}
        self.handles = []
        layers = model.model.language_model.layers
        for slot, layer_id in enumerate(full_layer_ids):
            module = layers[layer_id].self_attn
            self.handles.append(
                module.register_forward_hook(self._hook(slot))
            )

    def _hook(self, slot: int):
        def capture(_module, _args, output):
            weights = output[1] if isinstance(output, tuple) else None
            if weights is None:
                raise RuntimeError("Eager attention hook returned no weights")
            self.weights[slot] = weights.detach().float().cpu()

        return capture

    def run(self, model, input_ids, attention_mask) -> np.ndarray:
        import torch

        self.weights.clear()
        with torch.inference_mode():
            model(
                input_ids=input_ids,
                attention_mask=attention_mask,
                use_cache=False,
                logits_to_keep=1,
            )
        if sorted(self.weights) != list(range(len(self.handles))):
            raise RuntimeError("Not every full-attention hook fired")
        result = np.stack(
            [self.weights[index][0].numpy() for index in sorted(self.weights)]
        )
        self.weights.clear()
        return result

    def close(self) -> None:
        for handle in self.handles:
            handle.remove()


def calibrate(model, tokenizer, collector, cases):
    totals = None
    observations = 0
    rows = []
    for case in cases:
        encoded = tokenizer(
            case.text,
            add_special_tokens=False,
            return_offsets_mapping=True,
            return_tensors="pt",
        )
        offsets = encoded.pop("offset_mapping")[0].tolist()
        haystack_indices = overlapping_token_indices(
            offsets, start=0, end=case.haystack_end
        )
        needle_indices = overlapping_token_indices(
            offsets,
            start=case.needle_code_start,
            end=case.needle_code_end,
        )
        answer_indices = overlapping_token_indices(
            offsets,
            start=case.answer_code_start,
            end=case.answer_code_end,
        )
        if not needle_indices or not answer_indices:
            raise RuntimeError(f"Ambiguous calibration mapping: {case.case_id}")
        attention = collector.run(
            model,
            encoded["input_ids"].to(model.device),
            encoded["attention_mask"].to(model.device),
        )
        hits, case_observations = score_retrieval_heads(
            attention,
            haystack_indices=haystack_indices,
            answer_indices=answer_indices,
            needle_indices=needle_indices,
        )
        totals = hits if totals is None else totals + hits
        observations += case_observations
        rows.append(
            {
                "case_id": case.case_id,
                "vault": case.vault,
                "code": case.code,
                "needle_position": case.needle_position,
                "text_sha256": hashlib.sha256(
                    case.text.encode("utf-8")
                ).hexdigest(),
                "token_count": len(offsets),
                "haystack_token_count": len(haystack_indices),
                "needle_token_indices": list(needle_indices),
                "answer_token_indices": list(answer_indices),
                "observation_count": case_observations,
            }
        )
    return totals, observations, rows


def capture_query(model, tokenizer, collector, query: str):
    encoded = tokenizer(
        query,
        add_special_tokens=False,
        return_offsets_mapping=True,
        return_tensors="pt",
    )
    offsets = encoded.pop("offset_mapping")[0].tolist()
    input_ids = encoded["input_ids"]
    eos_id = tokenizer.eos_token_id
    if eos_id is None:
        raise RuntimeError("Pinned tokenizer has no EOS token")
    import torch

    input_ids = torch.cat(
        [input_ids, torch.tensor([[eos_id]], dtype=input_ids.dtype)],
        dim=1,
    )
    attention_mask = torch.ones_like(input_ids)
    offsets.append([len(query), len(query)])
    attention = collector.run(
        model,
        input_ids.to(model.device),
        attention_mask.to(model.device),
    )
    tokenization = {
        "query": query,
        "query_sha256": hashlib.sha256(query.encode("utf-8")).hexdigest(),
        "input_ids": input_ids[0].tolist(),
        "tokens": tokenizer.convert_ids_to_tokens(input_ids[0].tolist()),
        "offsets": offsets,
        "query_token_count": input_ids.shape[1] - 1,
        "eos_token_index": input_ids.shape[1] - 1,
    }
    return attention, tokenization


def probe_query() -> str:
    for line in TURN_LOG.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if int(row["turn_number"]) == PROBE_TURN:
            return str(row["user_message"])
    raise RuntimeError("Q4 probe query is absent")


def leakage_audit() -> dict:
    forbidden = {"q_facts_key", "rubric", "atomic_items", "targeted_items"}
    imported = set()
    for source_path in (MECHANISM_SOURCE, CAPTURE_SOURCE):
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.lower() for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.lower())
    forbidden_imports = sorted(
        name for name in imported if any(term in name for term in forbidden)
    )
    planted_rejected = False
    try:
        assert_mechanism_path_allowed("experiments/study_009/q_facts_key.md")
    except ValueError:
        planted_rejected = True
    return {
        "status": (
            "PASS"
            if not forbidden_imports and planted_rejected
            else "FAIL"
        ),
        "forbidden_imports": forbidden_imports,
        "planted_forbidden_path_rejected": planted_rejected,
    }


def track1_manifest(repo: Path) -> dict:
    analyzer = repo / "protected" / "attention" / "analyzer.py"
    return {
        "repository": str(repo.resolve()),
        "commit": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=repo, text=True
        ).strip(),
        "analyzer_sha256": _sha256(analyzer),
        "imported_at_runtime": False,
    }


def hash_model_snapshot(model_path: Path) -> dict:
    files = sorted(
        path
        for path in model_path.iterdir()
        if path.is_file()
    )
    rows = [
        {
            "name": path.name,
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in files
    ]
    return {
        "path": str(model_path.resolve()),
        "revision": EXPECTED_MODEL_REVISION,
        "file_count": len(rows),
        "total_bytes": sum(row["bytes"] for row in rows),
        "files": rows,
        "tree_sha256": _json_sha256(rows),
    }


def _write_head_scores(path, scores, full_layer_ids, selected):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=("layer_slot", "model_layer", "head", "score", "selected"),
            lineterminator="\n",
        )
        writer.writeheader()
        for layer_slot in range(scores.shape[0]):
            for head in range(scores.shape[1]):
                writer.writerow(
                    {
                        "layer_slot": layer_slot,
                        "model_layer": full_layer_ids[layer_slot],
                        "head": head,
                        "score": f"{scores[layer_slot, head]:.17g}",
                        "selected": (layer_slot, head) in selected,
                    }
                )


def _write_json(path: Path, value: object) -> None:
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _hash_paths(paths):
    return {
        str(path.relative_to(REPO_ROOT)).replace("\\", "/"): _sha256(path)
        for path in paths
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _array_sha256(value: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(value).tobytes()).hexdigest()


def _json_sha256(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _git(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=REPO_ROOT, text=True).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--model-path", type=Path, required=True)
    parser.add_argument("--track1-repo", type=Path, required=True)
    args = parser.parse_args()
    result = run_capture(
        args.output_dir,
        args.model_path.resolve(),
        args.track1_repo.resolve(),
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
