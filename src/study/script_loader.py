import json


def load_script(path: str, minimum_turns: int = 30) -> dict:
    with open(path, "r") as f:
        script = json.load(f)

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
