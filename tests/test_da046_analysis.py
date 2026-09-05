from analysis.da046_analysis import DA046AnalysisError


def test_da046_analysis_error_is_runtime_error() -> None:
    assert issubclass(DA046AnalysisError, RuntimeError)
