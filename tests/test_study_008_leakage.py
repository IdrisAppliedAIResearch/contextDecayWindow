from pathlib import Path

from src.analysis.study_008_leakage import run_leakage_audit


REPO = Path(__file__).resolve().parents[1]


def test_live_retrieval_path_has_no_measurement_leakage():
    audit = run_leakage_audit(REPO)
    assert audit.passed, (
        f"literal={audit.literal_violations}, "
        f"import={audit.import_violations}"
    )


def test_transitive_planted_violation_is_caught_by_both_detectors(tmp_path):
    memory = tmp_path / "src" / "memory"
    memory.mkdir(parents=True)
    root = memory / "retrieval_engine.py"
    helper = memory / "helper.py"
    root.write_text("from src.memory import helper\n", encoding="utf-8")
    helper.write_text(
        'MEASUREMENT_PATH = "q_facts_key.md"\n',
        encoding="utf-8",
    )

    audit = run_leakage_audit(
        tmp_path,
        scan_dirs=(Path("src/memory"),),
        import_roots=(Path("src/memory/retrieval_engine.py"),),
    )

    assert {v.path for v in audit.literal_violations} == {
        "src/memory/helper.py"
    }
    assert {v.path for v in audit.import_violations} == {
        "src/memory/helper.py"
    }
