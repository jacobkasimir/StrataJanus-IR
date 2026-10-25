import pytest

from stratajanus.evaluation.scifact_data import (
    load_qrels,
    load_queries,
    sha256_file,
)


def test_load_queries(tmp_path):
    path = tmp_path / "queries.jsonl"

    path.write_text(
        '{"query_id":"q1","text":"Café claim"}\n'
        '{"query_id":"q2","text":"Another claim"}\n',
        encoding="utf-8",
    )

    assert load_queries(path) == {
        "q1": "Café claim",
        "q2": "Another claim",
    }

    assert len(sha256_file(path)) == 64


def test_duplicate_query_id_is_rejected(tmp_path):
    path = tmp_path / "queries.jsonl"

    path.write_text(
        '{"query_id":"q1","text":"First"}\n'
        '{"query_id":"q1","text":"Second"}\n',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Duplicate query"):
        load_queries(path)


def test_load_qrels_preserves_external_ids(tmp_path):
    path = tmp_path / "train.tsv"

    path.write_text(
        "query_id\tdoc_id\trelevance\n"
        "q1\t00123\t1\n"
        "q1\tpaper-A\t2\n",
        encoding="utf-8",
    )

    assert load_qrels(path) == {
        "q1": {
            "00123": 1,
            "paper-A": 2,
        }
    }


def test_duplicate_judgment_is_rejected(tmp_path):
    path = tmp_path / "train.tsv"

    path.write_text(
        "query_id\tdoc_id\trelevance\n"
        "q1\td1\t1\n"
        "q1\td1\t1\n",
        encoding="utf-8",
    )

    with pytest.raises(
        ValueError,
        match="Duplicate judgment",
    ):
        load_qrels(path)