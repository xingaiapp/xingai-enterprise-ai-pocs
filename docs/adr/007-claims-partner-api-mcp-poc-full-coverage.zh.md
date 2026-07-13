# ADR-007：理赔第三方 API MCP POC——全量 API 覆盖，认证推迟

**日期：** 2026-07-13
**状态：** 已采纳
**作者：** Xing @ XingAI
**其他语言：** [English](007-claims-partner-api-mcp-poc-full-coverage.md)

## 背景

[ADR-006](006-claims-mcp-oauth-poc-real-auth.md) 新增了 `claims-mcp-oauth-poc`：一个真实的 OAuth 2.1 + PKCE + JWT 认证服务器挡在 Claims MCP Server 前面，工具集刻意收窄到**4 个**（`get_claim`、`get_policy_coverage`、`review_claim_decision`、`submit_claim_decision`），这样受测的是认证协议本身，而不是工具广度。

这留下了一个本仓库还没证明过的、真正独立的设计问题：如果一个理赔业务想把**所有**面向第三方合作方的对接点都通过 MCP 暴露出来——不只是判定工作流，还包括理赔提交、状态历史、备注、文件证据、保单查询、理赔人管理、赔付结算——一个持有全量读写覆盖的单一 MCP server 能否保持自洽，还是必须拆分、加门槛，或者等窄切片先跑通再说？

这是 MCP server 设计里一个公认的取舍：全量 API 端点覆盖 vs 一小撮专门的工作流工具；当调用方（agent）的真实使用模式还不确定时，全量覆盖能给它们最大的自由度去自己组合操作。`claims-mcp-oauth-poc` 选的是工作流工具这一侧（也是被迫的——它要证明的是认证，不是覆盖面）。本仓库此前还没有人选另一侧、并把它端到端跑通过。

## 决定

**新增 `pocs/claims-partner-api-mcp-poc/` 作为一个新 POC：把一份完整的理赔业务 OpenAPI 契约（`claims-api-openapi.yaml`，7 个业务域共 18 个端点）包装成一个 TypeScript MCP server，对应 18 个工具——并且刻意不在前面加任何第三方认证层，把这件事推迟到后续阶段，而不是让全量 API 覆盖等认证先解决。**

这是一次范围拆分，和 ADR-006 与 ADR-003 的关系是同一个形状：

| 这个 POC 覆盖的 | `claims-mcp-oauth-poc` 覆盖的 |
|---|---|
| 全面的 API-to-MCP 工具覆盖：理赔、状态、备注、文件、保单、理赔人、赔付的完整 CRUD | 一个刻意收窄的 4 工具工作流 |
| 一份 OpenAPI 契约（`claims-api-openapi.yaml`）作为唯一事实来源，MCP server 和一个可运行的 mock 上游都照此实现 | 精心挑选的工具签名，背后没有正式 API 契约 |
| 没有认证层——单一静态 bearer token，被明确列为"距生产环境还差什么"的第一条 | 真实 OAuth 2.1 + PKCE + JWT + 双墙授权（scope + 理赔权限策略） |
| mock 上游里强制执行的理赔状态机，有端到端测试验证 | MCP server 里强制执行的 Review→Adjudicate 拆分 + 幂等性 |

这两个 POC 没有谁比谁"更对"——它们证明的是同一个真实部署问题的两个相反的侧面。一个生产级的第三方理赔 MCP 集成两者都需要：这个 POC 的覆盖广度，加上 `claims-mcp-oauth-poc` 真实的按合作方认证，合并成一个系统（具体的合并方案见本 POC 的 `enterprise-mapping.md`：把 `claims-mcp-oauth-poc` 的认证服务器挡在这个 POC 的 `mcp-server/` 前面，在每个工具执行前校验 `claims-api-openapi.yaml` 的 `securitySchemes` 里已经声明好的 10 个 scope）。

### 为什么不一次性把两者都做了

如果在同一个首发 POC 里同时做全量覆盖和真实 OAuth，两者都会更难独立评审和演示——一个想验证"认证到底有没有真的生效"的评审者，得先啃完 18 个工具的业务逻辑；而一个想验证"API 覆盖是否完整一致"的评审者，得先搞懂 PKCE 和 JWT 校验。拆成两个互相引用的 POC，能让每一个都干净地回答一个问题。这和 ADR-006 里把 `claims-mcp-oauth-poc` 和 `claims-multiagent-rag-poc` 分开的理由是同一套逻辑。

### 为什么 mock 上游是一个完整的 Express 服务，而不是随便糊一个占位符

按本仓库 `POC-STANDARDS.md` 的要求，"可运行"这个状态标签必须诚实。如果让 MCP server 指向一个根本不存在的 `https://api.claims.example.com`，这个 POC 就跑不起来——`claims-mcp-oauth-poc` 自己的 MOCK_CLAIMS/MOCK_POLICIES 先例已经确立了这是不可接受的，那个 POC 正是因此才提供了内存态 fixtures。这个 POC 沿用同一个先例，只是往上提了一个层级：因为它包装的是*整份* OpenAPI 契约而不是四个精心挑选的函数，mock 就必须是一个真正实现每条路由的服务，而不是一个 Python 模块里的几个硬编码字典就能撑住的。

## 考虑过的替代方案

- **直接把这 18 个工具加进 `claims-mcp-oauth-poc`**——否决。那个 POC 的全部意义就在于"真实认证背后的一个窄、可审计的表面"；把它扩到 18 个工具会稀释它本来要证明的东西，也会让它自己的演示脚本更难走通。
- **从一开始就在这个 POC 里把 OAuth 层建好**——本阶段否决；理由见上面"为什么不一次性把两者都做了"。已经在 `enterprise-mapping.md` 里记为下一步的自然方向，而不是被悄悄跳过。
- **在认证做好之前，把这个 POC 标成"仅架构设计，尚不可运行"**——否决。这个 POC 证明的模式（OpenAPI 契约 → MCP 工具逐一映射、强制状态机、涉及资金写操作的幂等性）今天就是真实的、可独立测试的；把它的"可运行"标签绑定在一个不相关的、未来的认证阶段上，会歪曲它实际展示的内容。

## 后果

正面：
- 本仓库第一个证明"OpenAPI 契约到 MCP 全量覆盖"（18/18 端点）而不是精选工具子集的 POC，配有可运行的 mock 上游和一个跑通完整理赔生命周期的端到端测试，包括一次非法状态流转拒绝和一次幂等打款重试。
- 给 `claims-mcp-oauth-poc` 的认证模式提供了一个具体的、更广阔的下一阶段集成目标（见 `enterprise-mapping.md`），而不是让那套模式无限期地停留在 4 个工具的范围里。

取舍：
- 这个 POC 明确**不能原样暴露给真实第三方使用**——单一静态 bearer token 是一个真实的缺口，不是风格上的简化，之所以被列为"距生产环境还差什么"的第一条，正是为了不被误认成后者。
- 现在有两个理赔域的 MCP POC（`claims-mcp-oauth-poc`、`claims-partner-api-mcp-poc`），语言不同（Python vs TypeScript）、工具数量也不同；读者需要看 `enterprise-mapping.md` 才能理解它们是互补的两半，而不是同一个想法的两个互相竞争的实现。

## 实施状态

- [x] `claims-api-openapi.yaml` —— 7 个业务域共 18 个端点的 OpenAPI 3.1 契约
- [x] `mcp-server/` —— TypeScript MCP server，Streamable HTTP 传输，18 个工具，Zod 校验，markdown/JSON 双格式输出，破坏性/幂等性标注
- [x] `mock-api/` —— 实现每个端点的 Express mock 上游，内存态数据，强制执行理赔状态机
- [x] `tests/e2e.mjs` —— 端到端全流程测试（建理赔人→建理赔→保单核验→加备注→状态流转→非法流转拒绝→带幂等性的赔付结算→状态历史查询），针对真实运行中的进程执行
- [x] `docker-compose.yml` 串联两个服务
- [x] POC-STANDARDS.md 要求的必需文件：README（EN + 中文）、architecture.md、enterprise-mapping.md、flow.mmd、references.md
- [ ] 挡在 `mcp-server/` 前面的第三方 OAuth 2.1 认证层（见 `enterprise-mapping.md` 与 `claims-mcp-oauth-poc` 的合并方案）——尚未开始
- [ ] 持久化存储、真实审计留痕、租户隔离、限流——见本 POC README 的"距生产环境还差什么"

## 相关

- [ADR-003：POC 的 MCP 网关占位策略](003-mcp-gateway-placeholder-policy.md)
- [ADR-006：理赔 MCP OAuth POC——真实认证，非占位](006-claims-mcp-oauth-poc-real-auth.md)
- [pocs/claims-partner-api-mcp-poc/](../../pocs/claims-partner-api-mcp-poc/) —— README、architecture.md、enterprise-mapping.md
- [pocs/claims-mcp-oauth-poc/](../../pocs/claims-mcp-oauth-poc/) —— 这个 POC 缺失的认证层所在的姊妹 POC
- `xingai-enterprise-ai-design` [articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.zh.md](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.zh.md) —— 本 POC 的直接设计来源
