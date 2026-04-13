"""Shared helpers for deterministic file writes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_text_if_changed(path: str | Path, content: str, *, encoding: str = 'utf-8') -> bool:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    existing = target.read_text(encoding=encoding) if target.exists() else None
    if existing == content:
        return False
    target.write_text(content, encoding=encoding)
    return True


def write_json_if_changed(
    path: str | Path,
    data: Any,
    *,
    indent: int = 2,
    sort_keys: bool = False,
    ensure_ascii: bool = False,
) -> bool:
    content = json.dumps(data, indent=indent, sort_keys=sort_keys, ensure_ascii=ensure_ascii) + '\n'
    return write_text_if_changed(path, content)
