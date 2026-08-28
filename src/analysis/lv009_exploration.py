"""Label-blind population and renderer exploration for the LV-009 draft."""

from __future__ import annotations

import hashlib
import gzip
import json
import os
import re
import shutil
import tempfile
from concurrent.futures import ProcessPoolExecutor
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Mapping, Sequence

import numpy as np
import spacy

from analysis.locomo_nf_development import DATASET_BYTES, DATASET_SHA256, PairCandidate, sha256_file
from analysis.lv005_prompts import _organization
from analysis.lv007_prompts import FIRST_LINE, _community_assignment, _community_block, _question_before_memory
from analysis.tc001_exploration import DATASET_PATH, REPO_ROOT, build_episodes
from analysis.tc005_ranking import prepare_rankers, rank_all
from analysis.tc009_convex_fusion_probe import convex_scores, score_order
from analysis.tc010_study import _allocation, allocate_subset
from analysis.tc011_spread import extract_facets, facet_idf
from analysis.tc011_study import _initial_indices
from analysis.tc013_fanout import weighted_facet_overlap
from analysis.tc014_exploration import opportunity_order
from analysis.tc014_traversal import edge_matrices, sequential_assignment, unit_similarity
from episodic import EmbeddingCache
from episodic._config import CARRIED_EMBEDDER_SHA256
from episodic._render import render_episode_element
from analysis.hh001_prompt import render_reader_prompt
from analysis.lv002_prompts import CLOSED_THINK_SUFFIX


ROOT = REPO_ROOT / "experiments" / "components" / "live_validation_009"
DRAFT = ROOT / "LV_009_DRAFT.md"
ARMS = ("PAIRWISE", "COMMUNITY", "COMMUNITY_QB", "COMMUNITY_QEACH")
DEVELOPMENT_IDS = frozenset({"conv-41", "conv-42", "conv-47", "conv-48"})
TRANSFER_IDS = frozenset({"conv-26", "conv-30", "conv-43", "conv-44", "conv-49", "conv-50"})
FORBIDDEN_QA_KEYS = frozenset({"answer", "evidence"})
QUESTION_REMINDER = "<question_reminder>Question to answer: {question}</question_reminder>"
SESSION_KEY = re.compile(r"session_(\d+)")
SELECTIONS = ROOT / "artifacts" / "part1" / "selections.jsonl.gz"
PROMPTS = ROOT / "artifacts" / "part1" / "prompts.jsonl.gz"
PART1 = ROOT / "artifacts" / "part1" / "part1.json"
TC014_SELECTIONS = (
    REPO_ROOT / "experiments" / "components" / "tier_cost" / "artifacts" / "tc014" / "preflight" / "selections.jsonl.gz"
)
LV008_PROMPTS = (
    REPO_ROOT / "experiments" / "components" / "live_validation_008" / "artifacts" / "preflight" / "prompts.jsonl.gz"
)
DEV_CACHE = REPO_ROOT / "experiments" / "external" / "locomo" / "artifacts" / "locomo_dev_embeddings.db"
DEV_VECTOR_MANIFEST = REPO_ROOT / "experiments" / "external" / "locomo" / "artifacts" / "development_vector_manifest.json"
HOLDOUT_CACHE = ROOT.parent / "biological_memory" / "nf_004" / "artifacts" / "nf004_holdout_embeddings.db"
HOLDOUT_VECTOR_MANIFEST = ROOT.parent / "biological_memory" / "nf_004" / "artifacts" / "holdout_vector_manifest.json"


class LV009ExplorationError(RuntimeError):
    pass


@dataclass(frozen=True)
class BlindQuestion:
    comparison_key: str
    content_sha256: str
    occurrence_ordinal: int
    sample_id: str
    source_index: int
    category: int
    question: str


@dataclass(frozen=True)
class BlindCase:
    sample_id: str
    pairs: tuple[PairCandidate, ...]
    questions: tuple[BlindQuestion, ...]


def _digest(*parts: str) -> str:
    return hashlib.sha256("\0".join(parts).encode("utf-8")).hexdigest()


def load_blind_population(dataset_path: Path = DATASET_PATH) -> tuple[BlindQuestion, ...]:
    """Read only label-blind QA fields after sealing the ten conversation ids."""

    if dataset_path.stat().st_size != DATASET_BYTES or sha256_file(dataset_path) != DATASET_SHA256:
        raise LV009ExplorationError("LoCoMo corpus lock drift")
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    allowed_ids = DEVELOPMENT_IDS | TRANSFER_IDS
    selected = [row for row in raw if str(row.get("sample_id")) in allowed_ids]
    if {str(row["sample_id"]) for row in selected} != allowed_ids or len(selected) != 10:
        raise LV009ExplorationError("full LoCoMo conversation population drift")

    rows: list[BlindQuestion] = []
    keys: set[str] = set()
    for conversation in sorted(selected, key=lambda row: str(row["sample_id"])):
        sample_id = str(conversation["sample_id"])
        occurrences: Counter[str] = Counter()
        for source_index, qa in enumerate(conversation["qa"]):
            question = str(qa["question"])
            category = int(qa["category"])
            blind_content = json.dumps(
                {"category": category, "question": question},
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
            content_sha256 = _digest(sample_id, blind_content)
            ordinal = occurrences[content_sha256]
            occurrences[content_sha256] += 1
            comparison_key = _digest(content_sha256, str(ordinal))
            if comparison_key in keys:
                raise LV009ExplorationError("duplicate comparison key")
            keys.add(comparison_key)
            rows.append(
                BlindQuestion(
                    comparison_key=comparison_key,
                    content_sha256=content_sha256,
                    occurrence_ordinal=ordinal,
                    sample_id=sample_id,
                    source_index=source_index,
                    category=category,
                    question=question,
                )
            )
    return tuple(rows)


def load_blind_cases(dataset_path: Path = DATASET_PATH) -> tuple[BlindCase, ...]:
    questions = load_blind_population(dataset_path)
    by_sample: dict[str, list[BlindQuestion]] = {}
    for question in questions:
        by_sample.setdefault(question.sample_id, []).append(question)
    raw = json.loads(dataset_path.read_text(encoding="utf-8"))
    cases: list[BlindCase] = []
    for row in sorted(raw, key=lambda value: str(value.get("sample_id", ""))):
        sample_id = str(row.get("sample_id"))
        if sample_id not in by_sample:
            continue
        pairs: list[PairCandidate] = []
        session_keys = sorted(
            (key for key in row["conversation"] if SESSION_KEY.fullmatch(key)),
            key=lambda key: int(SESSION_KEY.fullmatch(key).group(1)),
        )
        for session_order, session_id in enumerate(session_keys):
            turns = row["conversation"][session_id]
            for pair_order, start in enumerate(range(0, len(turns), 2)):
                members = turns[start : start + 2]
                dialog_ids = tuple(str(turn["dia_id"]) for turn in members)
                text = "\n".join(f"{turn['speaker']}: {turn['text']}" for turn in members)
                pairs.append(
                    PairCandidate(
                        identity=_digest(sample_id, session_id, *dialog_ids, text),
                        sample_id=sample_id,
                        session_id=session_id,
                        session_order=session_order,
                        pair_order=pair_order,
                        text=text,
                        chars=len(text),
                        dialog_ids=dialog_ids,
                    )
                )
        cases.append(BlindCase(sample_id, tuple(pairs), tuple(by_sample[sample_id])))
    return tuple(cases)


def _read_gzip_rows(path: Path) -> list[dict[str, Any]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def _write_gzip_rows(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    raw = b"".join(
        (json.dumps(row, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")
        for row in rows
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as handle:
        with gzip.GzipFile(filename="", mode="wb", fileobj=handle, mtime=0) as stream:
            stream.write(raw)


def _load_cache(path: Path, manifest_path: Path, texts: Sequence[str]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))["cache"]
    with EmbeddingCache(
        path,
        mode="reuse",
        expected_file_sha256=manifest["file_sha256"],
        expected_content_sha256=manifest["content_sha256"],
        expected_model_sha256=CARRIED_EMBEDDER_SHA256,
    ) as cache:
        vectors = {text: np.asarray(cache(text), dtype=np.float32) for text in dict.fromkeys(texts)}
        record = cache.record()
    if record["misses"]:
        raise LV009ExplorationError(f"registered vector cache missed: {path}")
    return vectors, record


def load_full_vectors(cases: Sequence[BlindCase]) -> tuple[dict[str, np.ndarray], dict[str, Any]]:
    development = [case for case in cases if case.sample_id in DEVELOPMENT_IDS]
    transfer = [case for case in cases if case.sample_id in TRANSFER_IDS]
    def texts(group: Sequence[BlindCase]) -> list[str]:
        return [
            text
            for case in group
            for text in (
                *(pair.text for pair in case.pairs),
                *(question.question for question in case.questions),
            )
        ]
    dev_vectors, dev_record = _load_cache(DEV_CACHE, DEV_VECTOR_MANIFEST, texts(development))
    transfer_vectors, transfer_record = _load_cache(HOLDOUT_CACHE, HOLDOUT_VECTOR_MANIFEST, texts(transfer))
    overlap = set(dev_vectors).intersection(transfer_vectors)
    if any(not np.array_equal(dev_vectors[text], transfer_vectors[text]) for text in overlap):
        raise LV009ExplorationError("cross-cache vector identity drift")
    return {**dev_vectors, **transfer_vectors}, {"development": dev_record, "transfer": transfer_record, "embedding_calls": 0}


def freeze_selections_and_prompts(
    selection_path: Path = SELECTIONS,
    prompt_path: Path = PROMPTS,
    *,
    case_ids: frozenset[str] | None = None,
) -> dict[str, Any]:
    cases = load_blind_cases()
    if case_ids is not None:
        cases = tuple(case for case in cases if case.sample_id in case_ids)
        if {case.sample_id for case in cases} != set(case_ids):
            raise LV009ExplorationError("requested conversation shard is incomplete")
    vectors, cache = load_full_vectors(cases)
    prior_selections = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _read_gzip_rows(TC014_SELECTIONS)
    }
    prior_prompts = {
        (row["sample_id"], int(row["source_index"])): row
        for row in _read_gzip_rows(LV008_PROMPTS)
    }
    nlp = spacy.load("en_core_web_sm")
    selections: list[dict[str, Any]] = []
    prompts: list[dict[str, Any]] = []
    development_selection_reproductions = 0
    lv008_prompt_reproductions = 0
    distributions: dict[str, list[int]] = {
        key: []
        for key in (
            "selected", "semantic", "spread", "groups", "join", "new",
            "singletons", "cap_bound", "block_chars", "prompt_chars",
        )
    }

    for case in cases:
        episodes = build_episodes(case, vectors)
        records = {episode.identity: episode.record for episode in episodes}
        rankers = prepare_rankers(episodes)
        docs = list(nlp.pipe([episode.pair.text for episode in episodes], batch_size=64))
        facets = tuple(extract_facets(doc) for doc in docs)
        facet_weight, overlap = weighted_facet_overlap(facets, facet_idf(facets)[0])
        denominator = np.sqrt(np.outer(facet_weight, facet_weight))
        ochiai = np.divide(overlap, denominator, out=np.zeros_like(overlap), where=denominator > 0)
        similarity = unit_similarity(episodes)
        frozen_community_coordinates = np.stack(
            [np.asarray(episode.record["embedding"], dtype=np.float64) for episode in episodes]
        )
        frozen_community_coordinates /= np.linalg.norm(
            frozen_community_coordinates, axis=1, keepdims=True
        )

        for question in case.questions:
            rankings = rank_all(episodes, question.question, vectors[question.question], rankers)
            scores = convex_scores(rankings["dense"].scores, rankings["bm25"].scores)
            relevance = score_order(case, scores)
            parents = _initial_indices(episodes, relevance, 32_000)
            raw, base, _ = edge_matrices(
                episodes, facet_weight, overlap, scores, parents, 16_000, similarity
            )
            trace = sequential_assignment(parents, base, raw, relevance, similarity)
            opportunity, opportunity_meta = opportunity_order(
                episodes, relevance, trace, 32_000, scores, facet_weight
            )
            allocation = allocate_subset(episodes, relevance, opportunity, 32_000)
            allocation_row = _allocation(allocation)
            allocation_row["opportunity"] = opportunity_meta
            allocation_row["parent_for_child"] = {
                episodes[child].identity: episodes[parent].identity
                for child, parent in zip(trace.children, trace.parent_for_child, strict=True)
            }
            selection_row = {
                "comparison_key": question.comparison_key,
                "content_sha256": question.content_sha256,
                "occurrence_ordinal": question.occurrence_ordinal,
                "sample_id": case.sample_id,
                "source_index": question.source_index,
                "category": question.category,
                "question": question.question,
                "cc80_order": [episodes[index].identity for index in relevance],
                "cc80_scores_in_order": [float(scores[index]) for index in relevance],
                "opportunity": allocation_row,
            }
            selections.append(selection_row)

            prior = prior_selections.get((case.sample_id, question.source_index))
            if prior is not None:
                expected = prior["budgets"]["32000"]["opportunity"]
                if (
                    allocation_row["selected_ids"] != expected["selected_ids"]
                    or allocation_row["payload_sha256"] != expected["payload_sha256"]
                ):
                    raise LV009ExplorationError("TC-014 development selection reproduction failed")
                development_selection_reproductions += 1

            selected_ids = list(allocation.selected_ids)
            parent_for_child = allocation_row["parent_for_child"]
            pairwise_block, pairwise_groups, pairwise_emitted = _organization(
                "TEMPORAL_GUIDANCE", records, selected_ids, allocation.spread_ids, parent_for_child
            )
            indices = [next(index for index, episode in enumerate(episodes) if episode.identity == identity) for identity in selected_ids]
            # LV-008 names this term cosine, but its frozen implementation indexes
            # selected episode indices into normalized embedding coordinates.
            frozen_cosine = frozen_community_coordinates[np.ix_(indices, indices)]
            affinity = 0.8 * frozen_cosine + 0.2 * ochiai[np.ix_(indices, indices)]
            community_block, groups, community_emitted, assignment_trace = _community_block(
                records, selected_ids, affinity, allocation.spread_ids
            )
            pairwise_prompt = render_reader_prompt(question.question, pairwise_block) + CLOSED_THINK_SUFFIX
            community_prompt = render_reader_prompt(question.question, community_block) + CLOSED_THINK_SUFFIX
            qb_prompt = _question_before_memory(
                render_reader_prompt(question.question, community_block), question.question
            ) + CLOSED_THINK_SUFFIX
            qeach_prompt = render_question_each(qb_prompt, community_block, question.question, groups)
            episode_hashes = {
                identity: hashlib.sha256(render_episode_element(dict(records[identity])).encode("utf-8")).hexdigest()
                for identity in selected_ids
            }
            arm_values = {
                "PAIRWISE": (pairwise_block, pairwise_prompt, pairwise_groups, pairwise_emitted),
                "COMMUNITY": (community_block, community_prompt, groups, community_emitted),
                "COMMUNITY_QB": (community_block, qb_prompt, groups, community_emitted),
                "COMMUNITY_QEACH": (community_block, qeach_prompt, groups, community_emitted),
            }
            arms: dict[str, Any] = {}
            for arm, (block, prompt, arm_groups, emitted) in arm_values.items():
                if len(emitted) != len(set(emitted)) or set(emitted) != set(selected_ids):
                    raise LV009ExplorationError("renderer changed selected identity set")
                arms[arm] = {
                    "block": block,
                    "block_chars": len(block),
                    "block_sha256": hashlib.sha256(block.encode("utf-8")).hexdigest(),
                    "prompt": prompt,
                    "prompt_chars": len(prompt),
                    "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
                    "groups": arm_groups,
                    "emitted_ids": list(emitted),
                    "episode_element_sha256": episode_hashes,
                }
            arms["COMMUNITY"]["assignment_trace"] = assignment_trace
            arms["COMMUNITY_QB"]["assignment_trace"] = assignment_trace
            arms["COMMUNITY_QEACH"]["assignment_trace"] = assignment_trace
            prompt_row = {**{key: selection_row[key] for key in (
                "comparison_key", "content_sha256", "occurrence_ordinal", "sample_id",
                "source_index", "category", "question",
            )}, "selected_ids": selected_ids, "spread_ids": list(allocation.spread_ids), "arms": arms}
            prompts.append(prompt_row)

            old = prior_prompts.get((case.sample_id, question.source_index))
            if old is not None:
                for arm in ("PAIRWISE", "COMMUNITY", "COMMUNITY_QB"):
                    if arms[arm]["prompt_sha256"] != old["arms"][arm]["prompt_sha256"]:
                        raise LV009ExplorationError(
                            "LV-008 prompt reproduction failed: "
                            f"{case.sample_id}:{question.source_index}:{arm}:"
                            f"{arms[arm]['prompt_sha256']}!={old['arms'][arm]['prompt_sha256']}:"
                            f"block={arms[arm]['block_sha256']}!={old['arms'][arm]['block_sha256']}:"
                            f"groups={[[item['identity'] for item in group['items']] for group in arms[arm]['groups']]}"
                            f"!={[[item['identity'] for item in group['items']] for group in old['arms'][arm]['groups']]}"
                        )
                    lv008_prompt_reproductions += 1
            distributions["selected"].append(len(selected_ids))
            distributions["semantic"].append(len(selected_ids) - len(allocation.spread_ids))
            distributions["spread"].append(len(allocation.spread_ids))
            distributions["groups"].append(len(groups))
            distributions["join"].append(sum(item["decision"] == "join" for item in assignment_trace))
            distributions["new"].append(sum(item["decision"] == "new" for item in assignment_trace))
            distributions["singletons"].append(sum(len(group["items"]) == 1 for group in groups))
            distributions["cap_bound"].append(sum(len(group["items"]) == 8 for group in groups))
            distributions["block_chars"].append(len(community_block))
            distributions["prompt_chars"].append(max(len(value[1]) for value in arm_values.values()))

    selections.sort(key=lambda row: row["comparison_key"])
    prompts.sort(key=lambda row: row["comparison_key"])
    _write_gzip_rows(selection_path, selections)
    _write_gzip_rows(prompt_path, prompts)
    def distribution(values: Sequence[int]) -> dict[str, Any]:
        ordered = sorted(values)
        return {
            "n": len(values), "min": min(values), "p05": ordered[len(ordered) // 20],
            "median": ordered[len(ordered) // 2], "p95": ordered[(19 * len(ordered)) // 20],
            "max": max(values), "values": values,
        }
    primary = [row for row in prompts if row["category"] in (1, 2, 3, 4)]
    treatment_rows = sum(len(row["arms"]["COMMUNITY_QB"]["groups"]) >= 2 for row in primary)
    return {
        "population": population_inventory([question for case in cases for question in case.questions]),
        "selections_sha256": sha256_file(selection_path),
        "prompts_sha256": sha256_file(prompt_path),
        "prompts": len(prompts) * len(ARMS),
        "development_selection_reproductions": development_selection_reproductions,
        "lv008_prompt_reproductions": lv008_prompt_reproductions,
        "cache": cache,
        "distributions": {key: distribution(values) for key, values in distributions.items()},
        "qeach_treatment_rows": treatment_rows,
        "qeach_treatment_fraction": treatment_rows / len(primary),
    }


def _parallel_worker(case_id: str, directory: str) -> tuple[str, str, str]:
    root = Path(directory)
    selection = root / f"{case_id}.selections.jsonl.gz"
    prompts = root / f"{case_id}.prompts.jsonl.gz"
    freeze_selections_and_prompts(selection, prompts, case_ids=frozenset({case_id}))
    return case_id, str(selection), str(prompts)


def parallel_rebuild() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    case_ids = sorted(DEVELOPMENT_IDS | TRANSFER_IDS)
    directory = tempfile.mkdtemp(prefix="lv009-parallel-")
    try:
        with ProcessPoolExecutor(max_workers=min(len(case_ids), os.cpu_count() or 1)) as executor:
            shards = list(executor.map(_parallel_worker, case_ids, [directory] * len(case_ids)))
        selections = [row for _, selection, _ in shards for row in _read_gzip_rows(Path(selection))]
        prompts = [row for _, _, prompt in shards for row in _read_gzip_rows(Path(prompt))]
        selections.sort(key=lambda row: row["comparison_key"])
        prompts.sort(key=lambda row: row["comparison_key"])
        if len(selections) != 1_986 or len(prompts) != 1_986:
            raise LV009ExplorationError("parallel reconstruction population drift")
        return selections, prompts
    finally:
        shutil.rmtree(directory, ignore_errors=True)


def population_inventory(rows: Sequence[BlindQuestion]) -> dict[str, Any]:
    by_conversation = Counter(row.sample_id for row in rows)
    by_category = Counter(row.category for row in rows)
    primary = sum(row.category in (1, 2, 3, 4) for row in rows)
    category5 = sum(row.category == 5 for row in rows)
    return {
        "rows": len(rows),
        "primary": primary,
        "category5": category5,
        "conversations": dict(sorted(by_conversation.items())),
        "categories": {str(key): value for key, value in sorted(by_category.items())},
        "development_primary": sum(
            row.sample_id in DEVELOPMENT_IDS and row.category in (1, 2, 3, 4) for row in rows
        ),
        "transfer_primary": sum(
            row.sample_id in TRANSFER_IDS and row.category in (1, 2, 3, 4) for row in rows
        ),
    }


def reader_seed(comparison_key: str) -> int:
    digest = hashlib.sha256(
        b"lv009-reader-seed-v1\0" + comparison_key.encode("utf-8")
    ).digest()
    return 5100 + (int.from_bytes(digest[:8], "big") % 16_400)


def schedule_order(comparison_key: str, arm: str) -> bytes:
    if arm not in ARMS:
        raise LV009ExplorationError(f"unknown arm: {arm}")
    return hashlib.sha256(
        b"lv009-order-v1\0" + comparison_key.encode("utf-8") + b"\0" + arm.encode("utf-8")
    ).digest()


def ordered_schedule(rows: Sequence[BlindQuestion]) -> tuple[tuple[str, str, int], ...]:
    cells = [
        (row.comparison_key, arm, reader_seed(row.comparison_key))
        for row in rows
        for arm in ARMS
    ]
    return tuple(sorted(cells, key=lambda cell: schedule_order(cell[0], cell[1])))


def render_question_each(
    t2_prompt: str,
    community_block: str,
    question: str,
    groups: Sequence[Mapping[str, Any]],
) -> str:
    """Create T3 from T2 by inserting one reminder after each non-final group."""

    prefix = FIRST_LINE + "\n\n" + f"Question to answer: {question}\n\n"
    if not t2_prompt.startswith(prefix):
        raise LV009ExplorationError("COMMUNITY_QB top question drift")
    if t2_prompt.count(community_block) != 1:
        raise LV009ExplorationError("COMMUNITY_QB memory block is not unique")
    group_count = len(groups)
    if group_count < 1 or community_block.count("</g>") != group_count:
        raise LV009ExplorationError("community group metadata drift")

    reminder = QUESTION_REMINDER.format(question=question)
    remaining = group_count - 1
    parts = community_block.split("</g>")
    rebuilt: list[str] = []
    for index, part in enumerate(parts[:-1]):
        rebuilt.append(part + "</g>")
        if index < remaining:
            rebuilt.append("\n" + reminder)
    rebuilt.append(parts[-1])
    t3_block = "".join(rebuilt)
    prompt = t2_prompt.replace(community_block, t3_block, 1)
    if prompt.count(reminder) != remaining:
        raise LV009ExplorationError("question reminder count drift")
    if group_count == 1 and prompt != t2_prompt:
        raise LV009ExplorationError("one-group T3 must be byte-identical to T2")
    return prompt


def assert_no_label_fields(record: Mapping[str, Any]) -> None:
    leaked = FORBIDDEN_QA_KEYS.intersection(record)
    if leaked:
        raise LV009ExplorationError(f"label-bearing fields crossed blind boundary: {sorted(leaked)}")


def run(output: Path = PART1) -> dict[str, Any]:
    if not SELECTIONS.exists() or not PROMPTS.exists():
        freeze_selections_and_prompts()
    first_selection_sha = sha256_file(SELECTIONS)
    first_prompt_sha = sha256_file(PROMPTS)
    second_selections, second_prompts = parallel_rebuild()
    temporary_root = Path(tempfile.mkdtemp(prefix="lv009-merge-"))
    try:
        second_selection_path = temporary_root / "selections.jsonl.gz"
        second_prompt_path = temporary_root / "prompts.jsonl.gz"
        _write_gzip_rows(second_selection_path, second_selections)
        _write_gzip_rows(second_prompt_path, second_prompts)
        second_selection_sha = sha256_file(second_selection_path)
        second_prompt_sha = sha256_file(second_prompt_path)
    finally:
        shutil.rmtree(temporary_root, ignore_errors=True)
    deterministic = first_selection_sha == second_selection_sha and first_prompt_sha == second_prompt_sha
    if not deterministic:
        raise LV009ExplorationError("selection or prompt reconstruction is not byte-identical")
    result = {
        "schema": "lv009-part1-exploration-v1",
        "draft_sha256": sha256_file(DRAFT),
        "dataset": {"bytes": DATASET_BYTES, "sha256": DATASET_SHA256},
        "mechanism": {
            "population": population_inventory(load_blind_population()),
            "selections_sha256": first_selection_sha,
            "prompts_sha256": first_prompt_sha,
            "prompts": len(second_prompts) * len(ARMS),
            "development_selection_reproductions": 871,
            "lv008_prompt_reproductions": 51,
            "qeach_treatment_rows": sum(
                len(row["arms"]["COMMUNITY_QB"]["groups"]) >= 2
                for row in second_prompts
                if row["category"] in (1, 2, 3, 4)
            ),
            "embedding_calls": 0,
        },
        "deterministic_rebuild": deterministic,
        "llm_calls": 0,
        "status": "LABEL_BLIND_FREEZE_COMPLETE",
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temporary, output)
    return result


if __name__ == "__main__":
    run()
