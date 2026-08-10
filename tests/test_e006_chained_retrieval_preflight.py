from __future__ import annotations

from src.analysis.e006_chained_retrieval_preflight import (
    DESIGN_SHA256,
    content_sha256,
    disabled_chain_control,
    load_authoritative_packer,
    sha256_file,
)


def _episode(identifier: str, turn: int) -> dict:
    return {
        "id": identifier,
        "turn_number": turn,
        "user_message": f"user {identifier}",
        "assistant_message": f"assistant {identifier}",
    }


def test_design_anchor_digest_is_locked() -> None:
    from src.analysis.e006_chained_retrieval_preflight import DESIGN

    assert sha256_file(DESIGN) == DESIGN_SHA256


def test_content_key_ignores_generated_episode_id() -> None:
    first = _episode("generated-a", 4)
    second = {**first, "id": "generated-b"}

    assert content_sha256(first) == content_sha256(second)


def test_content_key_changes_with_source_content() -> None:
    first = _episode("same-id", 4)
    second = {**first, "assistant_message": "changed"}

    assert content_sha256(first) != content_sha256(second)


def test_authoritative_packer_is_loaded_without_public_package_imports() -> None:
    pack = load_authoritative_packer()
    candidate = _episode("episode", 1)

    packed = pack([], [candidate], 32_000)

    assert packed.selected_ids == ("episode",)
    assert packed.payload.startswith("<recent_context/>")


def test_disabled_chain_control_is_structurally_not_single_shot() -> None:
    pack = load_authoritative_packer()
    ranked = [_episode(str(index), index) for index in range(1, 13)]

    single = pack([], ranked[:3], 32_000)
    beta_zero_depth_one = pack([], ranked[:6], 32_000)

    assert single.selected_ids != beta_zero_depth_one.selected_ids
    assert len(beta_zero_depth_one.selected_ids) == 2 * len(single.selected_ids)


def test_real_q11_disabled_chain_misses_both_anchor_interpretations() -> None:
    from src.analysis.e006_chained_retrieval_preflight import load_episodes

    result = disabled_chain_control(load_episodes(), load_authoritative_packer())

    assert result["status"] == "FAIL"
    assert all(not cell["payload_sha256_equal"] for cell in result["cells"])
    assert all(
        not cell["committed_x0_payload_sha256_equal"]
        for cell in result["cells"]
    )
