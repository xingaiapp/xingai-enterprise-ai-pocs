# XingAI 企业 Agent 平台架构

## 从 AI Chatbot 到企业数字劳动力

| 字段 | 值 |
|---|---|
| 版本 | 0.1 |
| 状态 | 草案 |
| 所有者 | XingAI |
| 受众 | 架构师、工程经理、CTO、产品负责人 |

---

## 执行摘要

大多数组织正在试验 AI 助手，但单个 AI 助手无法支撑复杂的企业工作流。

XingAI Enterprise 引入 **Agent-Oriented Architecture (AOA)**：专业 AI Agent 像人类团队一样协作。

平台能力包括：专业 Agent、Agent 协作、工具集成、MCP 集成、事件驱动、企业治理、可审计、可观测。

**Multi-Agent Lab POC** 是 **MVP 验证层** —— 该架构的第一个可运行里程碑。

```text
今天：Multi-Agent POC（Phase 1）
明天：XingAI Enterprise Agent Platform
```

---

## 愿景

将 AI 从「问题 → 答案」升级为：

```text
目标 → 规划 → Agent 协作 → 工具执行 → 决策 → 行动
```

---

## 企业参考架构

```text
用户界面（Web / Mobile / Teams / Slack）
        ↓
Orchestrator Agent（企业大脑）
        ↓
Research / Product / Support / Tech / Data / Security Agents
        ↓
MCP 层（内外部工具网关）
        ↓
企业系统（APIM、CRM、SharePoint、ServiceNow、Jira、GitHub、SAP…）
```

---

## Orchestrator 与 MCP Gateway

![Orchestrator 与 MCP Gateway — 企业 Agent 平台 UX](../assets/orchestrator-vs-mcp-gateway-ux.png)

团队常问：*有了 GitHub、Jira、SharePoint MCP，是否还需要 **Orchestration MCP**？*

**不需要。** 企业级需要 **两个内部系统**，而不是第三个叫「Orchestration MCP」的 MCP：

| 系统 | 编排对象 | 是否 MCP | 阶段 |
|------|----------|----------|------|
| **Orchestrator Agent** | 其他 **Agent**（Research → Product → Tech） | 否 | Phase 1 — [Multi-Agent Lab](../pocs/multi-agent-lab/) |
| **MCP Gateway** | 跨领域 MCP 的 **工具** | 网关对内可暴露 MCP 接口 | Phase 2 — `mcp-tool-gateway`（规划中） |
| **领域 MCP** | 单个企业系统（GitHub、Jira、SharePoint…） | 是 | Phase 2+ |

```text
工作流编排  →  Orchestrator Agent
工具编排    →  MCP Gateway
系统集成    →  领域 MCP 服务器
```

**安全路径：**

```text
用户 → 认证 → Orchestrator Agent → 专业 Agent → MCP Gateway → 领域 MCP → 企业系统
```

**避免：** Agent 直连多个 MCP，或用「Orchestration MCP」跑完整工作流。

**Trace 示例（Gateway DENY 体现治理）：**

```text
[1] Orchestrator Agent     · 规划 handoff
[2] Research Agent         · sharepoint.search_documents
[3] MCP Gateway            · ALLOW  · sharepoint.*
[4] SharePoint MCP         · 结果
[5] Tech Agent             · jira.create_issue
[6] MCP Gateway            · DENIED · Tech Agent 不可用 jira:*
[7] Tech Agent             · github.search_code
[8] MCP Gateway            · ALLOW  · github.*
[9] GitHub MCP             · 结果
[10] Orchestrator Agent    · 最终答案
```

完整 5W 说明与反模式：

- EN: [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md)
- 中文: [Orchestrator 与 MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md)

---

## POC 与平台映射

| Phase 1（当前 POC） | Phase 2+（企业平台） |
|---|---|
| 4 个专业 Agent | Agent Registry |
| SQLite Trace | 审计存储 + 可观测管道 |
| fake_research_tool | MCP → 企业系统 |
| 同步流水线 | Event Bus + 异步 Worker |
| 单租户 Demo | 多租户 RBAC |
| 仅 Session | Session + User + Enterprise Memory |

---

## 治理

每次操作必须可追溯：Request ID、Agent、Input、Output、Tool、Duration、Timestamp。

POC 通过 **Agent Trace Timeline** 演示这一点。

---

## 路线图

| 阶段 | 范围 |
|---|---|
| Phase 1 | Multi-Agent POC |
| Phase 2 | Agent Platform（Registry、MCP、Memory） |
| Phase 3 | Enterprise Platform（多租户、RBAC、Event Bus） |
| Phase 4 | Digital Workforce（自主 Agent、人机协同） |

---

## 向领导演示的核心话术

> 今天的 POC 不是玩具项目，而是 XingAI Enterprise Agent Platform 的最小可运行验证。未来所有企业 Agent、MCP、Event Bus、Memory、Governance 都会建立在同样的 Orchestrator + Specialized Agents 架构之上。

---

## 相关文档

- [Multi-Agent Lab POC](../pocs/multi-agent-lab/README.md)
- [Enterprise Architecture (EN)](./ENTERPRISE-AGENT-PLATFORM.md)
- EN: [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md)
- 中文: [Orchestrator 与 MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md)
