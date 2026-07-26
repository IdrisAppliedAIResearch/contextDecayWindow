"""Study 007 Correction 1 — script decoding must not depend on the environment.

Through Study 006 `load_script` opened the script with the platform default
encoding. On Windows that is cp1252, which decodes the UTF-8 script into
mojibake without raising. The run then proceeds, the model receives corrupted
text, and every downstream artifact agrees with itself; Study 006 caught one
such run only by comparing against a previous study's preserved hashes.

These tests pin the two properties that make that failure impossible:
correctness under a hostile default encoding, and a startup abort when the
decoded script is not the pre-registered one.
"""

import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from src.study.script_loader import load_script, script_digest


REPO_ROOT = Path(__file__).resolve().parents[1]
STUDY_SCRIPT = REPO_ROOT / "experiments/study_005/script.json"

# Recorded by Study 005, re-verified by Study 006, and carried into Study 007.
# SHA-256 of the UTF-8-decoded script normalized to LF.
PRE_REGISTERED_DIGEST = (
    "d8ba73fd02bfd41bec156904fb6a3328bbed3d0da8bff05e4667d2e450752f01"
)

# Characters that survive a UTF-8 round trip but are mangled by cp1252.
NON_LATIN1_MARKERS = ["\u2014", "\u2265", "\u2019"]


def _write_script(path: Path, marker_text: str) -> None:
    """Write a minimally valid 30-turn script carrying non-Latin-1 text."""
    script = {
        "system_prompt": "You are a helpful assistant.",
        "turns": [
            {"turn": i + 1, "user": marker_text if i == 0 else f"Turn {i + 1}."}
            for i in range(30)
        ],
    }
    path.write_text(json.dumps(script, ensure_ascii=False), encoding="utf-8")


def test_study_script_digest_matches_pre_registration():
    """The committed script still decodes to the digest every study recorded."""
    script_text = STUDY_SCRIPT.read_text(encoding="utf-8")
    assert script_digest(script_text) == PRE_REGISTERED_DIGEST


def test_digest_is_insensitive_to_line_endings():
    """core.autocrlf must not change the digest; script content must."""
    lf = '{"a": 1,\n "b": 2}'
    crlf = '{"a": 1,\r\n "b": 2}'
    assert script_digest(lf) == script_digest(crlf)
    assert script_digest(lf) != script_digest('{"a": 1,\n "b": 3}')


def test_load_script_preserves_non_latin1_characters(tmp_path):
    marker = "Span is 847 m \u2014 load \u2265 92.4 t. Bekova\u2019s team."
    path = tmp_path / "script.json"
    _write_script(path, marker)

    script = load_script(str(path))

    assert script["turns"][0]["user"] == marker
    for character in NON_LATIN1_MARKERS:
        assert character in script["turns"][0]["user"]


def test_load_script_accepts_matching_digest(tmp_path):
    path = tmp_path / "script.json"
    _write_script(path, "Plain turn.")
    digest = script_digest(path.read_text(encoding="utf-8"))

    script = load_script(str(path), expected_digest=digest)

    assert len(script["turns"]) == 30


def test_load_script_aborts_on_digest_mismatch(tmp_path):
    """An edited or mis-decoded script must fail before any inference."""
    path = tmp_path / "script.json"
    _write_script(path, "Plain turn.")
    digest = script_digest(path.read_text(encoding="utf-8"))

    _write_script(path, "Tampered turn.")

    with pytest.raises(ValueError) as excinfo:
        load_script(str(path), expected_digest=digest)

    message = str(excinfo.value)
    assert "Script digest mismatch after decode" in message
    assert digest in message


def test_correctness_does_not_depend_on_pythonutf8(tmp_path):
    """The acceptance criterion for Correction 1.

    Run the loader in a subprocess with UTF-8 mode explicitly OFF and the
    locale coerced to cp1252 — the exact configuration under which Study 006's
    mojibake run was produced — and require the pre-registered digest anyway.

    Before this correction the same subprocess produced a different digest and
    raised no error.
    """
    program = textwrap.dedent(
        f"""
        import sys
        sys.path.insert(0, {str(REPO_ROOT)!r})
        from src.study.script_loader import load_script, script_digest

        script = load_script(
            {str(STUDY_SCRIPT)!r},
            minimum_turns=30,
            expected_digest={PRE_REGISTERED_DIGEST!r},
        )
        text = open({str(STUDY_SCRIPT)!r}, encoding="utf-8").read()
        print(script_digest(text))
        """
    )

    result = subprocess.run(
        [sys.executable, "-X", "utf8=0", "-c", program],
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={
            "PATH": "",
            "SYSTEMROOT": "C:\\Windows",
            "PYTHONUTF8": "0",
            "PYTHONIOENCODING": "utf-8",
            "PYTHONLEGACYWINDOWSFSENCODING": "",
            "LC_ALL": "en_US.cp1252",
        },
    )

    assert result.returncode == 0, (
        "Loading under a non-UTF-8 default must succeed.\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert result.stdout.strip() == PRE_REGISTERED_DIGEST


def test_mojibake_would_have_been_caught(tmp_path):
    """The digest assertion detects the specific Study 006 corruption.

    Simulate the cp1252 mis-decode by round-tripping the em dash through
    Latin-1, and confirm the digest diverges. This is the check that would have
    aborted the quarantined run before it consumed a full script.
    """
    clean = 'Halcyon Crossing \u2014 a long-span bridge.'
    mojibake = clean.encode("utf-8").decode("cp1252")

    assert mojibake != clean
    assert script_digest(clean) != script_digest(mojibake)
