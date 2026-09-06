"""Streaming SHA-256 helpers for large recordings and manifests."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Iterable, Mapping


def sha256_file(path: Path, chunk_size: int = 1024 * 1024) -> str:
    """Hash a file in bounded chunks instead of loading it into memory."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(chunk_size):
            digest.update(chunk)
    return digest.hexdigest()


def verify_sha256(path: Path, expected: str) -> bool:
    """Return False for a missing path or a mismatching digest."""
    if not path.is_file():
        return False
    return sha256_file(path).lower() == expected.lower()


def audit_source_paths(
    records: Iterable[Mapping[str, Any]], manifest_dir: Path
) -> list[dict[str, Any]]:
    """Audit declared source paths without silently dropping missing files."""
    results: list[dict[str, Any]] = []
    for record in records:
        source = record.get("source_path")
        episode_id = str(record.get("episode_id", ""))
        if not source:
            results.append(
                {
                    "episode_id": episode_id,
                    "status": "missing_declaration",
                    "path": None,
                }
            )
            continue
        candidate = Path(str(source))
        if not candidate.is_absolute():
            candidate = manifest_dir / candidate
        expected = record.get("sha256")
        if not candidate.is_file():
            results.append(
                {
                    "episode_id": episode_id,
                    "status": "missing",
                    "path": str(candidate),
                }
            )
        elif expected:
            status = "match" if verify_sha256(candidate, str(expected)) else "mismatch"
            results.append(
                {
                    "episode_id": episode_id,
                    "status": status,
                    "path": str(candidate),
                    "sha256": sha256_file(candidate),
                }
            )
        else:
            results.append(
                {
                    "episode_id": episode_id,
                    "status": "unhashed",
                    "path": str(candidate),
                    "sha256": sha256_file(candidate),
                }
            )
    return results

