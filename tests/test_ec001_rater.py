from __future__ import annotations

from scripts import run_ec001_rater


def _local_client() -> run_ec001_rater.RaterClient:
    return run_ec001_rater.RaterClient(
        {
            "provider": "llama_cpp",
            "seed": 5005,
        },
        "http://127.0.0.1:9999",
    )


def test_local_binary_label_call_uses_exact_grammar(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url: str, payload: dict, headers: dict) -> dict:
        captured.update(payload)
        return {"content": "yes"}

    monkeypatch.setattr(run_ec001_rater, "_post_json", fake_post)

    response = _local_client().complete(
        "label prompt",
        max_tokens=10,
        binary_label=True,
    )

    assert response == "yes"
    assert (
        captured["grammar"]
        == run_ec001_rater.LOCAL_BINARY_LABEL_GRAMMAR
    )


def test_local_rationale_call_has_no_grammar(monkeypatch) -> None:
    captured: dict = {}

    def fake_post(url: str, payload: dict, headers: dict) -> dict:
        captured.update(payload)
        return {"content": "grounded rationale"}

    monkeypatch.setattr(run_ec001_rater, "_post_json", fake_post)

    response = _local_client().complete(
        "rationale prompt",
        max_tokens=160,
    )

    assert response == "grounded rationale"
    assert "grammar" not in captured


def test_openai_binary_call_does_not_add_local_grammar(
    monkeypatch,
) -> None:
    captured: dict = {}

    def fake_post(url: str, payload: dict, headers: dict) -> dict:
        captured.update(payload)
        return {
            "choices": [
                {"message": {"content": "yes"}},
            ]
        }

    monkeypatch.setenv("TEST_OPENAI_KEY", "not-a-real-key")
    monkeypatch.setattr(run_ec001_rater, "_post_json", fake_post)
    client = run_ec001_rater.RaterClient(
        {
            "provider": "openai",
            "api_key_env": "TEST_OPENAI_KEY",
            "base_url": "https://api.openai.test/v1",
            "model_id": "gpt-4o-2024-08-06",
            "seed": 5005,
        },
        None,
    )

    response = client.complete(
        "label prompt",
        max_tokens=10,
        binary_label=True,
    )

    assert response == "yes"
    assert "grammar" not in captured
