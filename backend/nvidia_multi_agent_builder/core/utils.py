"""Shared utilities."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import uuid4


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID with optional prefix."""
    unique = uuid4().hex[:12]
    return f"{prefix}{unique}" if prefix else unique


def generate_short_id() -> str:
    """Generate a short 8-character ID."""
    return uuid4().hex[:8]


def hash_content(content: str | bytes) -> str:
    """Generate SHA256 hash of content."""
    if isinstance(content, str):
        content = content.encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def hash_content_short(content: str | bytes, length: int = 12) -> str:
    """Generate short hash of content."""
    return hash_content(content)[:length]


def now_utc() -> datetime:
    """Get current UTC datetime."""
    return datetime.now(UTC)


def now_iso() -> str:
    """Get current UTC datetime as ISO string."""
    return now_utc().isoformat()


def parse_iso_datetime(value: str) -> datetime:
    """Parse ISO datetime string."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def slugify(text: str, max_length: int = 100) -> str:
    """Convert text to URL-safe slug."""
    # Lowercase and replace spaces/special chars with hyphens
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    slug = re.sub(r"[\s_-]+", "-", slug)
    slug = slug.strip("-")
    return slug[:max_length]


def ensure_dir(path: Path) -> Path:
    """Ensure directory exists."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_json_file(path: Path) -> dict[str, Any]:
    """Read JSON file."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(path: Path, data: dict[str, Any], indent: int = 2) -> None:
    """Write JSON file."""
    ensure_dir(path.parent)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)


def truncate(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length."""
    if len(text) <= max_length:
        return text
    return text[: max_length - len(suffix)] + suffix


def deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Deep merge two dictionaries."""
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


class JSONEncoder(json.JSONEncoder):
    """Extended JSON encoder for common types."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, Path):
            return str(obj)
        if hasattr(obj, "__dict__"):
            return obj.__dict__
        return super().default(obj)


def to_json(data: Any, **kwargs) -> str:
    """Serialize to JSON with custom encoder."""
    return json.dumps(data, cls=JSONEncoder, **kwargs)