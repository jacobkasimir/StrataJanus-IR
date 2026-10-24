"""Compress SciFact postings and compare against fixed-width storage."""

from pathlib import Path

from stratajanus.index.binary_storage import (
    load_index as load_fixed_index,
)
from stratajanus.index.compressed_storage import (
    load_index as load_compressed_index,
    save_index as save_compressed_index,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
FIXED_DIR = PROJECT_ROOT / "data" / "indexes" / "scifact-fixed32"
COMPRESSED_DIR = PROJECT_ROOT / "data" / "indexes" / "scifact-vb"


def directory_size(directory: Path) -> int:
    """Return total logical file bytes, including metadata."""
    return sum(
        path.stat().st_size
        for path in directory.rglob("*")
        if path.is_file()
    )


def main():
    """Compress, verify equality, and report measured storage sizes."""
    if COMPRESSED_DIR.exists():
        raise FileExistsError(
            f"Compressed index already exists: {COMPRESSED_DIR}"
        )

    original = load_fixed_index(FIXED_DIR)

    save_compressed_index(original, COMPRESSED_DIR)
    restored = load_compressed_index(COMPRESSED_DIR)

    if restored != original:
        raise ValueError("Compression changed the index.")

    fixed_bytes = (FIXED_DIR / "postings.bin").stat().st_size
    compressed_bytes = (
        COMPRESSED_DIR / "postings.bin"
    ).stat().st_size

    print("Compressed index verified.")
    print(f"Fixed-width postings: {fixed_bytes:,} bytes")
    print(f"Compressed postings: {compressed_bytes:,} bytes")

    if fixed_bytes:
        reduction = 100 * (1 - compressed_bytes / fixed_bytes)
        print(f"Posting-size reduction: {reduction:.2f}%")

    print(f"Fixed-width total: {directory_size(FIXED_DIR):,} bytes")
    print(f"Compressed total: {directory_size(COMPRESSED_DIR):,} bytes")


if __name__ == "__main__":
    main()