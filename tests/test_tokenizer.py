import json
import unicodedata

import pytest

from stratajanus.text.tokenizer import (
    tokenize,
    save_tokenizer_config,
    verify_tokenizer_config,
)


def test_punctuation_separates_tokens():
    assert tokenize("Hello, world! Search-engine.") == [
        "hello",
        "world",
        "search",
        "engine",
    ]


def test_empty_text_produces_no_tokens():
    assert tokenize("") == []
    assert tokenize("   \n\t") == []
    assert tokenize("!!!") == []


def test_repeated_terms_are_preserved():
    assert tokenize("Search search SEARCH") == [
        "search",
        "search",
        "search",
    ]


def test_accented_text_is_preserved():
    assert tokenize("CAFÉ naïve") == [
        "café",
        "naïve",
    ]


def test_canonically_equivalent_accents_match():
    composed = "café"
    decomposed = "cafe\u0301"

    assert composed != decomposed

    assert unicodedata.normalize("NFC", composed) == (
        unicodedata.normalize("NFC", decomposed)
    )

    assert tokenize(composed) == tokenize(decomposed)


def test_numbers_are_retained_and_punctuation_splits_them():
    assert tokenize("COVID-19 cost 3.14 in 2025.") == [
        "covid",
        "19",
        "cost",
        "3",
        "14",
        "in",
        "2025",
    ]


def test_underscores_are_part_of_regex_word_tokens():
    assert tokenize("paper_123") == ["paper_123"]


def test_non_string_input_is_rejected():
    with pytest.raises(TypeError, match="expected str"):
        tokenize(None)


def test_config_can_be_saved_and_verified(tmp_path):
    config_path = tmp_path / "index" / "tokenizer_config.json"

    save_tokenizer_config(config_path)
    verify_tokenizer_config(config_path)

    saved = json.loads(config_path.read_text(encoding="utf-8"))

    assert saved == {
        "schema_version": 1,
        "unicode_normalization": "NFC",
        "lowercase": True,
        "token_pattern": r"\w+",
    }


def test_mismatched_config_is_rejected(tmp_path):
    config_path = tmp_path / "tokenizer_config.json"

    save_tokenizer_config(config_path)

    changed = json.loads(
        config_path.read_text(encoding="utf-8")
    )
    changed["lowercase"] = False

    config_path.write_text(
        json.dumps(changed),
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="does not match the index",
    ):
        verify_tokenizer_config(config_path)

