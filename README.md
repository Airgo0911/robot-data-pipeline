# robot-data-pipeline

> A reproducible, manifest-first data pipeline skeleton for dual-arm, multi-task VLA experiments.

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

This repository is a public, lightweight engineering scaffold for showing how robot demonstrations move from raw exports to a training-ready view. It is deliberately independent of private datasets, robot credentials, model weights, and vendor-specific SDKs. The adapters are small enough to replace with the schemas used by a real project.

## 中文简介

这是一个面向双臂、多任务 VLA 实验的数据处理 pipeline 展示仓库。它把 Raw、LeRobot v2.1、项目内部的 DexData 中间视图和 training view 拆成可审计的阶段，并提供 manifest 校验、异常隔离、SHA-256 完整性检查和 dry-run CLI。公开代码不携带私有数据或模型权重，示例中的转换函数通过 TODO 标出需要按真实数据格式实现的适配点。

与 RoboChallenge Table30 V2 对应的事实口径是：30 个任务、32,939 个 episode、45,827,921 个 frame，隔离 15 个异常 episode；训练环境记录为 8×A100、BF16、ZeRO-3；动作目标是 next-state proxy，而不是 commanded action。仓库不声称官方排名、官方榜单分数或真实 W1 成功率。

## Project context

The scaffold mirrors the data path used in the RoboChallenge Table30 V2 project:

~~~text
Raw export -> LeRobot v2.1 view -> DexData intermediate view -> training view
~~~

The project record that motivated this repository contains the following evidence-bound facts:

| Item | Recorded value | Interpretation |
| --- | ---: | --- |
| Tasks | 30 | Multi-task collection/conversion scope |
| Episodes | 32,939 | Episode records counted in the project inventory |
| Frames | 45,827,921 | Frame count recorded for the inventory |
| Anomalies | 15 episodes | Isolated for audit; not silently deleted |
| Training hardware | 8 x A100 80 GB | BF16 distributed training with ZeRO-3 |
| Action semantics | next-state proxy | Observation-derived proxy; **not commanded action** |

These numbers describe the project inventory and training setup, not a promise that this public skeleton contains the original data. It also does not claim an official competition rank, official leaderboard score, real-robot W1 success rate, or ownership of the original dataset. The real W1 run was pending platform scheduling at the time of the resume audit.

## Why a data pipeline repository?

VLA experiments often fail before model training starts: camera order changes, timestamps are not monotonic, actions are interpreted with the wrong semantics, or an episode is copied incompletely. A useful pipeline should make those assumptions visible and auditable.

This repository demonstrates five practices:

1. **Manifest-first metadata**: every conversion records schema version, source, episode id, frame count, and action semantics.
2. **Explicit adapters**: Raw, LeRobot v2.1, DexData, and training views are separate stages rather than a single opaque script.
3. **Quality gates**: malformed records, non-finite values, non-monotonic timestamps, and shape mismatches are reported with an episode id.
4. **Isolation instead of deletion**: suspect episodes are moved to a quarantine manifest so the denominator can be explained later.
5. **Integrity evidence**: files can be hashed with SHA-256 and re-checked before training.

The implementation is intentionally partial. The conversion functions show the contracts and the order of operations; project-specific decoding, camera calibration, robot kinematics, and storage backends belong in adapters owned by the experiment.

## Features

- JSONL input/output for a dependency-light example path.
- Optional YAML configuration for repeatable runs.
- Episode-level validation with structured issue codes.
- SHA-256 hashing in bounded chunks, suitable for large recordings.
- Dry-run conversion plan that explains each stage without requiring private data.
- Training-view metadata with padding/mask and action-semantics fields.
- CLI commands for validation, audit, and dry-run planning.
- Unit-testable pure functions and a small example dataset.

## Data contract and semantics

### Stage definitions

The stage names are intentionally explicit. They should not be treated as interchangeable:

- **Raw**: source recordings or exports. The repository does not assume a vendor schema. An adapter must declare how images, proprioception, timestamps, task labels, and actions are decoded.
- **LeRobot v2.1 view**: a normalized dataset view intended to follow the relevant LeRobot v2.1 conventions. Before publishing a dataset, validate the exact version-specific feature names and storage layout against the official LeRobot documentation. This repository provides a metadata contract, not a claim that its sample JSONL is an official LeRobot dataset.
- **DexData**: the intermediate hand/dexterous-manipulation view used by the project. In this public skeleton it is an internal interface name, not an assertion about a public or vendor-owned schema. Keep a versioned adapter if the real project changes fields.
- **Training view**: model-ready records after normalization, sequence slicing, padding, and masks. It is not the same as the source data and must retain provenance back to episode and frame ids.

### Action semantics

The example config uses the value next_state_proxy to make a critical distinction visible. A next-state proxy is derived from consecutive observations, for example a difference between pose or joint states. It is **not** the command sent to a controller and must not be described as commanded action in a paper, resume, or interview. If commanded actions are available, set action_semantics to commanded_action and document the controller, units, clipping, and coordinate frame.

### Required episode fields

The minimal JSONL record accepted by the example validator is:

~~~json
{
  "schema_version": "0.1",
  "episode_id": "task_000_seed000_000",
  "task": "place_object",
  "frame_count": 32,
  "timestamps": [0.0, 0.1, 0.2],
  "action_semantics": "next_state_proxy",
  "source_path": "raw/task_000/episode_000.jsonl",
  "metadata": {
    "camera_order": ["wrist_left", "wrist_right", "overhead"],
    "state_dim": 14,
    "action_dim": 14
  }
}
~~~

For a production pipeline, store frame-level data in Parquet, Zarr, HDF5, or the official dataset format and keep this episode manifest alongside it. Do not infer success, action semantics, or coordinate frames from a filename.

### Quality and denominator rules

An episode is not automatically valid because a file exists. The validation stage should check, as applicable:

- task and episode ids are present and unique;
- frame count is positive and agrees with the decoded arrays;
- timestamps are finite and monotonic;
- camera names and ordering match the declared schema;
- state/action arrays have the declared dimensions;
- action values use documented units and coordinate frames;
- terminal and success labels have a defined source;
- no NaN or Inf reaches the training view.

Invalid records are written to the quarantine report. The report must preserve the original id and issue code so that a later success-rate or sample-count denominator can be reconstructed.

## Repository layout

~~~text
robot-data-pipeline/
├── configs/
│   └── example.yaml
├── examples/
│   ├── config/
│   │   └── example.yaml
│   ├── raw_manifest.jsonl
│   └── run_pipeline.py
├── src/
│   └── robot_data_pipeline/
│       ├── __init__.py
│       ├── cli.py
│       ├── convert.py
│       ├── integrity.py
│       ├── io.py
│       ├── quality.py
│       └── schema.py
├── tests/
│   └── test_smoke.py
├── .gitignore
├── LICENSE
├── pyproject.toml
├── requirements.txt
└── README.md
~~~

## Requirements

- Python 3.10 or newer.
- A local filesystem for the example path.
- For real data, install the storage/robot SDK required by the source format separately. No private SDK, data, checkpoint, or robot credentials are included here.

The pinned ranges in requirements.txt are for a convenient research environment; update them with the target CUDA/PyTorch and dataset stack used by the experiment.

## Installation

~~~bash
git clone https://github.com/Airgo0911/robot-data-pipeline.git
cd robot-data-pipeline

python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -e .
~~~

## Quick start

The sample manifest is intentionally tiny and contains no images or robot data. It is enough to exercise the validation and planning code.
The third record intentionally has a non-monotonic timestamp so the audit output demonstrates an explicit quality issue and quarantine candidate; it is not a hidden deletion.

### Validate a manifest

~~~bash
python -m robot_data_pipeline.cli validate \
  --manifest examples/raw_manifest.jsonl
~~~

### Run an audit and write reports

~~~bash
python -m robot_data_pipeline.cli audit \
  --manifest examples/raw_manifest.jsonl \
  --output-dir outputs/example
~~~

The audit writes summary.json, issues.jsonl, and integrity.json when file paths are available. A missing source_path is reported as a warning rather than hidden.

### Print a conversion plan

~~~bash
python -m robot_data_pipeline.cli dry-run \
  --manifest examples/raw_manifest.jsonl \
  --config configs/example.yaml
~~~

On Windows PowerShell, the same commands can be written on one line.

### Use the Python API

~~~python
from pathlib import Path

from robot_data_pipeline.convert import build_training_view, plan_pipeline
from robot_data_pipeline.io import read_jsonl
from robot_data_pipeline.quality import validate_episode

records = list(read_jsonl(Path("examples/raw_manifest.jsonl")))
issues = [validate_episode(item) for item in records]
plan = plan_pipeline(Path("examples/raw_manifest.jsonl"), Path("configs/example.yaml"))
training_view = build_training_view(records, action_semantics="next_state_proxy")

print(plan.stages)
print(sum(len(item) for item in issues), "issue groups")
print(training_view["record_count"])
~~~

The functions return metadata and placeholders rather than silently inventing arrays. Replace the marked adapter functions before using a real dataset.

## Configuration

configs/example.yaml records the stage names, expected dimensions, action semantics, quarantine policy, and project inventory notes. A minimal configuration looks like:

~~~yaml
schema_version: "0.1"
action_semantics: "next_state_proxy"
camera_order:
  - wrist_left
  - wrist_right
  - overhead
state_dim: 14
action_dim: 14
quarantine_dir: "outputs/quarantine"
stages:
  - raw
  - lerobot_v2_1
  - dexdata
  - training_view
~~~

Keep the project inventory values in a separate experiment manifest when the pipeline is used for a real run. Do not overwrite measured counts with estimates.

The same minimal schema is copied to examples/config/example.yaml so a reviewer can inspect the example without opening the project-level configuration directory. Keep the two files synchronized when changing the public demo.

## Adapting this scaffold to real data

1. Implement a RawAdapter that decodes the source recording and emits one episode manifest plus frame arrays.
2. Add a versioned LeRobot adapter. Check feature names, dtype, image encoding, and episode indexing against the exact LeRobot v2.1 release used by the experiment.
3. Define the DexData schema in a checked-in document. Record whether actions are commanded, next-state proxy, or another target.
4. Add camera calibration and coordinate-frame transforms as explicit, tested functions. Never hide a reorder or unit conversion in a dataloader.
5. Add a training-view builder that performs normalization, sequence slicing, padding, and masks while retaining provenance ids.
6. Run audit before and after conversion, and quarantine anomalies with an explanation.
7. Store code version, config hash, dataset manifest hash, checkpoint, and hardware details with the training run.

## Example implementation notes

The code intentionally leaves several project-specific decisions as TODOs:

- camera decoding and image compression;
- robot-specific joint/pose conventions;
- action clipping and gripper encoding;
- episode success/termination labels;
- Parquet/Zarr/HDF5 or LeRobot storage;
- distributed sharding and worker retry policy.

This keeps the public repository honest and makes the boundaries visible during an interview. It is better to say “the adapter is the integration point” than to present a fabricated benchmark result.

## Reproducibility checklist

Before reporting a dataset or training result, archive:

- source manifest and schema version;
- exact commit and configuration hash;
- raw/normalized/training-view counts;
- quarantined episode ids and issue codes;
- SHA-256 hashes for large artifacts;
- action semantics, dimensions, units, and coordinate frames;
- camera order and calibration revision;
- random seeds and data split;
- hardware, software, CUDA, and mixed-precision settings.

For the RoboChallenge project context, the defensible wording is: “I processed a 30-task inventory of 32,939 episodes and 45,827,921 frames, isolated 15 anomalous episodes, and prepared a LeRobot v2.1 -> DexData -> training-view path. The training setup used 8×A100 with BF16/ZeRO-3. The recorded action target was a next-state proxy, not commanded action.” Avoid extending that statement to an official rank or real-robot success rate without a corresponding receipt.

## Testing

~~~bash
python -m pytest -q
~~~

The smoke tests only check the public contract and sample path. Add dataset-specific tests before accepting a training run.

## License

MIT. See LICENSE.

## Citation / acknowledgement

If this scaffold is useful in a portfolio, cite the repository commit and the exact experiment manifest rather than copying the project inventory as if it were a public benchmark result. See the official [LeRobot documentation](https://huggingface.co/docs/lerobot) when implementing a production adapter.
