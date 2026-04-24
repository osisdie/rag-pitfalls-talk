"""AST-parse every .py file under app/ to guard against syntax errors.

Analog of the top-level .github/workflows/verify.yml for the demo tree.
Runs without any service dependencies — fast CI smoke.
"""
from __future__ import annotations

import ast
from pathlib import Path


def test_all_py_files_parse():
    root = Path(__file__).resolve().parent.parent / "app"
    errors: list[str] = []
    for f in root.rglob("*.py"):
        try:
            ast.parse(f.read_text(encoding="utf-8"))
        except SyntaxError as exc:
            errors.append(f"{f}: {exc}")
    assert not errors, "Syntax errors:\n  " + "\n  ".join(errors)


def test_rag_default_parses():
    root = Path(__file__).resolve().parent.parent / "app" / "core"
    default = root / "rag.py.default"
    assert default.exists(), f"missing {default}"
    ast.parse(default.read_text(encoding="utf-8"))
