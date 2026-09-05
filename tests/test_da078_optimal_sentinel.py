from itertools import product

from analysis.da034_sentinel_backrefs import decode_members, encoded_chars, reference_code
from analysis.da023_backrefs import Backref
from analysis.da078_optimal_sentinel import encode_members


def _brute_cost(text: str, history: tuple[str, ...], sentinel: str) -> int:
    costs = [0] * (len(text) + 1)
    for position in range(len(text) - 1, -1, -1):
        best = 1 + costs[position + 1]
        for member_index, source in enumerate(history):
            for start in range(len(source)):
                limit = min(len(text) - position, len(source) - start)
                for length in range(4, limit + 1):
                    if text[position:position + length] != source[start:start + length]:
                        break
                    ref = Backref(member_index, start, length)
                    best = min(
                        best,
                        len(reference_code(sentinel, ref, len(history)))
                        + costs[position + length],
                    )
        costs[position] = best
    return costs[0]


def test_optimal_parse_matches_exhaustive_cost() -> None:
    history = ("abababab", "babaabbaba")
    for size in range(1, 9):
        for chars in product("ab", repeat=size):
            text = "".join(chars)
            encoded = encode_members([text], history, "~")
            assert decode_members(encoded, history, "~") == (text,)
            assert encoded_chars(encoded, "~", len(history)) == _brute_cost(
                text, history, "~"
            )
