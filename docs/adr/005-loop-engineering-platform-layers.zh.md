# ADR-005: Loop Engineering 与 17 层平台参考架构

**日期:** 2026-07-03
**状态:** Accepted
**作者:** Xing @ XingAI
**Also available:** [English](005-loop-engineering-platform-layers.md)

## 背景

ADR-001 到 ADR-004 建立了 Supervisor 编排、RAG、MCP Gateway 占位和事件总线设计的 POC 模式，覆盖了企业 Agent 技术栈的**第二层（Harness Engineering）**。

[企业 Agent 平台](../ENTERPRISE-AGENT-PLATFORM.zh.md)文档描述了目标驱动的 Agent 协作愿景，但没有具体说明**第三层（Loop Engineering）**——自主调度、反思和终止条件——如何融入平台架构，也没有分解功能层和治理层。

[超越 Prompt Engineering](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-03-beyond-prompt-engineering-loop-engineering.zh.md) 文章介绍了三层架构（Context → Harness → Loop）和 17 层平台分解。本 ADR 将该框架作为未来 POC 和企业平台设计的参考架构。

## 决策

### 1. 三层 Agent 架构

每个 POC 和生产 Agent 遵循三层：

```text
┌──────────────────────────────┐
│ 第三层 Loop Engineering      │
│ 入口 • 循环体 • 终止条件 • 防护栏 │
└──────────────────────────────┘
┌──────────────────────────────┐
│ 第二层 Harness Engineering   │
│ 工具 • 技能 • 记忆 •          │
│ 多 Agent • 权限               │
└──────────────────────────────┘
┌──────────────────────────────┐
│ 第一层 Context Engineering   │
│ Prompt • RAG • 用户画像 •     │
│ 对话 • 运行时状态              │
└──────────────────────────────┘
```

POC 阶段每次验证一到两层。生产阶段必须覆盖全部三层。

### 2. 17 层平台分解

企业平台分解为 11 个功能层和 6 个治理层：

**功能层 (11):** 流量层、API 网关、消息队列、Planner Agent、业务 Agent、技能、AI 网关、模型层、MCP/工具、知识、记忆。

**治理层 (6):** 配置中心、Agent 注册中心、评估中心、AI 安全、AI 治理、弹性扩缩容。

模型只是十七层中的一层。POC 应明确标注它验证了哪些层。

### 3. Loop 防护栏强制要求

任何包含循环的 POC 或生产 Agent 必须定义：

| 防护栏 | 要求 |
|--------|------|
| 最大迭代次数 | 硬上限（例如 5 次）|
| Token 预算 | 由 Harness 强制执行，不是 prompt |
| 无进展检测 | 连续 2 轮停滞自动停止 |
| 墙钟超时 | 防止 Agent 挂起 |
| 人工审批关卡 | 高风险操作必须升级 |

### 4. Micro Loop Engine 作为目标模式

长期目标是动态 Agent 组装（Micro Loop Engine）而非硬编码 Agent。POC 应将技能、工具和记忆设计为可组合组件，供未来引擎组装。

## 备选方案

| 方案 | 结果 |
|------|------|
| 继续不标注层次的 POC | 团队无法将 POC 发现映射到生产架构 |
| 采用不同的层次模型 | 三层 + 17 层模型与现有企业 Agent 平台文档和 XingAI 产品架构一致 |
| POC 中跳过 loop 防护栏 | 坏习惯带入生产；POC 阶段成本失控 |

## 后果

- 每个新 POC README 必须声明它验证了三层中的哪些层和 17 层中的哪些平台层
- 包含循环的 POC 至少实现最大迭代次数 + token 预算防护栏
- 企业 Agent 平台文档应更新引用此三层 + 17 层框架
- POC 的技能、工具和记忆应遵循可组合接口，以便 Micro Loop Engine 复用

## 迁移触发

- 如果行业趋向不同的标准分层（例如广泛采用的框架定义不同层次），重新评估并对齐
- 如果 Micro Loop Engine 从设计阶段进入 POC 阶段，为引擎的组装契约创建 ADR-006
