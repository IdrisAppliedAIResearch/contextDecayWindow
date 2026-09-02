from analysis.da042_analysis import DA042AnalysisError


def test_da042_analysis_error_is_runtime_error() -> None:
    assert issubclass(DA042AnalysisError, RuntimeError)
