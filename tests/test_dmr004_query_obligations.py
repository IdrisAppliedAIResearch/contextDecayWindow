"""Verification contract for DMR-004's query-obligation compiler.

Specification §11 names what these must cover: canonicalization, offsets across
Unicode normalization, every grammar class and precedence collision, malformed
numbers, number formatting, quoted spans, punctuation, nested coordination,
duplicate obligations, maximum length, output bounds, pure two-process replay,
dependency and import restrictions, and zero network or model calls.

Several tests here assert the registered behavior even where it is unhelpful -
`last Saturday` demoting a perfectly good lookup, for instance. That is
deliberate. A test that encodes what the grammar ought to do rather than what it
was registered to do would hide the finding instead of recording it.
"""

from __future__ import annotations

import json
import subprocess
import sys
import unicodedata
from pathlib import Path

import pytest

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY_ROOT / "src"))

from biological_memory.query_obligations import (  # noqa: E402
    MAX_QUERY_CHARACTERS,
    AGGREGATE_MARKERS,
    CompletenessMode,
    ObligationKind,
    PlanClass,
    QueryObligationCompiler,
    QueryObligationError,
    SupportMode,
    canonical_map,
    design_sha256,
)

COMPILER = QueryObligationCompiler()


def compile_query(text: str):
    return COMPILER.compile(text)


# ------------------------------------------------------------ canonicalization

def test_canonical_view_folds_case_and_collapses_whitespace():
    view, _ = canonical_map("  What   IS\tMy   Dog?  ")
    assert view == "what is my dog?"


def test_canonical_offsets_point_into_the_original_string():
    text = "  What breed is my dog?  "
    view, origins = canonical_map(text)
    assert len(view) == len(origins)
    for index, character in enumerate(view):
        origin = origins[index]
        assert 0 <= origin < len(text)
        if character != " ":
            assert text[origin].casefold() == character


def test_canonical_offsets_survive_a_length_changing_normalization():
    # The ligature normalizes to two characters, so index arithmetic against
    # the original would be off by one from here on.
    text = "What is the ﬁle number?"
    view, origins = canonical_map(text)
    assert "file number" in view
    assert len(view) != len(text)
    start = view.index("file number")
    assert text[origins[start]] == "ﬁ"


def test_casefold_expansion_keeps_one_origin_per_produced_character():
    text = "Weiß?"
    view, origins = canonical_map(text)
    assert view == "weiss?"
    assert origins[3] == origins[4] == 3


def test_span_text_always_equals_the_slice_it_reports():
    for text in [
        "What breed is my dog?",
        "  What   breed is my   dog?  ",
        "What is the ﬁle number in the records room?",
    ]:
        plan = compile_query(text)
        for obligation in plan.obligations:
            assert obligation.source_text == text[obligation.source_start : obligation.source_end]


# ------------------------------------------------------------------- classes

def test_lookup_is_one_frame_with_one_obligation():
    plan = compile_query("What breed is my dog?")
    assert plan.plan_class is PlanClass.LOOKUP
    assert plan.completeness_mode is CompletenessMode.FINITE
    assert len(plan.obligations) == 1
    assert plan.obligations[0].kind is ObligationKind.LOOKUP
    assert plan.obligations[0].support_mode is SupportMode.ONE_EVIDENCE


def test_history_marker_yields_a_lineage_obligation_that_claims_nothing():
    plan = compile_query("What was my previous occupation?")
    assert plan.plan_class is PlanClass.HISTORY
    assert plan.completeness_mode is CompletenessMode.NOVELTY_ONLY
    assert plan.obligations[0].kind is ObligationKind.HISTORY_LINEAGE
    assert plan.obligations[0].support_mode is SupportMode.LINEAGE
    assert plan.claims_completeness is False


def test_discourse_pointer_is_not_history():
    plan = compile_query(
        "I'm going back to our previous conversation about music theory. "
        "Can you remind me of the website you recommended?"
    )
    assert plan.plan_class is not PlanClass.HISTORY
    assert "DISCOURSE_POINTER_NOT_HISTORY" in plan.ambiguity_codes


def test_change_frame_is_history_without_a_marker_word():
    plan = compile_query("How did my commute change after the move?")
    assert plan.plan_class is PlanClass.HISTORY


def test_enumerate_carries_the_cardinality_on_one_obligation():
    # Amendment 001: one obligation carrying N, never N obligations sharing a span.
    plan = compile_query(
        "What is the order of the three trips I took in the past three months?"
    )
    assert plan.plan_class is PlanClass.ENUMERATE_N
    assert len(plan.obligations) == 1
    assert plan.obligations[0].kind is ObligationKind.LIST_MEMBER
    assert plan.obligations[0].requested_count == 3
    assert plan.obligations[0].support_mode is SupportMode.N_DISTINCT


def test_conjunct_needs_clause_initial_frames_not_a_comma():
    joined = compile_query(
        "Who is the lead engineer on Halcyon Crossing, and what is its load rating?"
    )
    assert joined.plan_class is PlanClass.LOOKUP, (
        "a coordinated interrogative after a comma is not clause-initial; "
        "Part 1 found this is how multi-part requests are actually written, "
        "which is why CONJUNCT is emitted but not gated"
    )

    split = compile_query("Who is the lead engineer? What is its load rating?")
    assert split.plan_class is PlanClass.CONJUNCT
    assert len(split.obligations) == 2


def test_conjunct_spans_never_overlap():
    plan = compile_query(
        "What is my dog's name? Where does my sister live? When did I move?"
    )
    assert plan.plan_class is PlanClass.CONJUNCT
    spans = [(o.source_start, o.source_end) for o in plan.obligations]
    assert spans == sorted(spans)
    for earlier, later in zip(spans, spans[1:]):
        assert earlier[1] <= later[0]


def test_top_level_semicolon_makes_a_conjunct():
    plan = compile_query("What is my dog's name; where does my sister live?")
    assert plan.plan_class is PlanClass.CONJUNCT


def test_aggregate_frame_is_never_finite():
    for text in [
        "How many bikes do I own?",
        "What is the total cost of the food bowl and the flea collar?",
        "What is the average age of me and my parents?",
    ]:
        plan = compile_query(text)
        assert plan.completeness_mode is CompletenessMode.UNREPRESENTABLE, text
        assert plan.obligations == ()


def test_no_interrogative_frame_falls_to_open():
    plan = compile_query(
        "For marine geophysics, name the project and lead, then state the value."
    )
    assert plan.plan_class is PlanClass.OPEN
    assert "NO_INTERROGATIVE_FRAME" in plan.ambiguity_codes


def test_empty_query_still_carries_the_registered_code():
    plan = compile_query("   ")
    assert plan.plan_class is PlanClass.OPEN
    assert "NO_INTERROGATIVE_FRAME" in plan.ambiguity_codes


# --------------------------------------------------------------- precedence

def test_history_outranks_the_aggregate_demotion():
    # Both a history marker and "how much" are present. Step 1 runs first.
    plan = compile_query("How much did my rent change from my previous apartment?")
    assert plan.plan_class is PlanClass.HISTORY


def test_conjunct_outranks_the_aggregate_demotion():
    # A registered consequence, and an unhelpful one: two aggregate clauses
    # become a FINITE plan because step 3 precedes step 4.
    plan = compile_query(
        "How many engineers did I lead then? How many engineers do I lead now?"
    )
    assert plan.plan_class is PlanClass.CONJUNCT
    assert plan.completeness_mode is CompletenessMode.FINITE


def test_enumerate_outranks_conjunct():
    plan = compile_query("What are the three rules? Which ones did I break?")
    assert plan.plan_class is PlanClass.ENUMERATE_N


def test_registered_temporal_superlative_demotes_an_ordinary_lookup():
    # "last" is a registered superlative marker. On a temporal deictic that is
    # the wrong call, and separating the two needs syntax this stage excludes.
    # The registration governs; the cost is recorded here rather than patched.
    plan = compile_query("Who did I go with to the music event last Saturday?")
    assert plan.plan_class is PlanClass.OPEN
    assert "SUPERLATIVE_OVER_UNNUMBERED_SET" in plan.ambiguity_codes


# ------------------------------------------------------------------ numerals

def test_ordinal_is_not_a_cardinality():
    plan = compile_query("What was the 7th job in the list you provided?")
    assert plan.plan_class is not PlanClass.ENUMERATE_N
    assert "NUMERAL_NOT_CARDINALITY" in plan.ambiguity_codes


def test_decimal_formatting_does_not_become_an_integer_cardinality():
    integer = compile_query("What are the 3 rules I set?")
    decimal = compile_query("What are the 3.0 rules I set?")
    assert integer.plan_class is PlanClass.ENUMERATE_N
    assert integer.obligations[0].requested_count == 3
    assert decimal.plan_class is not PlanClass.ENUMERATE_N, (
        "'3.0 rules' must not be read as an integer cardinality unless preregistered"
    )


def test_a_bare_integer_without_a_list_request_is_not_an_enumeration():
    plan = compile_query("What kitchen appliance did I buy 10 days ago?")
    assert plan.plan_class is not PlanClass.ENUMERATE_N


def test_cardinality_beyond_the_registered_ceiling_is_refused():
    plan = compile_query("What are the 5000 items I listed?")
    assert plan.plan_class is not PlanClass.ENUMERATE_N
    assert "CARDINALITY_OUT_OF_RANGE" in plan.ambiguity_codes


# ------------------------------------------------------ punctuation and quotes

def test_quoted_spans_do_not_change_the_class():
    plain = compile_query("Which book did I finish last week?")
    quoted = compile_query("Which book did I finish 'last week'?")
    assert plain.plan_class is quoted.plan_class


def test_curly_and_straight_quotes_agree():
    straight = compile_query("What did you say about 'The Nightingale'?")
    curly = compile_query("What did you say about ‘The Nightingale’?")
    assert straight.plan_class is curly.plan_class


@pytest.mark.parametrize(
    "mutate",
    [
        lambda text: text.upper(),
        lambda text: "  " + text.replace(" ", "   ") + "  ",
        lambda text: text.rstrip("? ") + " ?",
        lambda text: unicodedata.normalize("NFD", text),
    ],
)
def test_perturbations_do_not_change_the_plan_class(mutate):
    corpus = [
        "What breed is my dog?",
        "How many bikes do I own?",
        "What was my previous occupation?",
        "What is the order of the three trips I took?",
        "Who is the lead engineer? What is its load rating?",
    ]
    for text in corpus:
        assert compile_query(text).plan_class is compile_query(mutate(text)).plan_class, text


# --------------------------------------------------------------- output bounds

def test_output_cardinality_is_bounded_at_the_maximum_length():
    text = " ".join(["What is my dog's name?"] * 180)[:MAX_QUERY_CHARACTERS]
    plan = compile_query(text)
    assert len(plan.obligations) <= len(text)
    for obligation in plan.obligations:
        assert 0 <= obligation.source_start < obligation.source_end <= len(text)


def test_a_query_beyond_the_maximum_is_refused_not_truncated():
    with pytest.raises(QueryObligationError):
        compile_query("x" * (MAX_QUERY_CHARACTERS + 1))


def test_non_string_input_is_refused():
    with pytest.raises(QueryObligationError):
        compile_query(None)  # type: ignore[arg-type]


def test_obligation_ids_are_unique_within_a_plan():
    plan = compile_query(
        "What is my dog's name? Where does my sister live? When did I move?"
    )
    ids = [obligation.obligation_id for obligation in plan.obligations]
    assert len(ids) == len(set(ids))


def test_obligation_id_depends_on_the_query_not_on_call_order():
    first = compile_query("What breed is my dog?")
    second = QueryObligationCompiler().compile("What breed is my dog?")
    assert first.digest() == second.digest()
    assert first.obligations[0].obligation_id == second.obligations[0].obligation_id


def test_distinct_queries_get_distinct_plan_digests():
    a = compile_query("What breed is my dog?")
    b = compile_query("What breed is my cat?")
    assert a.digest() != b.digest()


# ---------------------------------------------------------------- determinism

def test_two_process_replay_is_byte_identical():
    corpus = [
        "What breed is my dog?",
        "How many bikes do I own?",
        "What was my previous occupation?",
        "What is the order of the three trips I took in the past three months?",
        "Who is the lead engineer? What is its load rating?",
        "For marine geophysics, name the project and lead, then state the value.",
        "  What   IS\tMy   Dog?  ",
        "What is the ﬁle number in the records room?",
    ]
    script = (
        "import json, sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'src')!r})\n"
        "from biological_memory.query_obligations import QueryObligationCompiler, design_sha256\n"
        "compiler = QueryObligationCompiler()\n"
        "corpus = json.loads(sys.stdin.read())\n"
        "print(json.dumps({\n"
        "    'design': design_sha256(),\n"
        "    'digests': [compiler.compile(text).digest() for text in corpus],\n"
        "}))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        input=json.dumps(corpus),
        capture_output=True,
        text=True,
        check=True,
    )
    other = json.loads(result.stdout)
    assert other["design"] == design_sha256()
    assert other["digests"] == [compile_query(text).digest() for text in corpus]


def test_design_hash_moves_when_the_grammar_moves():
    import biological_memory.query_obligations as module

    before = design_sha256()
    original = module.AGGREGATE_MARKERS
    try:
        module.AGGREGATE_MARKERS = original + ("how tall",)
        assert design_sha256() != before
    finally:
        module.AGGREGATE_MARKERS = original
    assert design_sha256() == before


# --------------------------------------------------------- purity and imports

def test_module_import_closure_is_standard_library_only():
    """A fresh interpreter, so an already-imported module cannot mask a leak."""
    # Membership in sys.stdlib_module_names, not path matching: C extensions
    # such as _hashlib and unicodedata live in DLLs/ on Windows and are still
    # standard library.
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'src')!r})\n"
        "before = set(sys.modules)\n"
        "import biological_memory.query_obligations\n"
        "added = sorted(set(sys.modules) - before)\n"
        "leaks = [\n"
        "    name for name in added\n"
        "    if not name.startswith('biological_memory')\n"
        "    and name.split('.')[0] not in sys.stdlib_module_names\n"
        "]\n"
        "print(repr(leaks))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]", result.stdout


def test_compiler_makes_no_network_or_subprocess_call():
    import socket

    calls: list[str] = []

    class Tripwire(socket.socket):
        def __init__(self, *args, **kwargs):
            calls.append("socket")
            raise AssertionError("the compiler opened a socket")

    original_socket = socket.socket
    original_run = subprocess.run
    original_popen = subprocess.Popen

    def forbid_run(*args, **kwargs):
        calls.append("subprocess")
        raise AssertionError("the compiler started a process")

    socket.socket = Tripwire  # type: ignore[misc]
    subprocess.run = forbid_run  # type: ignore[assignment]
    subprocess.Popen = forbid_run  # type: ignore[assignment]
    try:
        for text in [
            "What breed is my dog?",
            "How many bikes do I own?",
            "What was my previous occupation?",
        ]:
            compile_query(text)
    finally:
        socket.socket = original_socket  # type: ignore[misc]
        subprocess.run = original_run  # type: ignore[assignment]
        subprocess.Popen = original_popen  # type: ignore[assignment]
    assert calls == []


def test_compiler_does_not_reach_the_rater_or_any_corpus():
    """Rater B is measurement. A path from mechanism to it would be leakage."""
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'src')!r})\n"
        "import biological_memory.query_obligations\n"
        "banned = [n for n in sys.modules if 'rater_b' in n or 'dmr004_corpus' in n]\n"
        "print(repr(banned))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]", result.stdout


def test_package_init_does_not_re_export_the_compiler_into_a_wider_closure():
    """`src/biological_memory/__init__.py` must stay importable without pulling
    anything non-stdlib in; DMR-001 found a sibling doing exactly that."""
    script = (
        "import sys\n"
        f"sys.path.insert(0, {str(REPOSITORY_ROOT / 'src')!r})\n"
        "before = set(sys.modules)\n"
        "import biological_memory\n"
        "leaks = [\n"
        "    name for name in sorted(set(sys.modules) - before)\n"
        "    if not name.startswith('biological_memory')\n"
        "    and name.split('.')[0] not in sys.stdlib_module_names\n"
        "]\n"
        "print(repr(leaks))\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]", result.stdout


# ------------------------------------------------------------- corpus sanity

def test_every_committed_query_compiles_to_a_well_formed_plan():
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
    from analysis import dmr004_corpus as corpus

    records = corpus.read_cache(REPOSITORY_ROOT)
    assert len(records) == 524
    for record in records:
        plan = COMPILER.compile(record.text)
        assert plan.plan_class in set(PlanClass)
        assert plan.design_sha256 == design_sha256()
        spans = [(o.source_start, o.source_end) for o in plan.obligations]
        for start, end in spans:
            assert 0 <= start < end <= len(record.text)
            assert record.text[start:end].strip()
        for earlier, later in zip(spans, spans[1:]):
            assert earlier[1] <= later[0], record.text
        if plan.plan_class is PlanClass.OPEN:
            assert plan.obligations == ()
            assert plan.ambiguity_codes


def test_no_registered_marker_fires_only_on_internal_queries():
    """G6 in test form: a marker that only this program's own probes trigger is
    a house-style detector, not a grammar rule."""
    sys.path.insert(0, str(REPOSITORY_ROOT / "src"))
    from analysis import dmr004_corpus as corpus
    import re

    records = corpus.read_cache(REPOSITORY_ROOT)
    internal = [canonical_map(r.text)[0] for r in records if r.source == "internal"]
    external = [canonical_map(r.text)[0] for r in records if r.source == "longmemeval"]

    offenders = []
    for phrase in AGGREGATE_MARKERS:
        pattern = re.compile(r"\b" + re.escape(phrase) + r"\b")
        fires_internal = any(pattern.search(text) for text in internal)
        fires_external = any(pattern.search(text) for text in external)
        if fires_internal and not fires_external:
            offenders.append(phrase)
    assert offenders == []
