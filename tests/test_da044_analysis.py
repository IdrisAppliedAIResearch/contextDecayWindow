from analysis.da044_analysis import DA044AnalysisError


def test_da044_analysis_error_is_runtime_error() -> None:
    assert issubclass(DA044AnalysisError, RuntimeError)
