# API Reference

StrataJanus-IR currently exposes a small, script-oriented Python API for
preparing and inspecting the SciFact dataset. The functions below are the
public functions found in the existing `scripts` modules. They are useful both
as command-line entry points and as building blocks for dataset workflows.

The conversion pipeline reads BEIR-format SciFact files, validates identifiers
and relevance judgments, then writes normalized JSONL and TSV files together
with a manifest. The download and loading scripts provide the corresponding
dataset acquisition and inspection entry points.

## SciFact conversion

::: scripts.prepare_scifact
    options:
      heading_level: 3
      members:
        - read_jsonl
        - require_id
        - require_text
        - prepare_metadata
        - write_jsonl_row
        - convert_documents
        - convert_queries
        - convert_qrels
        - main

## Dataset download

::: scripts.download_scifact
    options:
      heading_level: 3
      members:
        - main

## Dataset loading and inspection

::: scripts.load_scifact
    options:
      heading_level: 3
      members:
        - main
