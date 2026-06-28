# ADR-003：POC 阶段 MCP Gateway 占位策略

**日期：** 2026-06-27  
**状态：** 已接受  
**作者：** Xing @ XingAI  
**英文：** [003-mcp-gateway-placeholder-policy.md](./003-mcp-gateway-placeholder-policy.md)

## 背景

[企业 Agent 平台](../ENTERPRISE-AGENT-PLATFORM.zh.md) 区分 **Orchestrator Agent**（专业 Agent 间工作流）与 **MCP Gateway**（工具路由与 ALLOW/DENY 治理）。Phase 1 POC（`multi-agent-lab`、理赔 RAG）尚无真实网关 — Agent 可能直连工具或使用 registry 桩。

需明确：POC 是否应做第三个「Orchestration MCP」，还是 Agent 直连 GitHub/Jira/SharePoint MCP。

## 决策

### 1. 两个内部系统 — 不要第三个 Orchestration MCP

| 系统 | 编排对象 | 是否 MCP | POC 现状 |
|------|----------|----------|----------|
| **Supervisor / Orchestrator** | 专业 **Agent** | 否 | Claims LangGraph；Lab orchestrator |
| **MCP Gateway** | 跨领域 **工具** | 网关对内可暴露 MCP | **占位** — registry + trace DENY |
| **领域 MCP** | 单个企业系统 | 是 | `MCP_REGISTRY` 桩 |

**反模式（禁止）：** 用 monolithic「Orchestration MCP」跑完整多 Agent 工作流。

### 2. POC 占位规则

在 `mcp-tool-gateway/` 落地前：

| 规则 | 要求 |
|------|------|
| **P1 Registry** | 列出工具名、领域、read/write、桩/ live |
| **P2 禁止静默写** | 写工具仅 `WOULD_CALL` 日志 |
| **P3 Trace 形态** | 演示含 Gateway 步 `ALLOW`/`DENIED` + 角色 |
| **P4 Agent 隔离** | 文档化角色 × 领域前缀 |
| **P5 人工门控** | 高风险写走 [ADR-001](./001-supervisor-audit-human-in-the-loop.zh.md) 人工审核 |

理赔 RAG：检索用本地向量库（[ADR-002](./002-rag-vector-store-production-path.zh.md)）；生产先 MCP **只读** 政策系统。

### 3. Phase 2 网关（规划）

`mcp-tool-gateway/`：策略引擎、审计日志、默认拒绝 + POC profile 白名单。POC 不得复制网关逻辑。

### 4. 目标安全路径

```text
用户 → 认证 → Orchestrator → 专业 Agent → MCP Gateway → 领域 MCP → 企业系统
```

POC 捷径：Orchestrator → Agent → **桩 Gateway trace** → 本地工具/mock（README 标明「治理预览」）。

## 备选

- Agent 直连多 MCP — 无集中 DENY，拒绝。
- 先做完整网关再做 POC — 拖慢演示，拒绝。
- Orchestration MCP 包 LangGraph — 混淆 Agent/工具边界，拒绝。

## 后果

正面：对外叙事一致；Phase 2 有迁移目标。  
代价：Phase 1 网关为**模拟**，非生产 MCP。

## 实现状态

- [x] ADR-003 文档
- [x] multi-agent-lab `MCP_REGISTRY`
- [ ] 共享 `mcp-tool-gateway/`
- [ ] Claims 政策系统 MCP 读桩

## 相关

- [ADR-001 Supervisor 与审计](./001-supervisor-audit-human-in-the-loop.zh.md)
- [企业 Agent 平台](../ENTERPRISE-AGENT-PLATFORM.zh.md)
