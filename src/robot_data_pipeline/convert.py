"""Stage contracts and dry-run conversion helpers.

The conversion functions return metadata-only placeholders. Real projects should
implement source-specific adapters where the TODO markers are located.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .io import load_yaml
from .schema import PipelineConfig


@dataclass(frozen=True)
class PipelinePlan:
    manifest: str
    stages: tuple[str, ...]
    action_semantics: str
    notes: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "manifest": self.manifest,
            "stages": list(self.stages),
            "action_semantics": self.action_semantics,
            "notes": list(self.notes),
        }


def load_config(path: Path | None) -> PipelineConfig:
    if path is None:
        return PipelineConfig()
    return PipelineConfig.from_mapping(load_yaml(path))


def plan_pipeline(manifest_path: Path, config_path: Path | None = None) -> PipelinePlan:
    """Describe the conversion order without touching private data."""
    config = load_config(config_path)
    return PipelinePlan(
        manifest=str(manifest_path),
        stages=config.stages,
        action_semantics=config.action_semantics,
        notes=(
            "Decode Raw records with a versioned adapter.",
            "Validate and write the LeRobot v2.1-compatible view.",
            "Map fields into the project DexData intermediate view.",
            "Slice, pad, mask, and retain provenance in the training view.",
            "Quarantine anomalies instead of silently deleting them.",
        ),
    )


def convert_raw_to_lerobot(
    records: Iterable[Mapping[str, Any]], config: PipelineConfig
) -> list[dict[str, Any]]:
    """Return a metadata-only LeRobot stage placeholder.

    TODO: replace the body with the exact LeRobot v2.1 feature/storage adapter
    used by the experiment. Do not infer camera order, action units, or labels.
    """
    converted: list[dict[str, Any]] = []
    for record in records:
        output = dict(record)
        output["stage"] = "lerobot_v2_1"
        output["schema_version"] = config.schema_version
        output["action_semantics"] = config.action_semantics
        output["provenance"] = {
            "source_episode_id": record.get("episode_id"),
            "source_stage": "raw",
        }
        converted.append(output)
    return converted


def convert_to_dexdata(
    records: Iterable[Mapping[str, Any]], config: PipelineConfig
) -> list[dict[str, Any]]:
    """Map normalized records to a versioned DexData interface placeholder.

    TODO: implement dexterous state/action packing, calibration transforms,
    and any camera or gripper conventions owned by the real project.
    """
    output_rows: list[dict[str, Any]] = []
    for record in records:
        output = dict(record)
        output["stage"] = "dexdata"
        output["provenance"] = {
            **dict(record.get("provenance") or {}),
            "source_stage": record.get("stage", "lerobot_v2_1"),
        }
        output_rows.append(output)
    return output_rows


def build_training_view(
    records: Sequence[Mapping[str, Any]], *, action_semantics: str
) -> dict[str, Any]:
    """Describe a model-ready view while leaving tensor construction explicit.

    TODO: implement normalization statistics, sequence windows, padding, masks,
    and storage writes. Every resulting sample should retain episode/frame ids.
    """
    return {
        "stage": "training_view",
        "record_count": len(records),
        "action_semantics": action_semantics,
        "tensorization": "TODO: project-specific arrays and masks",
        "provenance_preserved": True,
        "records": [
            {
                "episode_id": item.get("episode_id"),
                "task": item.get("task"),
            }
            for item in records
        ],
    }

