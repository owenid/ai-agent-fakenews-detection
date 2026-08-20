import pytest

from app.openai_client import _extract_json


def test_extract_json_plain_object():
    assert _extract_json('{"verdict": "true"}') == {"verdict": "true"}


def test_extract_json_with_code_fence():
    raw = '```json\n{"verdict": "false"}\n```'
    assert _extract_json(raw) == {"verdict": "false"}


def test_extract_json_with_surrounding_prose():
    raw = 'Here is the result:\n{"verdict": "unverified"}\nThanks.'
    assert _extract_json(raw) == {"verdict": "unverified"}


def test_extract_json_empty_raises_clear_error():
    with pytest.raises(ValueError, match="empty response"):
        _extract_json("")


def test_extract_json_whitespace_only_raises_clear_error():
    with pytest.raises(ValueError, match="empty response"):
        _extract_json("   \n  ")


def test_extract_json_no_braces_raises_clear_error():
    with pytest.raises(ValueError, match="No JSON object found"):
        _extract_json("I'm sorry, I cannot verify this claim.")


def test_extract_json_malformed_raises_clear_error():
    with pytest.raises(ValueError, match="not valid JSON"):
        _extract_json('{"verdict": "true", }')
