# TopoRisk

[English](README.md) | [简体中文](README_zh-CN.md)

**面向智能体工作流的依赖感知验证资源分配**

TopoRisk 研究如何在智能体工作流图中分配有限的审计预算。它不仅依据单个步骤的局部失败概率排序，还估计错误如何沿依赖关系传播到最终输出，并在每次选定审计节点后重新计算其余候选节点的边际价值，从而减少对重叠传播路径的重复计分。

本仓库是一个**研究工件预览版**，包含实现代码、聚合实验结果和复现工具。论文稿件与 LaTeX 源文件暂不公开，本工作也尚未经过同行评审。

完整的评测工件同步发布在 [Hugging Face](https://huggingface.co/datasets/JosephAA/toporisk-evaluation-artifacts)。

## 结果概览

| 评测 | 观察结果 |
|---|---|
| 受控 DAG，10% 审计预算 | 损坏终点比例：局部风险方法为 0.261，TopoRisk 为 0.147 |
| 受控 DAG，20% 审计预算 | 损坏终点比例：局部风险方法为 0.172，TopoRisk 为 0.059 |
| 固定轨迹分配压力测试 | 两种评分器/验证器配置下，成对剩余损失差分别为 -0.526 和 -0.544 |
| Retail 在线试验，DeepSeek Agent | 有、无验证均为 39/45 次成功 |
| Airline 在线试验，DeepSeek Agent | 无验证 41/45，Qwen 全覆盖验证 37/45 |
| Airline 在线试验，GLM Agent | 无验证 40/45，Qwen 全覆盖验证 39/45 |
| GLM 验证器成本 | 78 次保留调用估算为 0.0471 美元；GLM 总成本不可得 |

固定轨迹实验是在冻结上下文上构造双风险情形的分配压力测试，不能被解释为自然错误率或部署安全性的估计。在线试验中的零结果和负结果均被完整保留。GLM 扩展仍使用与主要 Airline 实验相同的 DeepSeek 用户模拟器和 Qwen 验证器，因此它扩大了 Agent 模型覆盖，但不能证明结果与供应商无关。

## 安装

建议使用 Python 3.10 或更高版本。

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## 快速检查

```bash
make test
make verify
make smoke
```

`make smoke` 运行小规模确定性实例，不会访问网络，也不会调用任何模型 API。

## 复现受控实验

完整受控实验是确定性的，但规模明显大于 smoke test：

```bash
make controlled
make figures
```

对应的具体命令记录在 `Makefile` 中。远程模型实验的冻结聚合结果也包含在仓库内，因此检查论文中报告的数值不需要再次产生付费 API 调用。

## 仓库结构

```text
src/                         仿真、分配、绘图与校验代码
tests/                       工作流风险与节点选择的单元测试
results/controlled/          可复现的合成 DAG 实验表格
results/fixed_trace_summary/ 异构验证器固定轨迹压力测试的聚合结果
results/online_summary/      在线成对试验的聚合结果
figures/                     根据聚合结果生成的图表
docs/                        数据来源、范围与限制说明
```

## 数据与隐私

本仓库不包含 API 密钥、`.env` 文件、供应商请求标识、账户信息、原始提示词、模型回复、对话轨迹、论文 PDF 或 LaTeX 源文件。聚合表格中的任务编号仅为本地实验标签。

详细说明见 [`docs/PROVENANCE_AND_SCOPE.md`](docs/PROVENANCE_AND_SCOPE.md)。

## 引用

在论文获得正式标识符之前，可以引用本工件版本：

```bibtex
@misc{yuan2026toporiskartifacts,
  title        = {TopoRisk Evaluation Artifacts},
  author       = {Yuan, Ye},
  year         = {2026},
  howpublished = {GitHub repository and Hugging Face dataset},
  url          = {https://github.com/YYJoseph/TopoRisk},
  note         = {Artifact-first research preview; manuscript not included}
}
```

## 许可证

- `src/` 与 `tests/` 中的代码采用 Apache License 2.0（`LICENSE`）。
- 聚合结果表、图表和文档采用 CC BY 4.0（`LICENSE-DATA-DOCS`）。

许可证不覆盖未收录的上游 benchmark 内容，也不覆盖尚未公开的论文稿件。
