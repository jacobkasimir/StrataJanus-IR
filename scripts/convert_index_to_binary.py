"""Convert the existing SciFact JSON index to fixed-width binary."""

from pathlib import Path

from stratajanus.index.binary_storage import (
    load_index as load_binary_index,
    save_index as save_binary_index,
)
from stratajanus.index.storage import load_index as load_json_index


PROJECT_ROOT = Path(__file__).resolve().parents[1]

JSON_DIR = PROJECT_ROOT / "data" / "indexes" / "scifact"
BINARY_DIR = (
    PROJECT_ROOT / "data" / "indexes" / "scifact-fixed32"
)


def directory_size(directory: Path) -> int:
    """Return the total logical size of files under a directory."""
    return sum(
        path.stat().st_size
        for path in directory.rglob("*")
        if path.is_file()
    )


def main():
    """Convert, reload, verify, and report storage sizes."""
    if BINARY_DIR.exists():
        raise FileExistsError(
            f"Binary index already exists: {BINARY_DIR}"
        )

    print("Loading existing JSON index...")
    original = load_json_index(JSON_DIR)

    print("Saving fixed-width binary index...")
    save_binary_index(original, BINARY_DIR)

    print("Reloading and checking binary index...")
    restored = load_binary_index(BINARY_DIR)

    if restored != original:
        raise ValueError(
            "Binary round trip changed the index."
        )

    print("\nConversion checks passed.")
    print(f"Documents: {restored.document_count:,}")
    print(f"Terms: {len(restored.postings):,}")
    print(f"JSON directory: {directory_size(JSON_DIR):,} bytes")
    print(f"Binary directory: {directory_size(BINARY_DIR):,} bytes")

    print(
        "Binary postings: "
        f"{(BINARY_DIR / 'postings.bin').stat().st_size:,} bytes"
    )

    print(f"Saved to: {BINARY_DIR}")


if __name__ == "__main__":
    main()