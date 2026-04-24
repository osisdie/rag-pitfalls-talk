"""Safe hot-reload of `app.core.rag`.

Rules:
    1. AST-parse *before* touching disk (fail fast, no partial writes).
    2. Atomic write (tmp + rename) so a crash mid-write can't corrupt rag.py.
    3. importlib.reload the existing module object so callers see new code.
    4. On import-error, auto-rollback to last known good source + reload.
    5. Every successful reload creates a row in rag_versions (capped per scenario).
"""
from __future__ import annotations

import ast
import importlib
import logging
import shutil
import sys
import tempfile
from pathlib import Path

from app.config import get_settings
from app.core import pg
from app.models.schemas import ApplyFixResult

log = logging.getLogger(__name__)

_MODULE_NAME = "app.core.rag"


def _read_live() -> str:
    s = get_settings()
    if s.rag_live_path.exists():
        return s.rag_live_path.read_text(encoding="utf-8")
    if s.rag_default_path.exists():
        return s.rag_default_path.read_text(encoding="utf-8")
    return ""


def _write_atomic(target: Path, source: str) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=".rag_", dir=str(target.parent))
    try:
        with open(fd, "w", encoding="utf-8") as f:
            f.write(source)
        shutil.move(tmp, target)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


def _reload_module() -> None:
    if _MODULE_NAME in sys.modules:
        importlib.reload(sys.modules[_MODULE_NAME])
    else:
        importlib.import_module(_MODULE_NAME)


async def ensure_live_from_default() -> None:
    """Copy rag.py.default → rag.py on first boot if live file is missing."""
    s = get_settings()
    if s.rag_live_path.exists():
        return
    if not s.rag_default_path.exists():
        raise RuntimeError(
            f"No rag.py.default at {s.rag_default_path}. Cannot bootstrap."
        )
    _write_atomic(s.rag_live_path, s.rag_default_path.read_text(encoding="utf-8"))
    _reload_module()


async def apply_rag_source(
    source: str, *, scenario_id: str | None, author: str, label: str
) -> ApplyFixResult:
    s = get_settings()

    # Step 1: AST parse — fail fast, no disk write.
    try:
        ast.parse(source)
    except SyntaxError as exc:
        return ApplyFixResult(ok=False, error=f"SyntaxError: {exc}")

    # Step 2: snapshot current for rollback.
    rollback_source = _read_live()

    # Step 3: atomic write + reload.
    try:
        _write_atomic(s.rag_live_path, source)
        _reload_module()
    except Exception as exc:
        log.exception("apply_rag_source reload failed: %s", exc)
        # Rollback
        try:
            _write_atomic(s.rag_live_path, rollback_source)
            _reload_module()
        except Exception:
            log.exception("Rollback also failed; rag.py may be inconsistent")
        return ApplyFixResult(ok=False, error=str(exc), rolled_back=True)

    # Step 4: persist new version + prune.
    version_id = await pg.insert_version(scenario_id, author, label, source)
    if scenario_id:
        await pg.prune_versions(scenario_id, keep=s.rag_version_cap)
    return ApplyFixResult(ok=True, version_id=version_id)


async def revert_to_version(version_id: int) -> ApplyFixResult:
    row = await pg.get_version(version_id)
    if row is None:
        return ApplyFixResult(ok=False, error=f"version {version_id} not found")
    return await apply_rag_source(
        row["source"],
        scenario_id=row["scenario_id"],
        author="revert",
        label=f"revert to v{version_id}",
    )


def read_current_source() -> str:
    return _read_live()
