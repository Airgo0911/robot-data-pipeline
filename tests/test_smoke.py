from __future__ import annotations

import hashlib
from pathlib import Path

from robot_data_pipeline.convert import build_training_view, plan_pipeline
from robot_data_pipeline.integrity import sha256_file
from robot_data_pipeline.io import read_jsonl
from robot_data_pipeline.quality import validate_episode, validate_manifest


def test_sample_manifest_has_expected_inventory_shape() -> None:
    path = Path(__file__).parents[1] / "examples" / "raw_manifest.jsonl"
    records = list(read_jsonl(path))
    assert len(records) == 3
    assert records[0]["action_semantics"] == "next_state_proxy"


def test_quality_gate_flags_non_monotonic_timestamps() -> None:
    issue_codes = {
        item["code"]
        for item in validate_episode(
            {
                "schema_version": "0.1",
                "episode_id": "bad-1",
                "task": "demo",
                "frame_count": 3,
                "timestamps": [0.0, 0.2, 0.1],
                "action_semantics": "next_state_proxy",
            }
        )
    }
    assert "non_monotonic_timestamps" in issue_codes


def test_manifest_duplicate_ids_are_explicit() -> None:
    rows = [
        {
            "schema_version": "0.1",
            "episode_id": "same",
            "task": "demo",
            "frame_count": 1,
            "timestamps": [0.0],
        },
        {
            "schema_version": "0.1",
            "episode_id": "same",
            "task": "demo",
            "frame_count": 1,
            "timestamps": [0.0],
        },
    ]
    issues, summary = validate_manifest(rows)
    assert summary["errors"] == 1
    assert any(item["code"] == "duplicate_episode_id" for item in issues)


def test_sha256_is_streaming_and_deterministic(tmp_path: Path) -> None:
    path = tmp_path / "payload.bin"
    payload = b"robot-data-pipeline\n"
    path.write_bytes(payload)
    assert sha256_file(path) == hashlib.sha256(payload).hexdigest()


def test_plan_and_training_view_preserve_provenance() -> None:
    manifest = Path("examples/raw_manifest.jsonl")
    plan = plan_pipeline(manifest)
    assert plan.stages == ("raw", "lerobot_v2_1", "dexdata", "training_view")
    view = build_training_view(
        [{"episode_id": "e1", "task": "demo"}],
        action_semantics="next_state_proxy",
    )
    assert view["provenance_preserved"] is True
    assert view["records"][0]["episode_id"] == "e1"
