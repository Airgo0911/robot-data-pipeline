"""Run the public sample without private robot or dataset dependencies."""

from __future__ import annotations

import json
from pathlib import Path

from robot_data_pipeline.convert import build_training_view, plan_pipeline
from robot_data_pipeline.io import load_yaml, read_jsonl
from robot_data_pipeline.quality import validate_manifest


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    manifest_path = root / "examples" / "raw_manifest.jsonl"
    config_path = root / "configs" / "example.yaml"

    records = list(read_jsonl(manifest_path))
    config = load_yaml(config_path)
    issues, summary = validate_manifest(
        records,
        expected_state_dim=config.get("state_dim"),
        expected_action_dim=config.get("action_dim"),
        expected_camera_order=tuple(config.get("camera_order") or ()),
    )
    plan = plan_pipeline(manifest_path, config_path)
    view = build_training_view(
        records, action_semantics=str(config.get("action_semantics"))
    )

    print(json.dumps({"summary": summary, "plan": plan.to_dict()}, ensure_ascii=False, indent=2))
    print(f"training_view records: {view['record_count']}")
    if issues:
        print(f"quality issues: {len(issues)} (see audit output for quarantine decisions)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

