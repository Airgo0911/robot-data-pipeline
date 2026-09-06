"""Episode and manifest quality gates."""

from __future__ import annotations

import math
from collections import Counter
from typing import Any, Iterable, Mapping

from .schema import EpisodeManifest, ValidationIssue


def validate_episode(
    value: Mapping[str, Any],
    *,
    expected_state_dim: int | None = None,
    expected_action_dim: int | None = None,
    expected_camera_order: tuple[str, ...] = (),
) -> list[dict[str, str]]:
    """Return structured issues; do not mutate or discard the input record."""
    episode_id = str(value.get("episode_id", ""))
    issues: list[ValidationIssue] = []
    if not value.get("schema_version"):
        issues.append(
            ValidationIssue(episode_id, "missing_schema_version", "schema_version is required")
        )
    if not episode_id:
        issues.append(ValidationIssue("", "missing_episode_id", "episode_id is required"))
    if not value.get("task"):
        issues.append(ValidationIssue(episode_id, "missing_task", "task is required"))
    try:
        frame_count = int(value.get("frame_count", 0))
    except (TypeError, ValueError):
        frame_count = 0
        issues.append(
            ValidationIssue(episode_id, "invalid_frame_count", "frame_count must be an integer")
        )
    if frame_count <= 0:
        issues.append(
            ValidationIssue(episode_id, "non_positive_frame_count", "frame_count must be positive")
        )

    timestamps = value.get("timestamps")
    if timestamps is not None:
        if not isinstance(timestamps, (list, tuple)):
            issues.append(
                ValidationIssue(
                    episode_id, "invalid_timestamps", "timestamps must be a list or tuple"
                )
            )
        else:
            numeric: list[float] = []
            for item in timestamps:
                try:
                    number = float(item)
                except (TypeError, ValueError):
                    issues.append(
                        ValidationIssue(
                            episode_id,
                            "non_numeric_timestamp",
                            "timestamps must contain finite numbers",
                        )
                    )
                    break
                if not math.isfinite(number):
                    issues.append(
                        ValidationIssue(
                            episode_id,
                            "non_finite_timestamp",
                            "timestamps must contain finite numbers",
                        )
                    )
                    break
                numeric.append(number)
            if len(numeric) > 1 and any(
                right < left for left, right in zip(numeric, numeric[1:])
            ):
                issues.append(
                    ValidationIssue(
                        episode_id,
                        "non_monotonic_timestamps",
                        "timestamps must be monotonic non-decreasing",
                    )
                )
            if numeric and frame_count > 0 and len(numeric) != frame_count:
                issues.append(
                    ValidationIssue(
                        episode_id,
                        "timestamp_length_mismatch",
                        "timestamps length does not equal frame_count",
                        severity="warning",
                    )
                )

    semantics = str(value.get("action_semantics", "unknown"))
    if semantics == "commanded_action":
        pass
    elif semantics in {"next_state_proxy", "unknown"}:
        # next_state_proxy is valid, but remains visible in the audit output.
        pass
    else:
        issues.append(
            ValidationIssue(
                episode_id,
                "unknown_action_semantics",
                f"unsupported action_semantics: {semantics}",
                severity="warning",
            )
        )

    metadata = value.get("metadata") or {}
    if not isinstance(metadata, Mapping):
        issues.append(
            ValidationIssue(episode_id, "invalid_metadata", "metadata must be an object")
        )
        metadata = {}
    if expected_state_dim is not None and metadata.get("state_dim") not in (
        None,
        expected_state_dim,
    ):
        issues.append(
            ValidationIssue(
                episode_id,
                "state_dim_mismatch",
                f"state_dim differs from configured value {expected_state_dim}",
            )
        )
    if expected_action_dim is not None and metadata.get("action_dim") not in (
        None,
        expected_action_dim,
    ):
        issues.append(
            ValidationIssue(
                episode_id,
                "action_dim_mismatch",
                f"action_dim differs from configured value {expected_action_dim}",
            )
        )
    if expected_camera_order:
        cameras = tuple(metadata.get("camera_order") or ())
        if cameras and cameras != expected_camera_order:
            issues.append(
                ValidationIssue(
                    episode_id,
                    "camera_order_mismatch",
                    "camera_order differs from configuration",
                )
            )

    return [item.to_dict() for item in issues]


def validate_manifest(
    records: Iterable[Mapping[str, Any]], **kwargs: Any
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Validate all records and count duplicate ids without changing rows."""
    all_issues: list[dict[str, Any]] = []
    ids: list[str] = []
    for record in records:
        episode_id = str(record.get("episode_id", ""))
        ids.append(episode_id)
        all_issues.extend(validate_episode(record, **kwargs))
    duplicate_counts = Counter(item for item in ids if item)
    for episode_id, count in duplicate_counts.items():
        if count > 1:
            all_issues.append(
                {
                    "episode_id": episode_id,
                    "code": "duplicate_episode_id",
                    "message": f"episode_id occurs {count} times",
                    "severity": "error",
                }
            )
    summary = {
        "records": len(ids),
        "issues": len(all_issues),
        "errors": sum(item["severity"] == "error" for item in all_issues),
        "warnings": sum(item["severity"] == "warning" for item in all_issues),
    }
    return all_issues, summary


def split_quarantine(
    records: Iterable[Mapping[str, Any]], **kwargs: Any
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Split records into accepted and quarantined lists for explicit review."""
    accepted: list[dict[str, Any]] = []
    quarantine: list[dict[str, Any]] = []
    for record in records:
        issues = validate_episode(record, **kwargs)
        if any(item["severity"] == "error" for item in issues):
            quarantine.append(dict(record))
        else:
            accepted.append(dict(record))
    return accepted, quarantine

