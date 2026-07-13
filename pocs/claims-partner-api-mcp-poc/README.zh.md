# 理赔第三方 API MCP POC

> **状态：可运行 · Phase 1**

**模式：** 把一个现有的理赔业务 REST API 全量包装——涵盖理赔提交、状态流转、备注、文件、保单核验、理赔人、赔付结算的完整读写——成一个单一的 MCP server，让第三方 AI agent（合作修理厂、理赔人自助 app、经纪工具）用一套标准工具接口对接，而不是每个合作方单独写一套客户端。

**English:** [README.md](./README.md)

---

## 这个 POC 证明了什么

一个（现有或新设计的）理赔业务 REST API 可以通过**一个覆盖全面的单一 MCP server**暴露给第三方 AI agent——18 个工具、覆盖 7 个业务域，每个都有 Zod 输入校验、markdown/JSON 双格式输出、读写标注——而不是精心挑选的一小撮工作流工具。这是与本仓库姊妹项目 [`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/) 相反的设计取舍：那个 POC 证明的是真实 OAuth 2.1 + PKCE 认证，工具集刻意收窄到 4 个。这个 POC 证明的是"全量 API 覆盖"这一侧；**它目前还没有认证层**——见下面"距生产环境还差什么"。

## 体现的企业级模式

- **OpenAPI 契约先行** —— [`claims-api-openapi.yaml`](./claims-api-openapi.yaml) 是唯一事实来源；MCP server 的工具 schema 和 mock 上游的路由都各自照着这份契约写，而不是互相照抄
- **全量 CRUD 覆盖，不只是工作流切片** —— 理赔的创建/查询/更新、状态流转、备注、文件上传、保单核验、理赔人注册、赔付结算全部暴露，第三方 agent 不会因为"还差一个工具"被卡住
- **涉及资金的写操作带幂等性** —— `claims_create_payment` 始终携带 `Idempotency-Key`；重试请求会返回原来那笔赔付而不是重复创建（`tests/e2e.mjs` 第 8 步已验证）
- **显式状态机** —— mock API 强制执行合法的理赔状态流转（比如 `approved → under_review` 会被拒绝），非法写入会明确报错而不是悄悄破坏理赔状态
- **破坏性操作有标注** —— `claims_transition_status` 和 `claims_create_payment` 是仅有的两个标注 `destructiveHint: true` 的工具；其余全部是只读或增量写
- **不依赖真实承保系统也能跑通** —— `mock-api/` 是一个实现同一份 OpenAPI 契约的小型 Express 服务，内存数据，`docker compose up` 即可端到端运行，无外部依赖

## 距生产环境还差什么

- **这个 MCP server 前面没有第三方认证层。** `mcp-server/` 用单一静态 `CLAIMS_API_TOKEN` 调用上游 Claims API——给一个内部调用方用没问题，但给多个外部合作方共用同一凭证并不安全，任何一方都无法被单独吊销。修复方案本仓库里已经有了：用 [`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/) 里那套 OAuth 2.1 + PKCE + JWT + scope 模式挡在前面，在每个工具的 handler 执行前，校验 `claims-api-openapi.yaml` 的 `securitySchemes` 里已经定义好的 scope（`claims.read`、`claims.write`、`claims.adjudicate`、`documents.read`、`documents.write`、`policies.read`、`claimants.read`、`claimants.write`、`payments.read`、`payments.write`）。
- **`mock-api/` 是内存、单进程的。** 每一条理赔、备注、文件、赔付都是一个 JS `Map`；重启即清空。生产环境需要真实的保单管理/理赔管理系统（Guidewire ClaimCenter、Duck Creek Claims，或自研系统）挡在同一份 OpenAPI 契约后面。
- **没有审计留痕。** 没有记录哪个第三方在什么时候对哪个理赔调用了哪个工具——这是任何受监管的理赔业务上线前的硬性要求。
- **没有限流和按合作方配额。** 目前一个行为异常或被攻破的合作方可以耗尽和其他所有合作方一样多的容量。
- **没有租户隔离。** 没有"合作方 A 只能看到分配给合作方 A 的理赔"这个概念——每次工具调用理论上都能碰到 mock 存储里的任意一条理赔。
- **文件上传并没有真正落盘存储。** `mock-api` 的 `downloadUrl` 是伪造出来的、看起来像签名 URL 的字符串，背后没有真实对象存储。
- **详见 [ADR-007](../../docs/adr/007-claims-partner-api-mcp-poc-full-coverage.md)**，记录了这个 POC 刻意做出的设计取舍（先做全量 API 覆盖、认证层推迟到后续阶段），以及它和 [ADR-003](../../docs/adr/003-mcp-gateway-placeholder-policy.md) 占位策略之间的关系。

## 架构

```text
第三方 AI Agent
     │
     │ POST /mcp（JSON-RPC 2.0：tools/list、tools/call）
     ▼
Claims MCP Server（mcp-server/，:3000）
     │  7 个业务域共 18 个工具 —— Zod 校验、markdown/JSON 输出、
     │  破坏性/幂等性标注
     │  用 Bearer token 调用 Claims API（目前是单一静态 token，还没有按合作方区分认证）
     ▼
Claims Mock API（mock-api/，:4000）
     │  实现 claims-api-openapi.yaml —— 内存中的理赔/保单/
     │  理赔人/备注/文件/赔付数据，强制执行理赔状态机
     ▼
（生产环境：换成真实的理赔/保单管理系统，契约不变）
```

完整时序图见 [flow.mmd](./flow.mmd)；组件职责见 [architecture.md](./architecture.md)。

## 快速开始

```bash
cd pocs/claims-partner-api-mcp-poc
docker compose up --build
```

会在 `:4000` 启动 `mock-api`，在 `:3000` 启动 `mcp-server`，两者已在 compose 网络里连好（`mcp-server` 的 `CLAIMS_API_BASE_URL` 指向 `mock-api`）。

不用 Docker 的话，分别在两个终端里跑：

```bash
# 终端 1
cd mock-api && npm install && npm run build && PORT=4000 npm start

# 终端 2
cd mcp-server && npm install && npm run build
CLAIMS_API_BASE_URL=http://localhost:4000 CLAIMS_API_TOKEN=mock-dev-token TRANSPORT=http PORT=3000 npm start
```

然后跑端到端的全流程脚本（建理赔人→建理赔→查询保单核验→加备注→状态流转→非法流转被拒绝→赔付结算→查状态历史）：

```bash
cd tests && node e2e.mjs
```

正常输出应以 `All checks passed.` 结尾。

## API

18 个 MCP 工具，对应 [`claims-api-openapi.yaml`](./claims-api-openapi.yaml) 里的 18 个端点：

| 业务域 | 工具 |
|---|---|
| 理赔 | `claims_list_claims`, `claims_create_claim`, `claims_get_claim`, `claims_update_claim` |
| 状态 | `claims_transition_status`, `claims_list_status_history` |
| 备注 | `claims_list_notes`, `claims_add_note` |
| 文件 | `claims_list_documents`, `claims_upload_document`, `claims_get_document` |
| 理赔人 | `claims_create_claimant`, `claims_get_claimant` |
| 保单 | `claims_get_policy`, `claims_check_policy_coverage` |
| 赔付 | `claims_list_payments`, `claims_create_payment`, `claims_get_payment` |

`claims_transition_status` 和 `claims_create_payment` 标注为 `destructiveHint: true`；其余工具要么是 `readOnlyHint: true`，要么是非破坏性的增量写（创建理赔/理赔人/备注/文件）。

每个工具的详细文档（参数、返回结构、错误处理）都写在 `mcp-server/src/tools/*.ts` 各自的 `description` 字段里——对运行中的 server 调用 `tools/list` 即可看到渲染结果，或直接读源码。

## 团队演示脚本

1. `curl http://localhost:3000/mcp` 空请求体 → 确认 JSON-RPC 端点已启动；跑一次 `tools/list`，数一数 7 个业务域共 18 个工具。*"一个 MCP server，覆盖了整个理赔 API 表面——不是精心挑选的四个工具。"*
2. 跑 `tests/e2e.mjs`，念出第 7 步：一个已 approved 的理赔拒绝流转回 `under_review`。*"mock 后端强制执行的是和真实理赔系统一样的状态机——非法写入会明确报错，不会悄悄发生。"*
3. 再跑一次 `tests/e2e.mjs`，或者手动用 `curl` 复用同一个 idempotency key 调用第 8 步的打款——重复请求会返回同一个 `paymentId`，而不是生成第二笔赔付。*"agent 网络重试导致的请求，没法让同一条理赔被打款两次。"*
4. 打开 README 的"距生产环境还差什么"，念出第一条：还没有第三方认证层。然后并排打开 [`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/) 的 README。*"这两个 POC 是同一个真实部署的两半：这个负责全量 API 覆盖，那个负责真实的 OAuth scope 校验。"*

## 经验教训

- `mock-api` 打款端点的第一版只是把理赔状态改成 `in_payment`，却没有记一条 `StatusEvent`——OpenAPI 规范里明明写着"打款成功后理赔会进入 `in_payment`"，但实现悄悄跳过了记录*为什么*。`tests/e2e.mjs` 第 10 步（断言恰好有 3 条状态事件）第一次真跑的时候就抓到了：实际只返回了 2 条。修复方式是让 payments 路由也发出一条 `StatusEvent`，reason 里写清楚是哪笔赔付触发的。教训：任何会改 `claim.status` 的代码路径都得走同一条审计追加逻辑，不能只指望专门的状态流转端点——当第二个端点（打款）也顺带改状态时，很容易漏掉。
- 在这个环境里，用 `&` 在一次 shell 工具调用里起的后台进程，不会活到*另一次*独立的工具调用里——每次调用都是一个独立的 shell。`e2e.mjs` 只有在 `mock-api` 和 `mcp-server` 都启动、且测试脚本在*同一次* shell 调用里执行时才跑通。这点值得在快速开始里写明白（用三个持续存在的终端，或者一次 `docker compose up` 进程），而不是假设"后台启动、过会儿再回来看"在所有环境下都成立。
- 手工（没用代码生成）分别从同一份 `claims-api-openapi.yaml` 推导出 MCP server 的 Zod schema 和 mock API 的 Express 路由，中间出现过几次差点对不上——比如 `claims_check_policy_coverage` 的 `claimType` 需要对 mock 的 `coverages` key 做宽松的子串匹配（`"glass"` vs `"auto_glass"`），因为 OpenAPI 规范里从没定死理赔类型到保障类别名字的映射关系。真正的 Phase 2 应该要么从 OpenAPI 文件双向代码生成，要么加一张显式的"理赔类型→保障类别"映射表，而不是靠字符串匹配。

## 相关设计文档

- EN: [MCP API Coverage vs. Workflow Tools: A Claims Partner Integration Case Study](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.md)
- 中文: [MCP 全量 API 覆盖 vs 工作流工具：一个理赔第三方对接案例](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-13-mcp-api-coverage-vs-workflow-tools.zh.md)
- EN: [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.md)
- 中文: [生产环境里 MCP 如何真正运转](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)
- 姊妹 POC：[`claims-mcp-oauth-poc`](../claims-mcp-oauth-poc/) —— 这个 POC 缺的真实 OAuth 2.1 + PKCE + JWT 认证；两者如何组合见本 POC 的 [enterprise-mapping.md](./enterprise-mapping.md)

## 免责声明

本 POC 仅用于**信息与教育目的**，**不是**可直接用于生产的保险或理赔软件。

- 代码、文档和示例均按**"现状"**提供，不附带任何保证。
- 若你复用其中任何内容，安全性、合规性、部署方式及结果均由你自行负责。
- 使用本 POC 不会与 XingAI 建立任何专业、法律或合规关系。
- 涉及受监管的决策，请咨询合格的专业人士。
