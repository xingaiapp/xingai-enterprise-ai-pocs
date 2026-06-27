# ADR-001：Supervisor 编排、审计链路与人工复核

**状态：** Accepted  
**日期：** 2026-06-17  
**作者：** Xing @ XingAI  
**取代：** —  
**被取代：** —  
**语言：** [English](001-supervisor-audit-human-in-the-loop.md) · 中文

## 背景

`xingai-enterprise-ai-pocs` 在产品化之前，为未来的 **XingAI Enterprise Agent Platform** 验证架构模式。早期 POC（`multi-agent-lab`、`claims-multiagent-rag-poc`）面临相同的治理问题：

- 自由 Agent 群难以测试、审计，也难以向非技术干系人解释。
- 无文档引用的纯 LLM 决策在保险、金融等受监管场景不可接受。
- 高风险结果必须路由给人 — 不能静默自动批准。

需要一份仓库级 ADR，让每个 POC 满足同一最低标准。

## 决策

### 1. Supervisor 模式（非 Agent 群）

每个可运行 POC 使用**显式编排器** — LangGraph 状态机或等价物：

- 每一步只有一个 specialist agent 处于活动状态。
- 状态为在节点间传递的类型化对象（Pydantic / TypedDict）。
- 条件边处理升级（如 intake 置信度低 → 人工复核）。
- 图定义文件必须适合现场 demo 屏幕共享阅读。

Agent **不得**绕过 Supervisor 随意互调。

### 2. 只追加审计链路

每个 agent 步骤记录：

- `trace_id`（关联一次端到端运行）
- Agent 名称
- 脱敏后的 input / output JSON
- 可选 metadata（backend、延迟、工具名）
- UTC 时间戳

存储：POC 用 SQLite 只追加表；生产路径为不可变合规存储。

**PII：** 任何日志写入前 `redact()` 剥离类 SSN 模式。POC 仅使用合成数据。

### 3. 人工复核阈值

阈值配置驱动（YAML — 代码中无 magic number）：

| 信号 | POC 默认行为 |
|------|----------------|
| 抽取 / 决策置信度低 | `ESCALATE_TO_HUMAN` |
| 欺诈 / 风险分数高 | 升级 — **不因欺诈单独自动拒赔** |
| 金额超阈值 | 无论模型多自信都升级 |
| 检索或 LLM 失败 | 带错误原因升级 — 不静默猜测 |

当 `require_policy_citation: true` 时，裁决 agent 对 APPROVE/DENY 必须引用至少一份源文档。

### 4. RAG 引用纪律

使用检索时：

- 按域分集合（保单 / 历史 / 法规 — 不混用）。
- 下游 agent 看到的每个 chunk 带 `document_id`、`chunk_id`、相似度分数。
- 无引用 metadata 的检索文本不得进入后续 agent。

### 5. 可观测性

POC 最低可观测性：

- 带 `trace_id` 的结构化 JSON 日志
- 有 API key 时接 LangSmith 或 OpenTelemetry
- 决策准确率 golden-set 评估（合成 fixture 目标 ≥ 80%）

### 6. POC 文档要求

每个 POC 目录包含：`README.md`、`architecture.md`、`enterprise-mapping.md`、`flow.mmd`、`references.md`，见 [POC-STANDARDS.md](../POC-STANDARDS.md)。

## 备选方案

- **单一巨型 prompt** — 拒绝（不可测试、无审计粒度）。
- **共享记忆的 Agent 群** — Phase 1 拒绝（企业评审难解释）。
- **欺诈即自动拒赔** — 拒绝（责任风险；改为升级）。

## 后果

正面：保险、创意等垂直 POC demo 叙事一致；可映射到 Platform 编排器 + 审计 + 审批队列。

代价：每个 POC 更多样板（graph、audit、config YAML、golden eval）。

## 实现状态

- [x] ADR-001 文档
- [x] `multi-agent-lab` — trace 时间线 + orchestrator
- [x] `claims-multiagent-rag-poc` — LangGraph supervisor + SQLite audit + golden eval
- [ ] Platform 服务抽取（Phase 2）

## 相关

- [Enterprise Agent Platform](../ENTERPRISE-AGENT-PLATFORM.zh.md)
- [POC Standards](../POC-STANDARDS.md)
- [Claims POC](../../pocs/claims-multiagent-rag-poc/)
- [Multi-Agent Lab](../../pocs/multi-agent-lab/)
- Invest AI [ADR-028](https://github.com/xingaiapp/xingai-invest-ai/blob/main/docs/adr/028-robinhood-mcp-execution-gates.zh.md)
