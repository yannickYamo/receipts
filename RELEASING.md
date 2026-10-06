# Releasing

In order:

```bash
pip install -e ".[dev,mcp,anthropic]" build twine
ruff check src tests bench && ruff format --check src tests bench
pyright src
pytest -q                                   # 0 failed, 0 skipped
pip uninstall -y claim-receipts && PYTHONPATH=src pytest -q && pip install -e .

python -m build && twine check dist/*
python -m venv /tmp/try && /tmp/try/bin/pip install dist/*.whl && /tmp/try/bin/receipts --help

git tag v$(python -c "import receipts; print(receipts.__version__)") && git push --tags
```

Before the tag: `CHANGELOG.md` has the release entry with its date, and `EVALS.md` says which reader
each published number is for.

When a round's files are in the repository, two more steps come before the build. The suite then
also fails if the code that decides a claim differs from `bench/study/FROZEN.json`.

```bash
python bench/round3_report.py --write       # the round's page, from its files
git diff --exit-code studies/ROUND3_RESULTS.md
```

To publish on PyPI as well: `twine upload dist/*`, then change the README's install line to
`pip install claim-receipts`.
