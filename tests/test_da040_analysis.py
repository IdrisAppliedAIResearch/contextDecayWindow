from analysis.da040_analysis import DA040AnalysisError


def test_da040_analysis_error_is_runtime_error() -> None:
    assert issubclass(DA040AnalysisError, RuntimeError)
