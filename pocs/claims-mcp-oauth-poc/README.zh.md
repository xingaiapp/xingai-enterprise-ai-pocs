# 理赔 MCP OAuth 2.1 + PKCE POC

> **状态：可运行 · Phase 1**

**模式：** 在一个理赔行业 MCP 服务器前面做真实的 OAuth 2.1 + PKCE + JWT 认证授权——不是占位符,不是架构图,是一个真正会签发 token 的授权服务器和一个真正会校验 token 的 MCP 服务器,理赔顾问辅助 Agent 端到端地跟它们做认证。

**English:** [README.md](./README.md) · **MCP 认证深度讲解：** [docs/mcp-auth-deep-dive.zh.md](./docs/mcp-auth-deep-dive.zh.md)

---

## 这个 POC 证明了什么

Robinhood 给它的 Agentic Trading MCP 用的那套认证模式——OAuth 2.1 + 强制 PKCE、`.well-known` 元数据发现、短生命周期的带 scope JWT、任何"绑定动作"都拆成 Review→Execute 两步——能干净地搬到一个完全不同的、同样受监管、同样碰钱的领域:保险理赔裁定。[原始案例文章](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)和配套的 [OAuth 实验课](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.zh.md)是为券商写的;这个 POC 就是那套实验课的移植版:同样的密码学、同样的协议流程、同样的双墙模型,换了一套领域名词(`claims.read`/`claims.adjudicate` 代替 `portfolio.read`/`orders.place`,理赔权限上限代替单笔名义金额上限,"AI 辅助处理队列"代替隔离的 Agentic 券商账户)。

## 企业模式

- **OAuth 2.1 授权码流程 + 强制 PKCE**——没有 implicit grant,没有明文 client secret,只认 S256 挑战方式
- **`.well-known` 元数据发现**(RFC 8414 授权服务器元数据 + RFC 9728 受保护资源元数据)——Agent 从一次 401 里发现所有端点,永远不硬编码某个保险公司的认证配置
- **短生命周期、绑定 audience 的 JWT**(RS256,5分钟 TTL),通过 JWKS 校验,不是共享密钥
- **Scope ≠ 策略**——`claims.review` 和 `claims.adjudicate` 是两个独立的 scope;两个都拿到了也不代表能对*任意*理赔案*任意*金额做裁定(见下面的"墙 #2")
- **只有 Review → Adjudicate,绝不一步到位写**——先起草、冻结决策,只有第二次调用(不接受任何可变业务参数)才会让它生效
- **幂等的最终提交**——网络重试不会导致同一个理赔被重复裁定
- **两道独立的授权墙**,对应[四层防护模型](docs/mcp-auth-deep-dive.zh.md#四层防护模型)：OAuth scope(墙 #1,"这个 Agent 到底能不能调这个工具")和 Agent 理赔权限(墙 #2,"这一笔具体理赔、这个具体金额,能不能过")——见 `mcp_server/policies.py`

## 现在还不能上生产

这个 POC 故意**不是**生产就绪的。真要接进一个真实保险公司之前:

- **真正的身份提供商**——把这里的演示授权服务器换成 Okta / Auth0 / Azure AD B2C,或者一套加固过的自建 IdP。本仓库的 `auth_server/` 跳过了 MFA、真实会话管理、异常登录检测、管理控制台——这些都是真 IdP 免费给你的东西,不值得在这里重造。
- **持久化存储**——`auth_server/storage.py` 和 `mcp_server/tools.py` 里的 review/幂等性存储都是内存里的 `dict`。进程一重启,所有会话和未完成的 review 悄悄全部失效。生产需要 PostgreSQL(code、client、同意记录)+ Redis(短 TTL 的 code、幂等性 key)。
- **真实登录 + 同意记录**——demo 的 `/authorize` 页面用的是固定用户,也不持久化"授权了什么"。生产需要真实身份验证、一份可查询/可撤销的(用户,client,scope)三元组同意记录,以及只有在策略允许时才跳过重新同意页面。
- **真实理赔系统对接**——`mcp_server/policies.py` 里的 `MOCK_CLAIMS`/`MOCK_POLICIES` 是合成的样例数据。生产要在一个真实的保单管理/理赔管理系统(Guidewire ClaimCenter、Duck Creek Claims,或自建系统)前面包一层同样形状的 MCP。
- **满足监管要求的审计留存**——这个 POC 目前完全没有持久化审计轨迹。真实的理赔 MCP 需要一份 append-only 日志(谁、哪个理赔、哪个工具、什么决策、什么结果),按各州保险监管要求留存,不能只是内存里的 dict。
- **密钥管理**——这里的 `keys/private.pem` 就是磁盘上的一个文件。生产需要 Key Vault / HSM、支持重叠有效期的 JWKS 密钥轮换,私钥永远不碰通用文件系统。
- **限流和防提示注入**——两者现在都不存在;等真正由 LLM(而不是这个 POC 的脚本化演示流程)来决定调哪个工具时,这两件事只会更重要,不会更不重要。
- **全程 HTTPS**——demo 里三个服务都跑在本地明文 HTTP 上。

完整清单见深度讲解文档的[上线前检查清单](docs/mcp-auth-deep-dive.zh.md#上线前检查清单)。

## 架构

```text
理赔顾问辅助 Agent（Python 客户端）
     │
     │ 1. POST /mcp（无 token）→ 401 + resource_metadata
     ▼
授权服务器 :8000
     │  元数据发现 / PKCE / JWT 签发 / Refresh 轮换 / 吊销
     ▼  Bearer JWT（RS256, 5分钟 TTL）
理赔 MCP 服务器 :8001
     │  签名校验 + Scope（墙 #1）+ 理赔权限策略（墙 #2）
     │  + Review → Adjudicate + 幂等性
     ▼
模拟的理赔案卷 / 保单保额 / 裁定结果（没有接真实保险公司系统）
```

完整 Mermaid 图见 [flow.mmd](./flow.mmd)。各组件职责见 [architecture.md](./architecture.md)。

## 快速开始

```bash
cd pocs/claims-mcp-oauth-poc
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

# 生成 RSA 密钥对（从不提交——见 keys/README.md）
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

pytest tests/ -v   # 33 个测试，不需要起服务
```

跑完整的三服务流程（三个终端）：

```bash
# 终端 1
uvicorn auth_server.main:app --port 8000 --reload

# 终端 2
uvicorn mcp_server.main:app --port 8001 --reload

# 终端 3
python -m client.main
```

客户端会打开浏览器走 OAuth 同意页,然后依次走：`get_claim` → `get_policy_coverage` → `review_claim_decision` → **你手动输入 `YES`** → `submit_claim_decision` → 幂等性重试演示。

或者用 Docker（只跑 `auth-server` + `mcp-server`——为什么客户端要在宿主机上跑,见 `docker-compose.yml` 里的注释）：

```bash
docker compose up --build
```

## API

| 端点 | 服务 | 用途 |
|------|------|------|
| `GET /.well-known/oauth-authorization-server` | Auth (:8000) | RFC 8414 元数据——所有 OAuth 端点 URL |
| `GET /jwks.json` | Auth (:8000) | 公钥 |
| `POST /register` | Auth (:8000) | 动态 client 注册（仅限 loopback redirect） |
| `GET`/`POST /authorize` | Auth (:8000) | 同意页 + 授权码签发 |
| `POST /token` | Auth (:8000) | code→token 兑换；refresh token 轮换 |
| `POST /revoke` | Auth (:8000) | 撤销 refresh token |
| `GET /.well-known/oauth-protected-resource/mcp` | MCP (:8001) | RFC 9728 元数据——指向授权服务器 |
| `POST /mcp` | MCP (:8001) | JSON-RPC 2.0——`initialize`、`tools/list`、`tools/call` |

`tools/call` 暴露的工具：

| 工具 | 所需 Scope | 效果 |
|------|-----------|------|
| `get_claim` | `claims.read` | 返回理赔案卷 |
| `get_policy_coverage` | `policy.read` | 返回保单保额/免赔额 |
| `review_claim_decision` | `claims.review` | 起草一个决策，不生效 |
| `submit_claim_decision` | `claims.adjudicate` | 让之前起草的决策生效，幂等 |

## 团队演示脚本

1. 演示 `curl http://localhost:8001/mcp` 不带 token → 401 + `WWW-Authenticate` 里点名去哪发现授权服务器。*"服务器从不猜你是谁——它直接告诉你去哪证明。"*
2. 跑 `python -m client.main`,让浏览器的同意页渲染出来——把 scope 列表念一遍。*"这就是人类在任何授权发生之前,用大白话看到 Agent 到底在申请什么权限的那一刻。"*
3. `review_claim_decision` 打印出摘要之后，**先别输 YES**，问在场的人："如果我跳过这一步会怎样？"——然后打开 `mcp_server/tools.py` 的 `tool_submit_claim_decision`：它只接受 `review_id`，别的什么都不接受。没有任何代码路径能裁定一个没被 review 步骤冻结过的理赔。
4. 输入 `YES`，展示最终裁定结果，然后立刻重跑一次幂等性步骤，指着 `idempotent: true`——*"Agent 那边一次不稳定的网络重试,不可能导致这笔理赔被重复赔付。"*
5. 打开 `mcp_server/policies.py`，把 `MAX_SETTLEMENT_USD` 改成 `100`，重启 MCP 服务器，对着 `CLM-8842`（一笔 $1,850 的理赔）重跑演示——看它被 `policy_violation` 拒绝。*"这不是 OAuth 层说不——token 依然完全有效。这是第二道墙：scope 说的是这个 Agent* 能不能 *调这个工具，policy 说的是* 这一笔理赔、这个金额 *能不能过。"*

## 踩过的坑

- 直接照搬参考实验课的密码学代码看起来安全,其实不然：`public_key_to_jwk()` 对一个已经是公钥的对象(直接从 `public.pem` 用 `load_pem_public_key` 读出来的,不是需要额外解包的证书封装)调用了 `.public_key()`。直到 `pytest` 真的跑了 `/jwks.json` 才暴露出来——提醒自己"从一份能跑的参考资料改的"和"测过的"不是一回事,尤其是密码学胶水代码,没人会在设计文档里逐行读。
- Scope 强制测试的第一版整个 mock 掉了 `authenticate_request`(`return_value=limited_claims`),这悄悄跳过了它本该测试的真实 `require_scopes()` 检查——每个"权限不足"测试都通过了,但理由是错的(压根没断言 scope 逻辑真的跑过)。修法是往下 mock 一层(`verify_token`),让真实的 scope 检查针对 mock 出来的 claims 真正执行一遍。教训：当一个安全检查本身就是被测对象时,永远 mock 它的*输入*,绝不 mock 检查本身。
- 把 `MAX_SETTLEMENT_USD` 和 `ALLOWED_CLAIM_TYPES` 旁边配一句解释真实保险概念(理赔权限分级)的注释,让演示脚本明显更容易讲给非工程背景的听众——比原版的名义金额上限好懂得多。把一个安全控制点绑定到听众已经有心智模型的业务概念上,多写这一段注释是值得的。

## 相关设计文档

- EN: [How MCP Works in Production: A Deep Dive from Robinhood Trading MCP](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.md)
- 中文: [生产环境里 MCP 如何真正运转](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-11-mcp-in-production-robinhood-case.zh.md)
- EN: [Build an OAuth 2.1 + PKCE MCP Project from Scratch](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.md)（本 POC 的直接代码来源——同样的代码，理赔领域代替券商领域）
- 中文: [从零搭建 OAuth 2.1 + PKCE MCP 项目](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-pkce-lab.zh.md)
- EN: [MCP Auth — The Robinhood Deep Dive](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.md)
- 中文: [从 Robinhood MCP 看懂 MCP 认证](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/guides/2026-07-12-mcp-oauth-auth-deep-dive.zh.md)
- 本模式的真实实现来源: [xingai-robinhood-mcp](https://github.com/xingaiapp/xingai-robinhood-mcp)（[ADR-001](https://github.com/xingaiapp/xingai-robinhood-mcp/blob/main/docs/adr/001-mcp-gateway-proxy.zh.md)：网关代理；G1–G7 执行门控）
- 本仓库的姊妹 POC: [Claims Multi-Agent RAG](../claims-multiagent-rag-poc/)——本 POC 的 `MOCK_POLICIES` 复用了那个 POC 的 `POL-1001`/`POL-2002`/`POL-3003` 保单号，保持两个 POC 之间的叙事连续性；真实的 Phase 2 可以让那个 POC 的 Adjudication Agent 走本 POC 的 MCP 层，而不是直接调理赔系统
- [ADR-003：POC 的 MCP 网关占位策略](../../docs/adr/003-mcp-gateway-placeholder-policy.md)——本 POC 是本仓库第一个实现*真实* OAuth 的 POC，而不是那篇 ADR 给其他所有 POC 定的 P1–P5 占位规则；两者关系见 [enterprise-mapping.md](./enterprise-mapping.md)

完整外部参考列表（RFC、MCP 规范）见 [references.md](./references.md)。

## 免责声明

本 POC 仅供**信息与教育**用途，**不是**生产级保险或理赔软件。

- 代码、文档与示例按 **「现状」** 提供，不附带任何保证。
- 若你复用本仓库的任何内容，安全、合规、部署与结果由你自行负责。
- 遵循本 POC **不构成** 与 XingAI 的专业、法律或合规关系。
- 涉及受监管决策时，请咨询具备资质的专业人士。
