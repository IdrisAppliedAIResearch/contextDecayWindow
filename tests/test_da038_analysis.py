from analysis.da038_analysis import DA038AnalysisError


def test_da038_analysis_error_is_runtime_error() -> None:
    assert issubclass(DA038AnalysisError, RuntimeError)
