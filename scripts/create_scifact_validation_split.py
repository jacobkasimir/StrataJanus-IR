"""Create a fixed query-level validation split from SciFact train qrels."""

import json
import random
from pathlib import Path

from stratajanus.evaluation.scifact_data import (
    load_qrels,
    sha256_file,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]

TRAIN_QRELS = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "scifact"
    / "qrels"
    / "train.tsv"
)

OUTPUT_PATH = (
    PROJECT_ROOT
    / "configs"
    / "scifact_eval_split.json"
)

SEED = 42
VALIDATION_FRACTION = 0.2


def main():
    """Select and save validation query IDs without reading test qrels."""
    if OUTPUT_PATH.exists():
        raise FileExistsError(
            f"Split already exists: {OUTPUT_PATH}"
        )

    qrels = load_qrels(TRAIN_QRELS)
    query_ids = sorted(qrels)

    if len(query_ids) < 2:
        raise ValueError(
            "At least two training queries are needed."
        )

    generator = random.Random(SEED)
    generator.shuffle(query_ids)

    validation_count = max(
        1,
        int(len(query_ids) * VALIDATION_FRACTION),
    )

    validation_ids = sorted(
        query_ids[:validation_count]
    )

    development_train_ids = sorted(
        query_ids[validation_count:]
    )

    split = {
        "dataset": "scifact",
        "seed": SEED,
        "validation_fraction": VALIDATION_FRACTION,
        "train_qrels_sha256": sha256_file(TRAIN_QRELS),
        "development_train_query_ids": development_train_ids,
        "validation_query_ids": validation_ids,
    }

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_PATH.open("x", encoding="utf-8") as file:
        json.dump(split, file, indent=2)
        file.write("\n")

    print(f"Saved split: {OUTPUT_PATH}")
    print(
        f"Development-training queries: "
        f"{len(development_train_ids)}"
    )
    print(f"Validation queries: {len(validation_ids)}")


if __name__ == "__main__":
    main()