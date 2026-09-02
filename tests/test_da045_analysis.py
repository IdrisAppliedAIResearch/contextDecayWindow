from analysis.da045_analysis import DA045AnalysisError


def test_da045_analysis_error_is_runtime_error() -> None:
    assert issubclass(DA045AnalysisError, RuntimeError)
