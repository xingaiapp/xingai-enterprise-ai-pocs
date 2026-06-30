# ADR-004：事件总线 AI 审核 — 仅设计阶段占位策略

**日期：** 2026-06-28  
**状态：** 已接受  
**作者：** Xing @ XingAI  
**英文：** [004-event-bus-ai-review-placeholder.md](./004-event-bus-ai-review-placeholder.md)

## 背景

[事件总线 AI 审核](../../pocs/event-bus-ai-review/) 目前**仅架构设计**，目标流：

```text
event → AI 审核 → 合规审核 → 人工批准 → 审计日志
```

可运行 POC 为 Multi-Agent Lab 与理赔 RAG。需明确事件总线如何达到 [ADR-001](./001-supervisor-audit-human-in-the-loop.zh.md) 同等治理，且不演示「AI 自动放行」。

## 决策

### 1. 实现前保持设计-only

| 产物 | 现在 | 实现前禁止 |
|------|------|------------|
| architecture.md、flow.mmd | 允许 | — |
| 幻灯片模拟 trace | 允许，标 **设计预览** | — |
| 可运行队列消费者 | 否 | 需新 ADR |
| AI 审核后自动执行 | **禁止** | — |

### 2. 占位规则

| 规则 | 要求 |
|------|------|
| **E1 独立 worker** | AI 与合规为**独立订阅者** — 合规不得藏在 AI prompt 里 |
| **E2 人工门控** | 人工节点通过前无副作用（ADR-001） |
| **E3 追加审计** | 每步记录 event id、worker、脱敏 I/O、时间、审批结果 |
| **E4 故障隔离** | 单 worker 失败不删原事件与既有审计 |
| **E5 禁止静默写** | POC 桩仅 `WOULD_ACT`（同 ADR-003） |

### 3. 与 Orchestrator / Gateway

事件总线负责 fan-out；外部系统写仍走 MCP Gateway ALLOW/DENY；**不要**第三个「Orchestration MCP」。

### 4. 何时实现

满足任一：外部 webhook/队列需异步 handoff；企业客户明确要求事件驱动审核；需第二个独立合规 worker。

此前保持 `event-bus-ai-review/` 为设计参考。

## 备选

- 立即上 Kafka POC — 拒绝
- 并入 Claims LangGraph — 拒绝（同步 supervisor 已够演示）
- 仅 wiki 无 ADR — 拒绝

## 后果

正面：叙事诚实、清单就绪。代价：暂无可运行事件总线 demo。

## 相关

- [ADR-001](./001-supervisor-audit-human-in-the-loop.zh.md)
- [ADR-003 MCP 占位](./003-mcp-gateway-placeholder-policy.zh.md)
- [事件总线架构](../../pocs/event-bus-ai-review/architecture.md)
