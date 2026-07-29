from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SURVEY_ROOT = REPO_ROOT / "experiments" / "surveys" / "retrieval_bakeoff"
QUERY_ROOT = SURVEY_ROOT / "holdout"
CACHE_ROOT = SURVEY_ROOT / "cache"

DEFAULT_BUDGET = 32_000
EMBEDDING_DIMENSION = 1_024
CARRIED_EMBEDDING_SHA256 = (
    "06507c7b42688469c4e7298b0a1e16deff06caf291cf0a5b278c308249c3e439"
)
RRF_CONSTANT = 60
BM25_K1 = 1.2
BM25_B = 0.75
SEED = 5005


@dataclass(frozen=True)
class CorpusSpec:
    corpus_id: str
    database_path: Path
    eligible_turn_min: int
    eligible_turn_max: int
    query_manifest: Path
    domain_labels: tuple[str, ...]
    has_distilled_ltm: bool
    advancement_primary: bool
    run_directory: Path


_C121_L_RUN = (
    REPO_ROOT
    / "experiments"
    / "study_007"
    / "runs"
    / "study_007_full_001"
    / "condition_c"
)
_C121_S_RUN = (
    REPO_ROOT
    / "experiments"
    / "study_009"
    / "runs"
    / "study_009_full_001"
    / "arm_s"
)
_C1000_L_RUN = (
    REPO_ROOT
    / "experiments"
    / "study_010"
    / "runs"
    / "study_010_full_001"
    / "arm_l"
)
_C1000_S_RUN = (
    REPO_ROOT
    / "experiments"
    / "study_010"
    / "runs"
    / "study_010_full_001"
    / "arm_s"
)

_DOMAINS_121 = (
    "civil engineering",
    "renaissance art",
    "monetary policy",
    "marine biology",
)
_DOMAINS_1000 = (
    "structural engineering",
    "clinical epidemiology",
    "archival history",
    "battery chemistry",
    "monetary economics",
    "observational astronomy",
    "wetland ecology",
    "applied cryptography",
    "marine geophysics",
    "historical linguistics",
    "field robotics",
    "materials conservation",
)


CORPORA: dict[str, CorpusSpec] = {
    "c121_l": CorpusSpec(
        corpus_id="c121_l",
        database_path=_C121_L_RUN / "study.db",
        eligible_turn_min=1,
        eligible_turn_max=111,
        query_manifest=QUERY_ROOT / "queries_121.json",
        domain_labels=_DOMAINS_121,
        has_distilled_ltm=True,
        advancement_primary=True,
        run_directory=_C121_L_RUN,
    ),
    "c121_s": CorpusSpec(
        corpus_id="c121_s",
        database_path=_C121_S_RUN / "study.db",
        eligible_turn_min=1,
        eligible_turn_max=111,
        query_manifest=QUERY_ROOT / "queries_121.json",
        domain_labels=_DOMAINS_121,
        has_distilled_ltm=False,
        advancement_primary=False,
        run_directory=_C121_S_RUN,
    ),
    "c1000_l": CorpusSpec(
        corpus_id="c1000_l",
        database_path=_C1000_L_RUN / "study.db",
        eligible_turn_min=1,
        eligible_turn_max=986,
        query_manifest=QUERY_ROOT / "queries_1000.json",
        domain_labels=_DOMAINS_1000,
        has_distilled_ltm=True,
        advancement_primary=True,
        run_directory=_C1000_L_RUN,
    ),
    "c1000_s": CorpusSpec(
        corpus_id="c1000_s",
        database_path=_C1000_S_RUN / "study.db",
        eligible_turn_min=1,
        eligible_turn_max=986,
        query_manifest=QUERY_ROOT / "queries_1000.json",
        domain_labels=_DOMAINS_1000,
        has_distilled_ltm=False,
        advancement_primary=False,
        run_directory=_C1000_S_RUN,
    ),
}


def corpus_spec(corpus_id: str) -> CorpusSpec:
    try:
        return CORPORA[corpus_id]
    except KeyError as exc:
        choices = ", ".join(sorted(CORPORA))
        raise ValueError(f"Unknown corpus {corpus_id!r}; choose one of {choices}") from exc
