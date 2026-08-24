from __future__ import annotations

import spacy

from analysis.tc009_syntactic_span_probe import disposition, extract_spans


def test_span_extraction_names_nouns_and_subject_sentences() -> None:
    nlp = spacy.load("en_core_web_sm", disable=["ner", "lemmatizer", "textcat"])
    spans = extract_spans(nlp("Maria repaired the bicycle. It works."))
    assert "Maria" in spans["noun"]
    assert "the bicycle" in spans["noun"]
    assert spans["subject"] == ["Maria repaired the bicycle.", "It works."]


def test_disposition_requires_joint_positive_feedback() -> None:
    good = {"combined": {"gains": 3, "losses": 1}, "targeted": {"gains": 1, "losses": 1}, "breadth": {"gains": 1, "losses": 0}, "breadth_identity": {"net_identities": 1}, "conversation_nets": {"a": 1, "b": 1, "c": 0, "d": 0}}
    bad = {**good, "targeted": {"gains": 0, "losses": 1}}
    assert disposition({"noun": good})["status"] == "DESCRIPTIVE_POSITIVE_SIGNAL"
    assert disposition({"noun": bad})["status"] == "NO_POSITIVE_SIGNAL"
