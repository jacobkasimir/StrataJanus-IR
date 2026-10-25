# Agent instructions for stratajanus

## Project overview

stratajanus is a Python search-engine project. Consult `README.md`,
`pyproject.toml`, `mkdocs.yml`, source code, and tests before making changes.
Treat the implementation and measured reports as the source of truth.

## Working rules

- Use the project name **StrataJanus-IR** consistently.
- Make focused changes; do not restructure unrelated code.
- Preserve public APIs, index formats, ranking behavior, and existing data
  unless the task explicitly requires changing them.
- Do not invent benchmark or retrieval-quality results.
- Mark planned features as planned, not implemented.
- Do not tune against official held-out SciFact test judgments.
- Keep generated `site/`, downloaded `data/`, and temporary artifacts out
  of commits.
- Do not commit or push unless explicitly asked.

## Python and tests

- Development and testing currently use Python 3.14. Do not claim support
  for other versions without evidence.
- Add or update tests for behavior changes and storage-format changes.
- Run relevant tests first, then `python -m pytest -v` when feasible.
- If you cannot run a check, say so clearly.

## Documentation

- Maintain clear docstrings for public functions, classes, and methods.
- Update README or MkDocs only when a change makes them inaccurate or
  incomplete.
- Prefer existing documentation structure over duplicate pages.
- Verify commands, paths, configuration, and results before documenting them.
- Run `mkdocs build --strict` when documentation changes and the
  environment permits it.
- Do not edit generated HTML under `site/`.

## Reporting

At the end of a task, summarize changed files, verification performed,
actual results, and unresolved issues.