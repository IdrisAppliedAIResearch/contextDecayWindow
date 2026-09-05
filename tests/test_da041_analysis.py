from analysis.da041_analysis import DA041AnalysisError


def test_da041_analysis_error_is_runtime_error() -> None:
    assert issubclass(DA041AnalysisError, RuntimeError)
