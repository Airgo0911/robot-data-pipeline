# Robot Data Pipeline

整理机器人数据处理时用到的检查方法，以及一套可以替换适配器的 Python 小框架。

## 为什么做这个

处理 RoboChallenge Table30 V2 数据时，花了不少时间在格式和字段对齐上。数据经过几次转换，同名字段的含义也可能变了，所以我把各阶段拆开，先记录来源、检查元数据，再接具体的转换逻辑：

```text
Raw export -> LeRobot v2.1 -> DexData -> training view
```

这里的 DexData 是项目使用的中间视图名称。公开仓库保留了这个流程的接口和小样例，真实数据的解码、存储和训练张量构建还需要各自实现。

## 项目背景

原项目的数据处理范围是 30 个任务、32,939 条 episode、45,827,921 帧，处理过程中识别并隔离了 15 条异常 episode。这些数字来自原项目记录，不是运行本仓库样例得到的结果；公开样例只有 3 条人工构造的元数据记录，没有对应的图像或机器人数据文件。

有一个容易混淆的地方：项目使用的是从观测状态构造的 `next_state_proxy`，不能直接当作控制器实际下发的 `commanded_action`。配置里把动作语义单独保留下来，是为了后续接数据和训练时能明确区分。

## 目前能做什么

- 读取 JSONL episode 清单，检查必需标识、正帧数和重复 episode ID。
- 检查已提供的时间戳是否为有限数值、是否单调不减；长度与帧数不同会给出 warning。
- 按配置核对已声明的状态维度、动作维度和相机顺序。这只是元数据对照，不会读取数组验证实际形状。
- 输出带 episode ID、问题代码和严重程度的审计报告。
- 对清单声明的源文件分块计算 SHA-256；有预期摘要时进行比对，并记录缺失文件。
- 打印转换阶段计划；Python API 提供元数据转换占位函数和记录分组工具。

`split_quarantine()` 可以把记录按单条校验结果分成两个列表，但不会移动文件，也不会自动执行清单级的重复 ID 检查。CLI 的 `audit` 只生成报告，不会删除、移动或过滤源数据。

## 快速开始

需要 Python 3.10 或更新版本，建议在虚拟环境中运行。

```bash
git clone https://github.com/Airgo0911/robot-data-pipeline.git
cd robot-data-pipeline
python -m pip install -e .
```

上面的安装包含运行 CLI 所需的 PyYAML。`requirements.txt` 另外列出了真实适配器常用的数据处理库和 pytest，需要时安装：

```bash
python -m pip install -r requirements.txt
```

### 检查样例清单

```bash
python -m robot_data_pipeline.cli validate --manifest examples/raw_manifest.jsonl --config configs/example.yaml
```

第三条记录故意放了倒序时间戳，预期得到 `records: 3`、`errors: 1` 和 `non_monotonic_timestamps`。当前 CLI 即使发现质量错误也返回退出码 0，接自动化流程时要读取输出中的 `errors` 和 `issues`，不能只看进程是否成功退出。

### 保存审计报告

```bash
python -m robot_data_pipeline.cli audit --manifest examples/raw_manifest.jsonl --config configs/example.yaml --output-dir outputs/example
```

生成三个文件：

| 文件 | 内容 |
| --- | --- |
| `summary.json` | 记录数、问题数量、问题代码和文件完整性状态统计 |
| `issues.jsonl` | 每个问题对应的 episode ID、代码、说明及严重程度 |
| `integrity.json` | 声明的源文件路径、检查状态和可读取文件的摘要 |

源文件的相对路径以 manifest 所在目录为基准。样例没有携带源文件，所以 3 条完整性结果均为 `missing`，这是预期结果。源文件存在但未提供预期摘要时，状态为 `unhashed`，报告仍会计算并保存当前摘要；只有与已有摘要比较后，才有 `match` 或 `mismatch`。

### 查看转换计划

```bash
python -m robot_data_pipeline.cli dry-run --manifest examples/raw_manifest.jsonl --config configs/example.yaml
```

这个命令只显示阶段顺序和动作语义，不会生成 LeRobot 数据集或训练张量。`convert.py` 中的 TODO 是接入真实格式的位置。

### 单独计算文件摘要

在仓库根目录运行下面的 Python 代码，可以用现有样例文件试一下：

```python
from pathlib import Path
from robot_data_pipeline.integrity import sha256_file, verify_sha256

path = Path("examples/raw_manifest.jsonl")
digest = sha256_file(path)
print(digest)
assert verify_sha256(path, digest)
```

这个例子只演示 API。实际使用时要提前保存可信的参考摘要，之后再做比对；现算现比不能证明文件在此前没有变化。SHA-256 能帮助发现文件字节变化，不能证明动作标签、时间对齐或任务语义正确。

## 文件放在哪里

```text
configs/example.yaml                  # 阶段、动作语义和预期维度
examples/raw_manifest.jsonl           # 3 条人工构造的样例记录
src/robot_data_pipeline/
  schema.py                          # 清单与配置的数据结构
  quality.py                         # 元数据校验、记录分组
  integrity.py                       # SHA-256 和源文件检查
  convert.py                         # 阶段计划、转换占位接口
  io.py                              # JSONL / YAML 读写
  cli.py                             # validate / audit / dry-run
tests/test_smoke.py                   # 样例路径和基础接口检查
```

配置中的 `project_context` 是原项目的背景记录，不是程序测量值。`quarantine_dir` 目前也只是配置字段，不会触发文件移动。

## 还没接上的部分

- [ ] 真实 Raw / LeRobot v2.1 存储适配器，以及 DexData 字段映射。
- [ ] 图像解码、损坏文件检测和跨相机时间同步检查。
- [ ] 状态与动作数组的逐帧维度、数值范围、单位及坐标系检查。
- [ ] 归一化、序列切片、padding / mask 和训练样本写入。
- [ ] 带复核记录的隔离执行流程，以及各转换阶段的完整来源追踪。

仓库不包含私有数据、模型权重或机器人 SDK，也没有实时流处理支持。样例 JSONL 不是标准 LeRobot 数据集；实现适配器时还需要对照所用版本的 [LeRobot 文档](https://huggingface.co/docs/lerobot)。

## 运行现有检查

安装 `requirements.txt` 后：

```bash
python -m pytest -q
```

这些检查覆盖公开样例和基础接口，不能代替真实数据集的验收。

## 相关记录

- [robotwin-evaluation-tools](https://github.com/Airgo0911/robotwin-evaluation-tools)：RoboTwin 评测工具。
- [vla-paper-reading-notes](https://github.com/Airgo0911/vla-paper-reading-notes)：VLA 论文阅读笔记。

## License

[MIT](LICENSE)
