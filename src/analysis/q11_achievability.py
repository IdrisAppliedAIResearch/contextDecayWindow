from __future__ import annotations

import csv
import hashlib
import json
import subprocess
import unicodedata
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Iterable, Sequence

from src.analysis.retrieval_bakeoff_tier6_121 import ATOMIC_ITEMS
from src.memory.context_builder import render_episode_element
from src.memory.context_matched_stm import render_stm_payload


REPO_ROOT = Path(__file__).resolve().parents[2]
COMPONENT_ROOT = (
    REPO_ROOT / "experiments" / "components" / "retrieval_mechanism_ledger"
)
TURN_LOG = (
    REPO_ROOT
    / "experiments"
    / "surveys"
    / "retrieval_bakeoff"
    / "tier6"
    / "runs"
    / "tier6_live_121_corrected_001"
    / "context_matched_stm"
    / "logs"
    / "turns.jsonl"
)
PROTOCOL = COMPONENT_ROOT / "AR_001_Q11_ACHIEVABILITY_PROTOCOL.md"
EXECUTION_SOURCE = REPO_ROOT / "src" / "analysis" / "q11_achievability.py"
RENDERER_SOURCE = REPO_ROOT / "src" / "memory" / "context_builder.py"
ATOMIC_SOURCE = (
    REPO_ROOT / "src" / "analysis" / "retrieval_bakeoff_tier6_121.py"
)

BUDGET_CHARS = 32_000
Q11_TURN = 120
TARGET_FACT_COUNT = 14
EXPECTED_EPISODE_COUNT = 119
EXPECTED_DOMAIN_SIZES = {
    "civil": 5,
    "art": 4,
    "monetary": 4,
    "marine": 4,
}


@dataclass(frozen=True)
class AtomicItem:
    index: int
    domain: str
    item: str
    needle: str

    @property
    def bit(self) -> int:
        return 1 << self.index


@dataclass(frozen=True)
class Episode:
    id: str
    turn_number: int
    user_message: str
    assistant_message: str
    coverage_mask: int
    element_chars: int

    @property
    def additive_chars(self) -> int:
        return self.element_chars + 1

    def as_renderable(self) -> dict:
        return {
            "id": self.id,
            "turn_number": self.turn_number,
            "user_message": self.user_message,
            "assistant_message": self.assistant_message,
        }


@dataclass(frozen=True)
class Solution:
    additive_chars: int
    episode_indexes: tuple[int, ...]


def atomic_items() -> tuple[AtomicItem, ...]:
    return tuple(
        AtomicItem(
            index=index,
            domain=domain,
            item=item,
            needle=normalize(needle),
        )
        for index, (domain, item, needle, _plant_turns) in enumerate(
            ATOMIC_ITEMS
        )
    )


def load_committed_episodes(
    turn_log: Path = TURN_LOG,
    items: Sequence[AtomicItem] | None = None,
) -> tuple[Episode, ...]:
    item_rows = tuple(items or atomic_items())
    rows = [
        json.loads(line)
        for line in turn_log.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    episodes = []
    for row in rows:
        episode_id = row.get("stored_episode_id")
        turn = int(row["turn_number"])
        if not episode_id or turn >= Q11_TURN:
            continue
        renderable = {
            "id": str(episode_id),
            "turn_number": turn,
            "user_message": str(row["user_message"]),
            "assistant_message": str(row["assistant_message"]),
        }
        element = render_episode_element(renderable)
        normalized = normalize(element)
        mask = 0
        for item in item_rows:
            if item.needle in normalized:
                mask |= item.bit
        episodes.append(
            Episode(
                id=str(episode_id),
                turn_number=turn,
                user_message=renderable["user_message"],
                assistant_message=renderable["assistant_message"],
                coverage_mask=mask,
                element_chars=len(element),
            )
        )
    return tuple(sorted(episodes, key=lambda row: (row.turn_number, row.id)))


def exact_solutions(
    episodes: Sequence[Episode],
    target_mask: int,
) -> dict[int, Solution]:
    useful = [
        (index, episode, episode.coverage_mask & target_mask)
        for index, episode in enumerate(episodes)
        if episode.coverage_mask & target_mask
    ]
    solutions: dict[int, Solution] = {0: Solution(0, ())}
    for index, episode, episode_mask in useful:
        prior = tuple(solutions.items())
        for mask, solution in prior:
            combined_mask = mask | episode_mask
            if combined_mask == mask:
                continue
            candidate = Solution(
                additive_chars=(
                    solution.additive_chars + episode.additive_chars
                ),
                episode_indexes=(*solution.episode_indexes, index),
            )
            incumbent = solutions.get(combined_mask)
            if incumbent is None or solution_key(
                candidate, episodes
            ) < solution_key(incumbent, episodes):
                solutions[combined_mask] = candidate
    return solutions


def best_solution(
    solutions: dict[int, Solution],
    episodes: Sequence[Episode],
    *,
    minimum_fact_count: int,
) -> tuple[int, Solution] | None:
    eligible = [
        (mask, solution)
        for mask, solution in solutions.items()
        if mask.bit_count() >= minimum_fact_count
    ]
    if not eligible:
        return None
    return min(
        eligible,
        key=lambda row: (
            exact_payload_cost(row[1], episodes),
            len(row[1].episode_indexes),
            solution_identity(row[1], episodes),
            row[0],
        ),
    )


def greedy_solution(
    episodes: Sequence[Episode],
    target_mask: int,
    *,
    minimum_fact_count: int,
) -> tuple[int, Solution] | None:
    selected: list[int] = []
    selected_set: set[int] = set()
    covered = 0
    while (covered & target_mask).bit_count() < minimum_fact_count:
        candidates = []
        for index, episode in enumerate(episodes):
            if index in selected_set:
                continue
            new_mask = (episode.coverage_mask & target_mask) & ~covered
            new_count = new_mask.bit_count()
            if not new_count:
                continue
            candidates.append(
                (
                    -Fraction(new_count, episode.additive_chars),
                    -new_count,
                    episode.additive_chars,
                    episode.turn_number,
                    episode.id,
                    index,
                )
            )
        if not candidates:
            return None
        index = min(candidates)[-1]
        selected.append(index)
        selected_set.add(index)
        covered |= episodes[index].coverage_mask & target_mask
    selected.sort()
    solution = Solution(
        additive_chars=sum(
            episodes[index].additive_chars for index in selected
        ),
        episode_indexes=tuple(selected),
    )
    return covered, solution


def analyze() -> dict:
    _assert_tracked(TURN_LOG)
    items = atomic_items()
    episodes = load_committed_episodes(items=items)
    _validate_inventory(episodes, items)

    all_mask = (1 << len(items)) - 1
    solutions = exact_solutions(episodes, all_mask)
    exact = best_solution(
        solutions,
        episodes,
        minimum_fact_count=TARGET_FACT_COUNT,
    )
    greedy = greedy_solution(
        episodes,
        all_mask,
        minimum_fact_count=TARGET_FACT_COUNT,
    )
    if exact is None:
        raise AssertionError("No exact solution reaches the Q11 threshold")
    if greedy is None:
        raise AssertionError("Greedy did not reach the Q11 threshold")

    exact_mask, exact_solution = exact
    greedy_mask, greedy_result = greedy
    exact_record = solution_record(exact_mask, exact_solution, episodes, items)
    greedy_record = solution_record(
        greedy_mask,
        greedy_result,
        episodes,
        items,
    )
    if greedy_record["serialized_chars"] < exact_record["serialized_chars"]:
        raise AssertionError("Greedy beat the purported exact optimum")

    frontier = exact_frontier(solutions, episodes, len(items))
    domain_results = {}
    for domain, expected_size in EXPECTED_DOMAIN_SIZES.items():
        domain_mask = mask_for_domain(items, domain)
        if domain_mask.bit_count() != expected_size:
            raise AssertionError(f"Unexpected {domain} item count")
        domain_solutions = exact_solutions(episodes, domain_mask)
        domain_best = best_solution(
            domain_solutions,
            episodes,
            minimum_fact_count=expected_size,
        )
        if domain_best is None:
            raise AssertionError(f"No complete {domain} solution")
        mask, solution = domain_best
        domain_results[domain] = solution_record(
            mask & domain_mask,
            solution,
            episodes,
            items,
            objective_mask=domain_mask,
        )

    store_mask = 0
    for episode in episodes:
        store_mask |= episode.coverage_mask
    missing_items = item_records(all_mask & ~store_mask, items)
    if missing_items:
        status = "STORE_INCOMPLETE"
    elif exact_record["serialized_chars"] <= BUDGET_CHARS:
        status = "ACHIEVABLE_AT_32K"
    else:
        status = "UNREACHABLE_AT_32K"

    return {
        "analysis": "AR-001",
        "status": status,
        "budget_chars": BUDGET_CHARS,
        "target_fact_count": TARGET_FACT_COUNT,
        "eligible_episode_count": len(episodes),
        "coverage_episode_count": sum(
            bool(episode.coverage_mask) for episode in episodes
        ),
        "store_fact_count": store_mask.bit_count(),
        "missing_store_items": missing_items,
        "exact_optimum": exact_record,
        "greedy_upper_bound": greedy_record,
        "greedy_overhead_chars": (
            greedy_record["serialized_chars"]
            - exact_record["serialized_chars"]
        ),
        "domain_optima": domain_results,
        "frontier": frontier,
        "source_hashes": source_hashes(),
        "design_commit": _last_commit(PROTOCOL),
        "execution_commit": _head_commit(),
        "interpretation": (
            "Offline availability and exact serialized cost only. "
            "E002's registered outcome is unchanged."
        ),
    }


def exact_frontier(
    solutions: dict[int, Solution],
    episodes: Sequence[Episode],
    item_count: int,
) -> list[dict]:
    rows = []
    for fact_count in range(item_count + 1):
        candidates = [
            (mask, solution)
            for mask, solution in solutions.items()
            if mask.bit_count() == fact_count
        ]
        if not candidates:
            rows.append(
                {
                    "fact_count": fact_count,
                    "serialized_chars": "",
                    "episode_count": "",
                    "coverage_mask": "",
                }
            )
            continue
        mask, solution = min(
            candidates,
            key=lambda row: (
                exact_payload_cost(row[1], episodes),
                len(row[1].episode_indexes),
                solution_identity(row[1], episodes),
                row[0],
            ),
        )
        rows.append(
            {
                "fact_count": fact_count,
                "serialized_chars": exact_payload_cost(solution, episodes),
                "episode_count": len(solution.episode_indexes),
                "coverage_mask": f"{mask:017b}",
            }
        )
    return rows


def solution_record(
    mask: int,
    solution: Solution,
    episodes: Sequence[Episode],
    items: Sequence[AtomicItem],
    *,
    objective_mask: int | None = None,
) -> dict:
    selected = [episodes[index] for index in solution.episode_indexes]
    payload = render_stm_payload(
        [],
        [episode.as_renderable() for episode in selected],
    )
    serialized_chars = len(payload)
    if serialized_chars != exact_payload_cost(solution, episodes):
        raise AssertionError("Additive and rendered payload costs differ")
    payload_mask = coverage_mask(payload, items)
    objective = (
        ((1 << len(items)) - 1)
        if objective_mask is None
        else objective_mask
    )
    if payload_mask & objective != mask:
        raise AssertionError("Rendered payload coverage differs from mask union")
    selected_rows = []
    for episode in selected:
        selected_rows.append(
            {
                "episode_id": episode.id,
                "source_turn": episode.turn_number,
                "element_chars": episode.element_chars,
                "additive_chars": episode.additive_chars,
                "items": item_records(episode.coverage_mask, items),
            }
        )
    return {
        "fact_count": mask.bit_count(),
        "payload_fact_count": payload_mask.bit_count(),
        "serialized_chars": serialized_chars,
        "budget_headroom_chars": BUDGET_CHARS - serialized_chars,
        "episode_count": len(selected),
        "coverage_mask": f"{mask:017b}",
        "covered_items": item_records(payload_mask, items),
        "objective_items": item_records(mask, items),
        "omitted_items": item_records(
            ((1 << len(items)) - 1) & ~payload_mask,
            items,
        ),
        "selected_episodes": selected_rows,
        "selected_ids": [episode.id for episode in selected],
        "selected_source_turns": [
            episode.turn_number for episode in selected
        ],
        "payload_sha256": hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        "payload": payload,
    }


def coverage_mask(text: str, items: Sequence[AtomicItem]) -> int:
    normalized = normalize(text)
    mask = 0
    for item in items:
        if item.needle in normalized:
            mask |= item.bit
    return mask


def mask_for_domain(items: Sequence[AtomicItem], domain: str) -> int:
    mask = 0
    for item in items:
        if item.domain == domain:
            mask |= item.bit
    return mask


def item_records(mask: int, items: Sequence[AtomicItem]) -> list[dict]:
    return [
        {"domain": item.domain, "item": item.item}
        for item in items
        if mask & item.bit
    ]


def exact_payload_cost(
    solution: Solution,
    episodes: Sequence[Episode],
) -> int:
    if not solution.episode_indexes:
        return len(render_stm_payload([], []))
    return nonempty_fixed_cost() + solution.additive_chars


def nonempty_fixed_cost() -> int:
    dummy = {
        "id": "dummy",
        "turn_number": 0,
        "user_message": "",
        "assistant_message": "",
    }
    element = render_episode_element(dummy)
    return len(render_stm_payload([], [dummy])) - (len(element) + 1)


def solution_key(
    solution: Solution,
    episodes: Sequence[Episode],
) -> tuple:
    return (
        solution.additive_chars,
        len(solution.episode_indexes),
        solution_identity(solution, episodes),
    )


def solution_identity(
    solution: Solution,
    episodes: Sequence[Episode],
) -> tuple[tuple[int, str], ...]:
    return tuple(
        (episodes[index].turn_number, episodes[index].id)
        for index in solution.episode_indexes
    )


def normalize(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(
        character
        for character in decomposed
        if not unicodedata.combining(character)
    ).lower()


def write_outputs(output_dir: Path) -> dict:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(
            f"Refusing to overwrite AR-001 output: {output_dir}"
        )
    first = analyze()
    second = analyze()
    if canonical_json(first) != canonical_json(second):
        raise AssertionError("AR-001 in-memory rerun was not deterministic")

    output_dir.mkdir(parents=True)
    public_result = without_payloads(first)
    _write_json(output_dir / "achievability.json", public_result)
    _write_csv(
        output_dir / "exact_frontier.csv",
        first["frontier"],
        (
            "fact_count",
            "serialized_chars",
            "episode_count",
            "coverage_mask",
        ),
    )
    episodes = load_committed_episodes()
    items = atomic_items()
    coverage_rows = []
    for episode in episodes:
        covered = item_records(episode.coverage_mask, items)
        coverage_rows.append(
            {
                "episode_id": episode.id,
                "source_turn": episode.turn_number,
                "element_chars": episode.element_chars,
                "additive_chars": episode.additive_chars,
                "fact_count": episode.coverage_mask.bit_count(),
                "domains": "|".join(
                    sorted({row["domain"] for row in covered})
                ),
                "items": "|".join(row["item"] for row in covered),
            }
        )
    _write_csv(
        output_dir / "episode_coverage.csv",
        coverage_rows,
        (
            "episode_id",
            "source_turn",
            "element_chars",
            "additive_chars",
            "fact_count",
            "domains",
            "items",
        ),
    )
    (output_dir / "global_optimum_payload.txt").write_text(
        first["exact_optimum"]["payload"],
        encoding="utf-8",
        newline="\n",
    )
    _write_report(output_dir / "AR_001_report.md", first)

    artifact_hashes = {
        path.name: sha256(path)
        for path in sorted(output_dir.iterdir())
        if path.is_file()
    }
    determinism = {
        "status": "PASS",
        "in_memory_result_sha256": hashlib.sha256(
            canonical_json(first).encode("utf-8")
        ).hexdigest(),
        "rerun_result_sha256": hashlib.sha256(
            canonical_json(second).encode("utf-8")
        ).hexdigest(),
    }
    _write_json(output_dir / "determinism.json", determinism)
    artifact_hashes["determinism.json"] = sha256(
        output_dir / "determinism.json"
    )
    _write_json(
        output_dir / "artifact_manifest.json",
        {
            "analysis": "AR-001",
            "design_commit": first["design_commit"],
            "execution_commit": first["execution_commit"],
            "source_hashes": first["source_hashes"],
            "artifact_hashes": artifact_hashes,
        },
    )
    return public_result


def without_payloads(result: dict) -> dict:
    value = json.loads(canonical_json(result))
    value["exact_optimum"].pop("payload")
    value["greedy_upper_bound"].pop("payload")
    for record in value["domain_optima"].values():
        record.pop("payload")
    return value


def source_hashes() -> dict[str, str]:
    return {
        str(path.relative_to(REPO_ROOT)).replace("\\", "/"): sha256(path)
        for path in (
            TURN_LOG,
            PROTOCOL,
            EXECUTION_SOURCE,
            RENDERER_SOURCE,
            ATOMIC_SOURCE,
        )
    }


def canonical_json(value: object) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _validate_inventory(
    episodes: Sequence[Episode],
    items: Sequence[AtomicItem],
) -> None:
    if len(episodes) != EXPECTED_EPISODE_COUNT:
        raise AssertionError(
            f"Expected {EXPECTED_EPISODE_COUNT} eligible episodes, "
            f"found {len(episodes)}"
        )
    if len(items) != 17 or len({item.needle for item in items}) != 17:
        raise AssertionError("Expected 17 unique Q11 atomic needles")
    domain_sizes = {
        domain: sum(item.domain == domain for item in items)
        for domain in EXPECTED_DOMAIN_SIZES
    }
    if domain_sizes != EXPECTED_DOMAIN_SIZES:
        raise AssertionError("Q11 domain sizes differ from 5/4/4/4")
    if len({episode.id for episode in episodes}) != len(episodes):
        raise AssertionError("Eligible episode IDs are not unique")


def _assert_tracked(path: Path) -> None:
    relative = path.relative_to(REPO_ROOT).as_posix()
    subprocess.run(
        ["git", "ls-files", "--error-unmatch", relative],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
    )


def _last_commit(path: Path) -> str:
    relative = path.relative_to(REPO_ROOT).as_posix()
    return subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", relative],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


def _head_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip()


def _write_json(path: Path, value: object) -> None:
    path.write_text(canonical_json(value), encoding="utf-8", newline="\n")


def _write_csv(
    path: Path,
    rows: Iterable[dict],
    fields: Sequence[str],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, result: dict) -> None:
    exact = result["exact_optimum"]
    greedy = result["greedy_upper_bound"]
    domain_lines = []
    for domain in EXPECTED_DOMAIN_SIZES:
        record = result["domain_optima"][domain]
        domain_lines.append(
            f"| {domain} | {record['fact_count']}/"
            f"{EXPECTED_DOMAIN_SIZES[domain]} | "
            f"{record['serialized_chars']:,} | "
            f"{record['episode_count']} | "
            f"{', '.join(str(turn) for turn in record['selected_source_turns'])} |"
        )
    episode_lines = []
    for episode in exact["selected_episodes"]:
        item_text = "; ".join(
            f"{row['domain']}:{row['item']}" for row in episode["items"]
        )
        episode_lines.append(
            f"| {episode['source_turn']} | `{episode['episode_id']}` | "
            f"{episode['element_chars']:,} | {item_text} |"
        )
    omitted = ", ".join(
        f"{row['domain']}:{row['item']}" for row in exact["omitted_items"]
    )
    status_text = (
        "The 14/17 bar exists within the enforced budget."
        if result["status"] == "ACHIEVABLE_AT_32K"
        else "The 14/17 bar does not fit within the enforced budget."
    )
    text = "\n".join(
        (
            "# AR-001 Q11 Achievability Audit",
            "",
            f"**Design commit:** `{result['design_commit']}`",
            f"**Execution commit:** `{result['execution_commit']}`",
            f"**Status:** **{result['status']}**",
            "",
            "## Result",
            "",
            f"The exact minimum for at least 14/17 Q11 items is "
            f"**{exact['serialized_chars']:,} characters** across "
            f"**{exact['episode_count']} episodes**, leaving "
            f"**{exact['budget_headroom_chars']:,} characters** of headroom "
            f"against 32,000. {status_text}",
            "",
            f"Greedy reached {greedy['fact_count']}/17 at "
            f"{greedy['serialized_chars']:,} characters, "
            f"{result['greedy_overhead_chars']:,} above the exact optimum.",
            "",
            f"Omitted by the exact threshold optimum: {omitted or 'none'}.",
            "",
            "## Domain Optima",
            "",
            "| Domain | Facts | Minimum payload chars | Episodes | Turns |",
            "|---|---:|---:|---:|---|",
            *domain_lines,
            "",
            "Domain optima are independent and non-additive because wrappers "
            "and episodes can overlap.",
            "",
            "## Exact Threshold Set",
            "",
            "| Turn | Episode | Element chars | Q11 items present |",
            "|---:|---|---:|---|",
            *episode_lines,
            "",
            "## Integrity",
            "",
            f"- Eligible committed episodes: {result['eligible_episode_count']}.",
            f"- Episodes containing at least one Q11 item: "
            f"{result['coverage_episode_count']}.",
            f"- Store coverage: {result['store_fact_count']}/17; missing: "
            f"{len(result['missing_store_items'])}.",
            "- Exact additive cost equals the complete rendered payload length.",
            "- Dynamic programming is covered by a synthetic exhaustive-subset test.",
            "- In-memory deterministic rerun: PASS.",
            "- No model, embedding, retrieval, local database, or inference call.",
            "",
            "## Interpretation Boundary",
            "",
            "This audit determines bar achievability only. It does not change "
            "E002's registered KILL or establish that a deployable retriever can "
            "find the optimum set without answer-key access.",
            "",
        )
    )
    path.write_text(text, encoding="utf-8", newline="\n")
