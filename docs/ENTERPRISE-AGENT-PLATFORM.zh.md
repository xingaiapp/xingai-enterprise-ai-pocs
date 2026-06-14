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
