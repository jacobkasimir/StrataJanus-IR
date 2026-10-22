from pathlib import Path

from beir import util


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DOWNLOAD_DIR = PROJECT_ROOT / "data" / "raw"

DATASET_URL = (
    "https://public.ukp.informatik.tu-darmstadt.de/"
    "thakur/BEIR/datasets/scifact.zip"
)


def main():
    DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

    dataset_path = util.download_and_unzip(
        DATASET_URL,
        str(DOWNLOAD_DIR),
    )

    print(f"Dataset extracted to: {dataset_path}")


if __name__ == "__main__":
    main()