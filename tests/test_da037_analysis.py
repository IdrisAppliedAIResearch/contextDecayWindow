from analysis.da037_analysis import DA037AnalysisError


def test_da037_analysis_error_is_runtime_error() -> None:
    assert issubclass(DA037AnalysisError, RuntimeError)
