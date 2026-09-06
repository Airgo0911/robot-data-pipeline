"""Command-line interface for validation, audit, and dry-run planning."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .convert import plan_pipeline
from .integrity import audit_source_paths
from .io import read_jsonl, write_json, write_jsonl
from .quality import validate_manifest
from .schema import PipelineConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="robot-data-pipeline",
        description="Audit and plan a manifest-first robot data pipeline.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate episode metadata")
    _add_manifest_argument(validate)
    validate.add_argument("--config", type=Path, default=None)

    audit = subparsers.add_parser("audit", help="write validation and integrity reports")
    _add_manifest_argument(audit)
    audit.add_argument("--output-dir", type=Path, required=True)
    audit.add_argument("--config", type=Path, default=None)

    dry_run = subparsers.add_parser("dry-run", help="print the stage plan")
    _add_manifest_argument(dry_run)
    dry_run.add_argument("--config", type=Path, default=None)
    return parser


def _add_manifest_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--manifest", type=Path, required=True)


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    records = list(read_jsonl(args.manifest))
    config = _load_config_for_cli(args.config)

    issues, summary = validate_manifest(
        records,
        expected_state_dim=config.state_dim,
        expected_action_dim=config.action_dim,
        expected_camera_order=config.camera_order,
    )
    summary["manifest"] = str(args.manifest)
    summary["action_semantics"] = config.action_semantics

    if args.command == "validate":
        print(json.dumps({"summary": summary, "issues": issues}, ensure_ascii=False, indent=2))
        return 0

    if args.command == "dry-run":
        plan = plan_pipeline(args.manifest, args.config)
        print(json.dumps(plan.to_dict(), ensure_ascii=False, indent=2))
        return 0

    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    integrity = audit_source_paths(records, args.manifest.parent)
    code_counts = Counter(item["code"] for item in issues)
    summary["issue_codes"] = dict(sorted(code_counts.items()))
    summary["integrity_status_counts"] = dict(
        sorted(Counter(item["status"] for item in integrity).items())
    )
    write_json(output_dir / "summary.json", summary)
    write_jsonl(output_dir / "issues.jsonl", issues)
    write_json(output_dir / "integrity.json", integrity)
    print(
        json.dumps(
            {"summary": summary, "output_dir": str(output_dir)},
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


def _load_config_for_cli(path: Path | None) -> PipelineConfig:
    if path is None:
        return PipelineConfig()
    from .io import load_yaml

    return PipelineConfig.from_mapping(load_yaml(path))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())

