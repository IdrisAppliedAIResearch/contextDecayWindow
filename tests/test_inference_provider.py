import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dataclasses import dataclass

from src.inference.provider import InferenceProvider, InferenceResult


@dataclass
class MockResult:
    assistant_message: str
    tokens_per_second: float
    time_to_first_token: float
    output_tokens: int


class TestInferenceResult:

    def test_all_fields_populated(self):
        result = InferenceResult(
            assistant_message="Hello",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=4,
        )
        assert result.assistant_message == "Hello"
        assert result.tokens_per_second == 50.0
        assert result.time_to_first_token == 0.02
        assert result.output_tokens == 4

    def test_is_dataclass(self):
        result = InferenceResult(
            assistant_message="Test",
            tokens_per_second=1.0,
            time_to_first_token=0.1,
            output_tokens=1,
        )
        assert hasattr(result, "__dataclass_fields__")

    def test_fields_are_correct_types(self):
        result = InferenceResult(
            assistant_message="Test",
            tokens_per_second=45.5,
            time_to_first_token=0.05,
            output_tokens=10,
        )
        assert isinstance(result.assistant_message, str)
        assert isinstance(result.tokens_per_second, float)
        assert isinstance(result.time_to_first_token, float)
        assert isinstance(result.output_tokens, int)

    def test_mock_compatible(self):
        mock = MockResult(
            assistant_message="Mock",
            tokens_per_second=50.0,
            time_to_first_token=0.02,
            output_tokens=4,
        )
        assert mock.assistant_message == "Mock"
        assert mock.tokens_per_second == 50.0
        assert mock.time_to_first_token == 0.02
        assert mock.output_tokens == 4


class TestInferenceProviderEnvCheck:

    def test_server_request_disables_reasoning_output(self, monkeypatch):
        class FakeResponse:
            def read(self):
                return b'{"content": "ok", "tokens_predicted": 1}'

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        captured = {}

        def fake_urlopen(request, timeout):
            captured["payload"] = json.loads(request.data.decode("utf-8"))
            return FakeResponse()

        monkeypatch.setattr("src.inference.provider.urlopen", fake_urlopen)
        provider = object.__new__(InferenceProvider)
        provider._server_url = "http://127.0.0.1:8000"

        response = provider._complete_server("Test prompt")

        assert response["content"] == "ok"
        assert captured["payload"]["reasoning_format"] == "none"
        assert captured["payload"]["prompt"].endswith("<think>\n</think>\n")

    def test_server_url_bypasses_local_model_path_requirement(self):
        saved_url = os.environ.get("CDW_INFERENCE_SERVER_URL")
        saved_path = os.environ.pop("CDW_INFERENCE_MODEL_PATH", None)
        os.environ["CDW_INFERENCE_SERVER_URL"] = "http://127.0.0.1:8000"
        from src.inference.provider import InferenceProvider
        InferenceProvider._instance = None
        try:
            provider = InferenceProvider()
            assert provider._server_url == "http://127.0.0.1:8000"
        finally:
            if saved_path is not None:
                os.environ["CDW_INFERENCE_MODEL_PATH"] = saved_path
            if saved_url is None:
                os.environ.pop("CDW_INFERENCE_SERVER_URL", None)
            else:
                os.environ["CDW_INFERENCE_SERVER_URL"] = saved_url
            InferenceProvider._instance = None

    def test_raises_when_model_path_not_set(self):
        saved = os.environ.pop("CDW_INFERENCE_MODEL_PATH", None)
        try:
            from src.inference.provider import InferenceProvider
            InferenceProvider._instance = None
            try:
                InferenceProvider()
                assert False, "Should have raised EnvironmentError"
            except EnvironmentError as e:
                assert "CDW_INFERENCE_MODEL_PATH" in str(e)
        finally:
            if saved is not None:
                os.environ["CDW_INFERENCE_MODEL_PATH"] = saved
            InferenceProvider._instance = None

    def test_raises_when_model_path_not_a_file(self):
        os.environ["CDW_INFERENCE_MODEL_PATH"] = "/nonexistent/path/to/model.gguf"
        from src.inference.provider import InferenceProvider
        InferenceProvider._instance = None
        try:
            InferenceProvider()
            assert False, "Should have raised FileNotFoundError"
        except FileNotFoundError as e:
            assert "Inference model not found" in str(e)
        finally:
            InferenceProvider._instance = None
