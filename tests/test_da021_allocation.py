from analysis.da009_role_pattern import role_pattern_pairs
from analysis.da015_phrase_dictionary import encode
from analysis.da021_allocation import choose_renderer


def test_joint_renderer_is_selected_only_when_strictly_smaller() -> None:
    pair = [{"speaker": "U", "text": "alpha beta gamma alpha beta gamma"}]
    role = role_pattern_pairs([pair])
    name, dictionary, chars = choose_renderer(role, [pair[0]["text"]], role.chars, None)
    assert chars <= role.chars
    assert (name == "JOINT") == (chars < role.chars)
    assert dictionary is not None if name == "JOINT" else dictionary is None


def test_control_phrase_renderer_reproduces_exact_charge() -> None:
    pair = [{"speaker": "U", "text": "repeated phrase repeated phrase repeated phrase"}]
    role = role_pattern_pairs([pair])
    dictionary = encode([pair[0]["text"]])
    control = role.chars - len(pair[0]["text"]) + dictionary.content_chars + dictionary.declaration_chars
    _, _, chars = choose_renderer(role, [pair[0]["text"]], control, dictionary)
    assert chars <= control

