from analysis.da015_phrase_dictionary import encode
from analysis.da016_allocation import encode_existing


def test_existing_dictionary_codes_payload_without_learning() -> None:
    dictionary = encode(("project cedar project cedar project cedar",))
    payload = ("project cedar remains active",)
    encoded = encode_existing(payload, dictionary)
    assert encoded.phrases == dictionary.phrases
    assert encoded.content_chars < len(payload[0])


def test_existing_dictionary_preserves_unmatched_payload() -> None:
    dictionary = encode(("project cedar project cedar project cedar",))
    payload = ("unrelated words",)
    encoded = encode_existing(payload, dictionary)
    assert encoded.content_chars == len(payload[0])
