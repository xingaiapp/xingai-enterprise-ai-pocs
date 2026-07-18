# ADR-010：LLM 护栏与监控十二步演示 POC

**日期：** 2026-07-17  
**状态：** Accepted  
**English:** [010-llm-guardrails-monitoring-poc.md](010-llm-guardrails-monitoring-poc.md)

## 背景

公开教学图常把「带护栏与监控的 LLM 应用」写成 10–12 步工具清单。XingAI 需要一个**可运行**的 POC：走完每一步，同时落实已知纠正——先风险后模型、证据充分性、不可信观测、MCP 双墙工具控制、Agent Run 追踪、Decision Ledger 迭代治理。

## 决策

新增 `pocs/llm-guardrails-monitoring-poc/`（FastAPI Phase-1）：

- 确定性 mock 模型（无需 API Key）
- 显式十二步流水线，失败则后续步骤 `skipped`
- UI 探针：正常路径、注入、高风险工具、弱证据
- 每步结果附带 XingAI 纠正说明

## 后果

- 补齐 claims-mcp-oauth / multi-agent-lab 之外的「全路径教学」演示
- 适合在 8020 端口做课堂 / 管理层演示
- 不能替代生产身份、持久工作流或真实评测闸门

## 后续

- 技术博文：[十二步不是十二个工具 Logo](https://github.com/xingaiapp/xingai-tech-blog/blob/main/posts/2026-07-17-llm-guardrails-twelve-steps-not-tool-stickers.zh.md)
- 企业设计：[Plan → Build → Validate → Operate 不是工具目录](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-17-llm-app-guardrails-plan-build-validate-operate.zh.md)
- Wiki：[产品页](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/products/llm-guardrails-monitoring-poc.zh.md) · [阶梯批判](https://github.com/xingaiapp/xingai-ai-learning-wiki/blob/main/wiki/syntheses/llm-guardrails-monitoring-vs-xingai.zh.md)
