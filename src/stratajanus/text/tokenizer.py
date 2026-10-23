import json
import re
import unicodedata
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass(frozen=True)
class TokenizerConfig:
    schema_version: int = 1
    unicode_normalization: str = "NFC"
    lowercase: bool = True
    token_pattern: str = r"\w+"


CONFIG = TokenizerConfig()

TOKEN_REGEX = re.compile(CONFIG.token_pattern)


def tokenize(text: str) -> list[str]:
    """
    Convert text into tokens using Strata's version-1 rules.

    Steps:
    1. Unicode-normalize using NFC.
    2. Lowercase.
    3. Extract tokens using the configured regex.
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
    """Write tokenizer settings into an index directory."""
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
    """
    Refuse to use an index built with different tokenizer settings.
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