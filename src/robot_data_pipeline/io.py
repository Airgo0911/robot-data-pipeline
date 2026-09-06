"""Small JSONL/YAML/JSON helpers used by the CLI and examples."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping


def read_jsonl(path: Path) -> Iterator[dict[str, Any]]:
    """Yield non-empty JSON objects from a UTF-8 JSONL file."""
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            text = line.strip()
            if not text:
                continue
            value = json.loads(text)
            if not isinstance(value, dict):
                raise ValueError(f"{path}:{line_number} is not a JSON object")
            yield value


def write_jsonl(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    """Write records deterministically enough for review and diffing."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(
                json.dumps(dict(row), ensure_ascii=False, sort_keys=True)
                + "\n"
            )


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def load_yaml(path: Path) -> dict[str, Any]:
    """Load YAML, with a small fallback for the checked-in example config.

    PyYAML remains the preferred parser.  The fallback intentionally supports
    only mappings, scalar values, and scalar lists; it prevents the public
    dry-run example from failing in a bare Python environment, while making it
    clear that a production schema should install PyYAML.
    """
    try:
        import yaml
    except ImportError:  # pragma: no cover - depends on environment
        value = _load_minimal_yaml(path.read_text(encoding="utf-8"))
    else:
        value = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return value


def _load_minimal_yaml(text: str) -> dict[str, Any]:
    """Parse the subset used by configs/example.yaml without third-party code."""
    lines = text.splitlines()
    meaningful = [
        (index, line)
        for index, line in enumerate(lines)
        if line.strip() and not line.lstrip().startswith("#")
    ]
    root: dict[str, Any] = {}
    stack: list[tuple[int, Any]] = [(-1, root)]
    for position, (line_index, raw_line) in enumerate(meaningful):
        content = raw_line.split("#", 1)[0].strip()
        if not content:
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if content.startswith("- "):
            if not isinstance(parent, list):
                raise ValueError("minimal YAML fallback expected a list parent")
            parent.append(_parse_scalar(content[2:].strip()))
            continue
        key, separator, raw_value = content.partition(":")
        if not separator:
            raise ValueError(f"minimal YAML fallback cannot parse line {line_index + 1}")
        key = key.strip()
        raw_value = raw_value.strip()
        if not isinstance(parent, dict):
            raise ValueError("minimal YAML fallback expected a mapping parent")
        if raw_value:
            parent[key] = _parse_scalar(raw_value)
            continue
        next_item = meaningful[position + 1][1] if position + 1 < len(meaningful) else ""
        next_indent = len(next_item) - len(next_item.lstrip(" "))
        child: Any = [] if next_indent > indent and next_item.lstrip().startswith("- ") else {}
        parent[key] = child
        stack.append((indent, child))
    return root


def _parse_scalar(value: str) -> Any:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
        return value[1:-1]
    if value in {"null", "~"}:
        return None
    if value.lower() in {"true", "false"}:
        return value.lower() == "true"
    try:
        return int(value)
    except ValueError:
        try:
            return float(value)
        except ValueError:
            return value
