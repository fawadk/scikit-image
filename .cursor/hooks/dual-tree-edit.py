#!/usr/bin/env python3
"""Remind the agent to keep skimage / skimage2 / _skimage2 in sync after edits."""

from __future__ import annotations

import json
import sys
from pathlib import Path


def _path_from_payload(data: object) -> Path | None:
    if not isinstance(data, dict):
        return None
    for key in ("file_path", "filePath", "path"):
        value = data.get(key)
        if isinstance(value, str) and value:
            return Path(value)
    file_obj = data.get("file")
    if isinstance(file_obj, dict):
        value = file_obj.get("path")
        if isinstance(value, str) and value:
            return Path(value)
    return None


def _posix_under(path: Path) -> str:
    text = path.as_posix()
    for marker in ("/src/", "/tests/"):
        idx = text.find(marker)
        if idx != -1:
            return text[idx + 1 :]
    return text.lstrip("./")


def reminder_for(rel: str) -> str | None:
    if rel.startswith("src/skimage/") and not rel.startswith("src/skimage2/"):
        return (
            "Edited src/skimage/ (stable re-export layer). Put new behavior in "
            "src/_skimage2/, keep this file as a re-export or ski2_migration_decorator "
            "wrapper, and add tests under both tests/skimage/ and tests/skimage2/."
        )
    if rel.startswith("src/skimage2/"):
        return (
            "Edited src/skimage2/ (experimental shim). Do not add algorithm code here; "
            "implement in src/_skimage2/ and re-export from src/skimage/ as well."
        )
    if rel.startswith("src/_skimage2/"):
        return (
            "Edited src/_skimage2/ (implementation). Confirm src/skimage/ still "
            "re-exports the public names, src/skimage2/ still shims the submodule, "
            "and tests exist in both tests/skimage/ and tests/skimage2/."
        )
    if rel.startswith("tests/skimage/") and not rel.startswith("tests/skimage2/"):
        if any(part in rel for part in ("/future/", "test_migration.py", "test_doctest_adapters.py", "test_backends.py")):
            return None
        return (
            "Edited tests/skimage/ only. Mirror the same cases in tests/skimage2/ "
            "(import _skimage2 as ski2). Exceptions: future/, test_migration.py, "
            "test_doctest_adapters.py, util/test_backends.py."
        )
    if rel.startswith("tests/skimage2/"):
        if "/_shared/" in rel or rel.endswith("test_skimage2.py"):
            return None
        return (
            "Edited tests/skimage2/ only. Mirror the same cases in tests/skimage/ "
            "unless this is _shared/ or test_skimage2.py."
        )
    return None


def main() -> None:
    try:
        raw = sys.stdin.read()
        data = json.loads(raw) if raw.strip() else {}
    except Exception:
        print("{}")
        return

    path = _path_from_payload(data)
    if path is None:
        print("{}")
        return

    msg = reminder_for(_posix_under(path))
    if not msg:
        print("{}")
        return

    print(json.dumps({"additional_context": msg}))


if __name__ == "__main__":
    main()
