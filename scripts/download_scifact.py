"""Download and extract the BEIR-format SciFact source dataset."""

from pathlib import Path

from beir import util


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOWNLOAD_DIR = PROJECT_ROOT / "data" / "raw"

DATASET_URL = (
    "https://public.ukp.informatik.tu-darmstadt.de/"
    "thakur/BEIR/datasets/scifact.zip"
)


def main():
    """Download and extract the SciFact BEIR dataset.

    Side effects:
        Creates ``data/raw`` if needed and downloads/extracts SciFact there.
        Requires the optional ``beir`` dependency and network access. The
        extracted path is printed to standard output.
    """
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    dataset_path = util.download_and_unzip(
        DATASET_URL,
        str(DOWNLOAD_DIR),
    )

    print(f"Dataset extracted to: {dataset_path}")


if __name__ == "__main__":
    main()
"""Download and extract the BEIR-format SciFact source dataset."""
