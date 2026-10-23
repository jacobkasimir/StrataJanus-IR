"""Versioned Unicode normalization and token extraction for stratajanus.

The active configuration is :data:`CONFIG`; index and query text should use
the same tokenizer configuration.
"""

import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class TokenizerConfig:
    """Describe the tokenizer settings recorded alongside an index.

    ``schema_version`` identifies the configuration format;
    ``unicode_normalization``, ``lowercase``, and ``token_pattern`` define
    analysis behavior.
    """
    schema_version: int = 1
    unicode_normalization: str = "NFC"
    lowercase: bool = True
    token_pattern: str = r"\w+"


CONFIG = TokenizerConfig()
"""Active version-1 tokenization settings (NFC, lowercase, ``\\w+``)."""

TOKEN_REGEX = re.compile(CONFIG.token_pattern)


def tokenize(text: str) -> list[str]:
    """
    Convert text into tokens using stratajanus' version-1 rules.

    Steps:
    1. Unicode-normalize using NFC.
    2. Lowercase.
    3. Extract non-overlapping matches of Python's Unicode-aware ``\\w+``.
       Letters, digits, and underscore are retained within matches; other
       characters separate them. Repeated tokens and source order are kept.

    Args:
        text: Unicode string to analyze.

    Returns:
        Tokens in their order of appearance. Punctuation-only or empty input
        returns an empty list.

    Raises:
        TypeError: If ``text`` is not a string.
    """
    if not isinstance(text, str):
        raise TypeError(
            f"tokenize() expected str, got {type(text).__name__}"
        )

    normalized = unicodedata.normalize(
        CONFIG.unicode_normalization,
        text,
    )

    if CONFIG.lowercase:
        normalized = normalized.lower()

    return TOKEN_REGEX.findall(normalized)


def save_tokenizer_config(path: Path) -> None:
    """Write active tokenizer settings as formatted UTF-8 JSON.

    Args:
        path: Destination file path.

    Returns:
        None. Parent directories are created as needed and an existing file is
        overwritten.
    """
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", encoding="utf-8") as file:
        json.dump(
            asdict(CONFIG),
            file,
            indent=2,
            ensure_ascii=False,
        )
        file.write("\n")


def verify_tokenizer_config(path: Path) -> None:
    """Check that a saved tokenizer configuration matches :data:`CONFIG`.

    Args:
        path: UTF-8 JSON configuration file to read.

    Returns:
        None when the decoded JSON equals the active configuration.

    Raises:
        FileNotFoundError: If the path does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        ValueError: If the saved settings differ from the active settings.
    """
    with path.open("r", encoding="utf-8") as file:
        saved_config = json.load(file)

    current_config = asdict(CONFIG)

    if saved_config != current_config:
        raise ValueError(
            "Tokenizer configuration does not match the index.\n"
            f"Saved:   {saved_config}\n"
            f"Current: {current_config}"
        )
