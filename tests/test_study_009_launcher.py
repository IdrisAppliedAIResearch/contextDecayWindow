import pytest

from scripts.run_study_009 import assert_server


def server_props(**overrides):
    props = {
        "total_slots": 1,
        "default_generation_settings": {
            "n_ctx": 50176,
            "params": {
                "seed": 5005,
                "speculative.types": "none",
            },
        },
    }
    for key, value in overrides.items():
        if key == "n_ctx":
            props["default_generation_settings"]["n_ctx"] = value
        elif key in {"seed", "speculative.types"}:
            props["default_generation_settings"]["params"][key] = value
        else:
            props[key] = value
    return props


def test_registered_server_props_pass():
    assert_server(server_props())


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("seed", 1),
        ("total_slots", 2),
        ("n_ctx", 49999),
        ("speculative.types", "draft"),
    ],
)
def test_server_guard_rejects_drift(key, value):
    with pytest.raises(RuntimeError, match="Registered runtime guard failed"):
        assert_server(server_props(**{key: value}))
