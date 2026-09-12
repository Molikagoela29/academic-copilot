import pytest

from app.utils.llm_parser import extract_json


def test_parses_raw_json_array():
    assert extract_json('[{"term": "Mitosis"}]') == [{"term": "Mitosis"}]


def test_parses_json_wrapped_in_code_fences():
    raw = '```json\n[{"question": "Why?", "answer": "Because."}]\n```'
    assert extract_json(raw) == [{"question": "Why?", "answer": "Because."}]


def test_parses_json_surrounded_by_prose():
    raw = 'Sure! Here are your cards:\n[{"term": "ATP"}]\nHope that helps.'
    assert extract_json(raw) == [{"term": "ATP"}]


def test_parses_json_object():
    assert extract_json('{"score": 80}') == {"score": 80}


def test_prefers_array_over_trailing_object_noise():
    raw = 'Output:\n[{"a": 1}, {"b": 2}]'
    assert extract_json(raw) == [{"a": 1}, {"b": 2}]


def test_raises_on_unparseable_text():
    with pytest.raises(ValueError):
        extract_json("I'm afraid I cannot help with that request.")
