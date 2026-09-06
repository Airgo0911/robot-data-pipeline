"""Versioned, dependency-light data contracts.

The public scaffold keeps the contract small on purpose. Real adapters can add
fields, but should preserve the provenance and action-semantics fields.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class EpisodeManifest:
    """Episode-level metadata emitted by every pipeline stage."""

    schema_version: str
    episode_id: str
    task: str
    frame_count: int
    timestamps: tuple[float, ...] = ()
    action_semantics: str = "unknown"
    source_path: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "EpisodeManifest":
        """Build a typed record without guessing missing values."""
        raw_timestamps = value.get("timestamps") or ()
        return cls(
            schema_version=str(value.get("schema_version", "")),
            episode_id=str(value.get("episode_id", "")),
            task=str(value.get("task", "")),
            frame_count=int(value.get("frame_count", 0)),
            timestamps=tuple(float(item) for item in raw_timestamps),
            action_semantics=str(value.get("action_semantics", "unknown")),
            source_path=value.get("source_path"),
            metadata=dict(value.get("metadata") or {}),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "schema_version": self.schema_version,
            "episode_id": self.episode_id,
            "task": self.task,
            "frame_count": self.frame_count,
            "timestamps": list(self.timestamps),
            "action_semantics": self.action_semantics,
            "source_path": self.source_path,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ValidationIssue:
    """A stable issue record suitable for JSONL audit output."""

    episode_id: str
    code: str
    message: str
    severity: str = "error"

    def to_dict(self) -> dict[str, str]:
        return {
            "episode_id": self.episode_id,
            "code": self.code,
            "message": self.message,
            "severity": self.severity,
        }


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration fields shared by the example stages."""

    schema_version: str = "0.1"
    action_semantics: str = "next_state_proxy"
    camera_order: tuple[str, ...] = ()
    state_dim: int | None = None
    action_dim: int | None = None
    quarantine_dir: str = "outputs/quarantine"
    stages: tuple[str, ...] = (
        "raw",
        "lerobot_v2_1",
        "dexdata",
        "training_view",
    )

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "PipelineConfig":
        return cls(
            schema_version=str(value.get("schema_version", "0.1")),
            action_semantics=str(
                value.get("action_semantics", "next_state_proxy")
            ),
            camera_order=tuple(value.get("camera_order") or ()),
            state_dim=_optional_int(value.get("state_dim")),
            action_dim=_optional_int(value.get("action_dim")),
            quarantine_dir=str(value.get("quarantine_dir", "outputs/quarantine")),
            stages=tuple(
                value.get("stages")
                or ("raw", "lerobot_v2_1", "dexdata", "training_view")
            ),
        )


def _optional_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    return int(value)


def normalise_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    """Copy a mapping while normalising only fields owned by this contract."""
    record = dict(value)
    record.setdefault("schema_version", "0.1")
    record.setdefault("action_semantics", "unknown")
    record.setdefault("metadata", {})
    return record


def ensure_sequence(value: Any) -> Sequence[Any]:
    """Return a sequence for shape checks without coercing arbitrary objects."""
    if isinstance(value, (list, tuple)):
        return value
    return ()

