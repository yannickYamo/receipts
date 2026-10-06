# Releasing

A release is the code that was measured, with its results beside it. In order:

```bash
pip install -e ".[dev,mcp,anthropic]" build twine
ruff check src tests bench && ruff format --check src tests bench
pyright src
pytest -q                                   # 0 failed, 0 skipped
pip uninstall -y claim-receipts && PYTHONPATH=src pytest -q && pip install -e .

python bench/round3_report.py --write       # the round's page, from its files; stops if the frozen code changed
git diff --exit-code studies/ROUND3_RESULTS.md

python -m build && twine check dist/*
python -m venv /tmp/try && /tmp/try/bin/pip install dist/*.whl && /tmp/try/bin/receipts --help

git tag v$(python -c "import receipts; print(receipts.__version__)") && git push --tags
twine upload dist/*
```

Before the tag: `CHANGELOG.md` has the release entry, `EVALS.md` gives the round's results with every
missed bar, the README's first sentence is the one `studies/ROUND3_RESULTS.md` prints, and nothing in
`core.py`, `text.py` or `reader.py` differs from `bench/study/FROZEN.json`.

After the upload: the README's install lines change from the clone to `pip install claim-receipts`.
