import hashlib
import json

# Study 007 Correction 1.
#
# Through Study 006 this module opened the script with no encoding argument, so
# it inherited the platform default. On Windows that is cp1252, which decodes
# the UTF-8 script into mojibake without raising: the model silently receives
# corrupted text and every downstream hash and log agrees with itself. Study 006
# caught one such run only by comparing against Study 005's preserved prompt
# hashes, and thereafter depended on PYTHONUTF8=1 being set in the environment.
#
# Correctness must not depend on an environment variable whose failure mode is
# silent. The encoding is now explicit, and load_script can assert the script's
# post-decode digest so a mis-decode aborts at startup instead of at analysis.

SCRIPT_ENCODING = "utf-8"


def script_digest(text: str) -> str:
    """SHA-256 of the decoded script, normalized to LF.

    Line endings are normalized because `core.autocrlf=true` rewrites the
    working-tree file without changing the committed blob. Normalizing keeps the
    digest stable across checkouts and equal to the value Studies 005 and 006
    recorded, so the assertion tests decoding rather than checkout settings.

    Every CR in this script is pretty-print whitespace between JSON tokens; none
    sits inside a string value, so normalization cannot alter script content.
    """
    return hashlib.sha256(
        text.replace("\r\n", "\n").replace("\r", "\n").encode("utf-8")
    ).hexdigest()


def load_script(
    path: str,
    minimum_turns: int = 30,
    expected_digest: str | None = None,
) -> dict:
    with open(path, "r", encoding=SCRIPT_ENCODING) as f:
        raw = f.read()

    if expected_digest is not None:
        actual_digest = script_digest(raw)
        if actual_digest != expected_digest:
            raise ValueError(
                "Script digest mismatch after decode. The script this run would "
                "have sent to the model is not the pre-registered script.\n"
                f"  path     : {path}\n"
                f"  expected : {expected_digest}\n"
                f"  actual   : {actual_digest}\n"
                "A mismatch here is usually a decoding fault (a non-UTF-8 "
                "default silently mangling the text) or an edited script. "
                "Aborting before any inference is spent."
            )

    script = json.loads(raw)

    if "system_prompt" not in script or not script["system_prompt"]:
        raise ValueError("Script must contain a non-empty 'system_prompt' key.")

    if "turns" not in script or not isinstance(script["turns"], list):
        raise ValueError("Script must contain a 'turns' key that is a list.")

    turns = script["turns"]

    if len(turns) < minimum_turns:
        raise ValueError(f"Script must have at least {minimum_turns} turns, found {len(turns)}.")

    for i, turn in enumerate(turns):
        if "turn" not in turn:
            raise ValueError(f"Turn at index {i} is missing 'turn' key.")
        if not isinstance(turn["turn"], int):
            raise ValueError(f"Turn at index {i} has non-integer 'turn' value: {turn['turn']}.")

        if "user" not in turn:
            raise ValueError(f"Turn {turn.get('turn', i)} is missing 'user' key.")
        if not isinstance(turn["user"], str):
            raise ValueError(f"Turn {turn['turn']} has non-string 'user' value.")

        expected_turn = i + 1
        if turn["turn"] != expected_turn:
            raise ValueError(
                f"Turn numbers must be sequential starting from 1. "
                f"Expected turn {expected_turn} at index {i}, got {turn['turn']}."
            )

    return script
