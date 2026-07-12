# ADR-006：理赔 MCP OAuth POC——真实认证，不是占位符

**日期：** 2026-07-12
**状态：** 已接受
**作者：** Xing @ XingAI
**英文版：** [English](006-claims-mcp-oauth-poc-real-auth.md)

## 背景

[ADR-003](003-mcp-gateway-placeholder-policy.zh.md) 定下了本仓库里每个 POC 至今都在遵守的规则：在 `mcp-tool-gateway/` 上线之前，POC 用**读**的 MCP 桩或者 mock 响应，**写**工具只记 `WOULD_CALL` 日志——一个模拟的治理预览，不是真实的 MCP 认证（P1–P5 规则）。

这条规则对它管的那件事是对的：跨领域的工具*路由和策略*（哪个 Agent 角色能调哪个领域前缀的工具——`sharepoint.*`、`jira.create_*` 之类），这个东西现在确实不存在，也不该在每个 POC 里各自假装出来。

但它没覆盖一个更窄、单独成立的问题：**任何未来 Gateway 底下的*认证协议*，用真实密码学、对着一个真实受监管的领域，端到端到底长什么样？** `xingai-robinhood-mcp`（XingAI 的一个姊妹仓库，不属于这个 POC 集合）已经为股票交易回答过这个问题——一个已上线、测过、生产形态的 MCP 网关，带类 OAuth 的执行门控（G1–G7）。一份配套的教学实验课（`xingai-enterprise-ai-design/guides/2026-07-12-mcp-oauth-pkce-lab.zh.md`）把完整的 OAuth 2.1 + PKCE + JWT 协议实现写成了教学素材，同样是给券商领域用的。

缺口在于：`xingai-enterprise-ai-pocs` 里没有任何东西把这套模式演示成**可运行的**，也没有任何东西证明它能从券商泛化到本仓库真正的旗舰领域——保险理赔（对应 `claims-multiagent-rag-poc`）。

## 决策

**新增 `pocs/claims-mcp-oauth-poc/`，把 OAuth 2.1 + PKCE + JWT 实验课的机制原样搬过来，把领域从券商换成理赔裁定——而且它实现的是*真实*认证，刻意排除在 ADR-003 的占位范围之外。**

这不是跟 ADR-003 打架；是范围澄清：

| ADR-003 管的 | 本 POC 覆盖的 |
|---|---|
| 跨领域工具路由/策略（哪个 Agent 能调哪个领域的工具） | 任何一个领域 MCP 服务器底下的认证协议 |
| 现在依然正确地是占位符——`mcp-tool-gateway/` 还不存在 | 不是占位符——真实的授权服务器 + 真实的 MCP 服务器 + 真实的客户端，端到端测过，包括一次对着真实运行服务器的冒烟测试 |
| P1–P5 规则（登记表、不静默写、trace 形态、Agent 隔离、人工关口） | 双墙模型（OAuth scope + Agent 理赔权限策略）加 Review→Adjudicate——针对问题的另一个层面、不同但互补的形态 |

从源实验课到这里的领域映射：

| 券商（源实验课） | 理赔（本 POC） |
|---|---|
| `portfolio.read` / `quotes.read` / `orders.review` / `orders.place` | `claims.read` / `policy.read` / `claims.review` / `claims.adjudicate` |
| 股票代码白名单 + 单笔名义金额上限 | 理赔类型白名单 + 理赔权限上限（`MAX_SETTLEMENT_USD`） |
| 隔离的、单独入金的 Agentic 券商账户 | 明确路由进"AI 辅助队列"的理赔（`AI_ASSIST_QUEUE_STATUS`） |
| `review_equity_order` → `place_equity_order` | `review_claim_decision` → `submit_claim_decision` |

同样的密码学，同样的协议流程，同样的四层防护模型——完整映射和每个 OAuth/PKCE 机制从零讲起的解释，见 POC 里的 `docs/mcp-auth-deep-dive.zh.md`，专门写得让一个不熟悉 OAuth 内部机制的读者也能跟上推理过程，而不只是看代码。

## 曾考虑的替代方案

- **直接并进 `claims-multiagent-rag-poc`** —— 拒绝。那个 POC 的模式（Supervisor + RAG + 引用）跟 MCP 认证是不同的架构关注点；混在一起会让两者都更难独立推理。它们通过 `enterprise-mapping.md` 和共享的合成保单号连接，而不是合并成一个 POC。
- **等 `mcp-tool-gateway/` 出来，把认证做成它的一部分** —— 拒绝。Gateway 的职责（按 ADR-003）是跨领域路由/策略；它应该架在一个像本 POC `mcp_server/` 这样形状的 MCP 服务器*前面*，消费这套认证模式，而不是把 token 校验重新造一遍塞进自己的范围里。先把认证层做出来，给未来的 Gateway 留一个真实的对接目标。
- **只写成设计文档/教程，不做可运行的 POC** —— 拒绝；源实验课已经作为教程存在于 `xingai-enterprise-ai-design`。本仓库存在的全部目的（按它自己 README 的说法："在产品化之前先测试架构模式的地方"）就是可运行的、换过领域的版本——教程证明了这套模式一次；这个 POC 证明它能泛化。

## 后果

正面：
- 本仓库里第一个有真实、测过的 OAuth 2.1 + PKCE + JWT 的 POC——给任何未来的领域 MCP 服务器（理赔、HR、采购）底下应该长什么样的认证层，提供了一个具体参考，不只是券商专属版本。
- 补上了 ADR-003 自己点过名的缺口："Claims RAG POC：检索用的是本地向量库；生产路径要在任何写 MCP 之前先加一个保单管理的 MCP 读"——本 POC 正是那一层缺失的 MCP 读/写层，现在演示出来了（还没接进 RAG POC 本身——见实现状态）。

代价：
- 现在有两个 POC（`claims-multiagent-rag-poc`、`claims-mcp-oauth-poc`）都碰"理赔"，但彼此还没打通——读者得去看新 POC 里的 `enterprise-mapping.md` 才能明白它们是互补关系，不是同一件事的两个竞争 demo。
- 本 POC 的 `MAX_SETTLEMENT_USD` / `ALLOWED_CLAIM_TYPES` 是示意性常量，没有对齐任何真实保险公司的权限矩阵——跟源实验课对它的名义金额上限用的是同一种"已披露的局限性"处理方式，如实带过来，而不是包装成本仓库并不具备的行业专业知识。

## 实现状态

- [x] `auth_server/`、`mcp_server/`、`client/`——完整的 OAuth 2.1 + PKCE + JWT + JWKS + Review→Adjudicate + 幂等性，从源实验课移植
- [x] `mcp_server/policies.py`——理赔领域的双墙模型（理赔权限、理赔类型白名单、AI 辅助队列隔离）
- [x] 33 个测试（授权服务器、MCP 认证/scope、理赔流程）——全部通过
- [x] 一次对着真实运行服务器的端到端冒烟测试（完整 PKCE 兑换 + 工具调用），不只是 mock 认证的测试
- [x] `docs/mcp-auth-deep-dive.md`（EN + 中文）——绑定本 POC 代码的协议层讲解
- [x] POC-STANDARDS.md 要求的文件：README（EN + 中文）、architecture.md、enterprise-mapping.md、flow.mmd、references.md
- [ ] 把 `claims-multiagent-rag-poc` 的 Adjudication Agent 接到本 POC 的 MCP 层，而不是直接调理赔数据（在 `enterprise-mapping.md` 里标注为 Phase 2 方向，还没开始）
- [ ] 持久化存储、真实审计轨迹、真实 IdP——见 POC 自己 README 的"现在还不能上生产"

## 相关

- [ADR-003：POC 的 MCP 网关占位策略](003-mcp-gateway-placeholder-policy.zh.md)
- [pocs/claims-mcp-oauth-poc/](../../pocs/claims-mcp-oauth-poc/)——README、architecture.md、enterprise-mapping.md
- [pocs/claims-multiagent-rag-poc/](../../pocs/claims-multiagent-rag-poc/)——姊妹理赔 POC
- `xingai-robinhood-mcp` [ADR-001：MCP 网关代理](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/001-mcp-gateway-proxy.zh.md)——本模式借鉴的真实实现
- `xingai-enterprise-ai-design` [guides/2026-07-12-mcp-oauth-pkce-lab.zh.md](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.zh.md)——本 POC 的直接代码来源
