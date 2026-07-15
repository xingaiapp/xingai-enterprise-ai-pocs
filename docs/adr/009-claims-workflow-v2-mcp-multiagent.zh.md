# ADR-009:理赔工作流 v2——深化为真实 MCP 工具访问、LLM Agent 与 LangGraph Supervisor

**日期:** 2026-07-15
**状态:** 已采纳(Phase 1 已实现;Phase 2/3 已规划,尚未开始)
**作者:** Xing @ XingAI
**其他语言:** [English](009-claims-workflow-v2-mcp-multiagent.md)

## 背景

[ADR-008](008-claims-workflow-v2-poc.md) 建立了 `claims-workflow-v2-poc`,证明设计文章的三处修复(欺诈检测拆分、Case Resolution Router、合规审计追踪)是可实现的,实现方式是纯 Python 函数互相直接调用、直接读写内存字典。这是刻意的——ADR-008 特意把 LLM 调用和 MCP 都排除在外,先把三处修复本身用确定性方式验证清楚。但这也意味着那个 POC 里的"Agent"只是取了这个名字:没有推理、没有工具调用边界、Agent 之间没有协议。

本 ADR 涵盖把它往深处做的三层,以及另外一个独立但相关的问题:如果/当第三方厂商要直接消费这个 POC 的工具时,认证该怎么做。

## 决策

**分三个阶段实现,每个阶段可独立交付:**

### Phase 1 —— MCP 作为数据访问边界(本 ADR 已实现的范围)

把 `MOCK_POLICIES`、`DecisionLedger`、赔付结算存储都挪到一个新的 `mcp_server/` 包后面(手写的 JSON-RPC `/mcp` 端点,跑在 FastAPI 上,和 `claims-mcp-oauth-poc/mcp_server/main.py` 是同一套模式——不依赖官方 MCP SDK,和本仓库已有先例保持一致)。四个工具,严格对应要搬走的三个本地存储,不多加没有 Phase 1 调用方的工具:`get_policy_coverage`(`policy.read`)、`record_ledger_decision`(`audit.write`)、`get_audit_trail`(`audit.read`)、`create_payment`(`payments.write`,幂等)。`claims_workflow.ledger.DecisionLedger` 以及承保核实/赔付两个 Agent 不再直接碰本地字典,而是通过一个轻量 MCP client(`claims_workflow/mcp_client.py`)去调——默认走进程内 ASGI transport(跑本 POC 自己的测试不需要另起进程),设了 `MCP_SERVER_URL` 时走真实 HTTP(docker-compose 场景)。`get_claim_history` 和一个 `get_claim` 查询工具刻意推迟到 Phase 2 才加——那时候换成 LLM 的 Fraud Triage Agent 才是第一个真正需要它们的调用方;Phase 1 只搬运已经存在的存储,不新增能力。这一步还不涉及 LLM——纯粹是"把一次直接的 Python 调用换成一次工具调用协议",所以现有 26 个测试的行为预期不变、应该继续全部通过(已验证,见"实现状态")。

### Phase 2 —— 判断力环节换成真 LLM Agent(已规划,尚未开始)

不是每个环节都值得换成 LLM:

| 环节 | 换成 LLM 吗 | 理由 |
|---|---|---|
| Fraud Triage | 是 | 真实的 velocity/tenure 欺诈判断需要对自由文本的理赔历史做推理,不只是比两个数字 |
| Fraud Scoring | 是 | 成本异常和照片取证的判断,适合对非结构化证据做推理 |
| Policy Coverage | 是,而且要接 RAG | 复用 `claims-multiagent-rag-poc` 已经搭好的向量库模式,让承保判断真正去读保单条款文本,而不是查一个 3 条记录的字典——这也是让拒赔信引用的条款变得"真实"而不是 mock 字符串的关键 |
| 拒赔信起草 | 是 | 把 Decision Ledger 一条记录里已经结构化的 `reasoning` 转成真正的信件文本;幻觉风险低,因为输入本身就是已核验的结构化数据,不是开放式生成 |
| Approval(金额阈值判断) | 否 | 纯数字比较,换成 LLM 只会增加不一致性风险,没有收益 |
| Payment | 否,绝不 | 涉及资金移动的写操作必须保持确定性和幂等,`claims-partner-api-mcp-poc` 已经定过这条规矩 |
| Case Resolution Router | 否——路由映射表保持确定性 | LLM 不应该临时发明新路由;它可以把人工的自由文本备注分类成结构化的 `outcome` 值喂给现有的确定性 Router,但路由表本身不能由 LLM 决定 |

每个换成 LLM 的 Agent 都保留启发式兜底实现(即当前 ADR-008 里的版本),这样测试套件在零 API key 情况下依然能跑——见下面"测试策略"。

### Phase 3 —— LangGraph Supervisor(已规划,尚未开始)

用一个 LangGraph `StateGraph` 取代 `pipeline.py` 里手写的 `_continue_from_triage` / `_continue_from_coverage` / `_continue_from_approval` 这些分支跳转函数,对齐 `claims-multiagent-rag-poc` 的 supervisor 模式。图的节点还是同样九个环节;边编码的是 `pipeline.py` 现在硬编码的同一套转移关系。这**不会**改变 MCP 所处的位置:按照 `xingai-enterprise-ai-design` 的文章 [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.md),编排器本身不应该是 MCP Server——MCP 只负责单个 Agent 节点的工具/数据访问,不负责 Agent 之间的交接逻辑。

### 第三方消费 MCP 的认证方式(现在就定,先不接线)

如果/当外部厂商要直接调用这个 POC 的 MCP 工具(未来的"Phase 4 / Direction D",不在本 ADR 范围内),**必须用 OAuth 2.1 + PKCE + JWT、按工具分 scope,不能用静态 API key**——这和 [ADR-006](006-claims-mcp-oauth-poc-real-auth.md) 之前对理赔裁决场景已经得出的结论一致,而且在这里成立的理由更强,因为这条流水线会移动资金、会产生有法律后果的拒赔决定:

- 静态 key 没有 scope 概念——一旦泄露,能干的事和合法调用方完全一样。OAuth scope(`claims.read` / `policy.read` / `claims.adjudicate` / `payments.write`,复用 `claims-mcp-oauth-poc` 已有的词汇表)能让读权限和赔付写权限分开授予、分开吊销。
- 这个领域需要 `claims-mcp-oauth-poc` 的双墙模型——OAuth scope 之外再加一层独立的赔付授权策略(单笔金额上限、理赔类型白名单),因为 scope 本身表达不了"这个合作方不能授权超过 $10,000 的赔付"这类业务规则。
- JWT 的 `sub` claim 能把每一条 Decision Ledger 记录和具体调用方身份绑定,拒赔信和监管报送都需要这一点,共享的静态 key 做不到。

**现在实际做的是什么:** Phase 1 的 `mcp_server/` 用一个单一的静态内部服务 token,因为这个阶段唯一的调用方是我们自己的进程(还没有跨越外部信任边界)——和 `claims-partner-api-mcp-poc` 在 ADR-007 加真实认证之前的起步方式一样。工具的 scope 命名不是新发明的,而是对齐本仓库已有的词汇表:`policy.read` 完全照抄 `claims-mcp-oauth-poc`,`payments.write` 完全照抄 `claims-partner-api-mcp-poc`;`audit.read`/`audit.write` 是新的(两个兄弟 POC 都没有审计追踪工具可以照抄),已在文档里注明。这样做专门是为了将来把真实的 Authorization Server 接到这个 server 前面时,只是一次 scope 映射工作,而不是重写——这和 ADR-007 已经为 `claims-partner-api-mcp-poc` 写好的组合方案是同一套路子。

### 测试策略

主 `pytest` 套件继续保持零 API key 可跑:每个换成 LLM 的 Agent(Phase 2)在 `ANTHROPIC_API_KEY` 未设置时都会用启发式实现兜底;Phase 1 的 MCP client/server 往返直接测试(起 FastAPI test client、调工具、断言响应),不涉及模型。另开一个 `tests/eval/` 目录,标记 `@pytest.mark.eval`,跑真实 LLM 路径,只有在有 key 时才执行(`pytest -m eval`)——这是 `claims-multiagent-rag-poc` 已有的模式("没有 OPENAI_API_KEY 时用离线 hash embedding"),这里是复用而不是重新发明。

## 备选方案

- **跳过 MCP,让每个 Agent 函数直接调 LLM**——已否决。没有工具调用边界,就没有东西强制 Agent 通过一个可审查、有 scope 的接口去访问数据;也会让 Phase 4(对外暴露给第三方)变成重写,而不是"在已有的 server 前面加一个 Authorization Server"。
- **Phase 2、Phase 3 和 Phase 1 一起做**——因交付风险已否决。A+B+C 一起做,体量大约翻倍,同时要做 LLM prompt 设计、RAG 接线、新编排框架;先单独交付 Phase 1(只加数据访问边界、行为不变、还是那 26 个测试)能在投入更具试验性的部分之前有一个检查点。
- **用官方 `mcp` Python SDK / FastMCP,而不是手写 JSON-RPC over FastAPI**——本阶段已否决,纯粹是为了一致性:`claims-mcp-oauth-poc` 在本仓库里已经手写了同一套 `/mcp` JSON-RPC 端点模式,跟着用意味着以后"把 Authorization Server 接到前面"这一步是已知套路,而不是要再调和第二套集成模式。
- **要求所有测试都用真实 API key**——已否决;这会让本 POC"无需外部依赖即可运行"的卖点依赖一个付费外部服务,和 `claims-multiagent-rag-poc` 当初做离线 embedding 兜底时的理由一样。

## 后果

积极的一面:

- Phase 1 引入 MCP 工具边界,行为零变化、零新增外部依赖——风险最低的一步,现有测试套件已完整验证。
- 提前对齐 `claims-mcp-oauth-poc` 的 scope 命名,意味着 Phase 4(如果真要对外暴露)复用一个已经建好的 Authorization Server,而不是再实现一遍认证。
- Phase 2 那张"要不要换成 LLM"的逐环节决策表,是一个可复用的决策框架,其他理赔类或相邻领域的 XingAI POC 可以直接套用,不用每次都重新争论。

权衡取舍:

- 三阶段计划意味着本 ADR 记录的是一份只完成了一部分(Phase 1)的工作——只看"决策"部分而不看"实现状态"的读者会误判进度。
- Phase 1 的静态内部服务 token 明确不适合用于本仓库进程边界之外;只扫一眼"决策"部分、漏看"现在实际做的是什么"的读者,可能会把 scope 命名对齐误认为已经有真实的 OAuth 强制执行——目前还没有。
- 引入 LangGraph 依赖(Phase 3)是本 POC 第一个非 FastAPI/pydantic 的运行时依赖,`claims-multiagent-rag-poc` 出于同样理由(真正的 supervisor 模式)已经接受过同样的权衡。

## 实现状态

- [x] `mcp_server/`——JSON-RPC `/mcp` 端点、4 个工具(`get_policy_coverage`、`record_ledger_decision`、`get_audit_trail`、`create_payment`)、静态内部服务 token、scope 命名对齐 `claims-mcp-oauth-poc`/`claims-partner-api-mcp-poc`
- [x] `claims_workflow.ledger.DecisionLedger` 以及承保核实/赔付两个 Agent 已改为通过 MCP client(`claims_workflow/mcp_client.py`)调工具,不再直接访问字典
- [x] 现有 26 个测试在 MCP 化实现下全部通过,行为无变化(除了 `tests/conftest.py` 的重置 fixture 改成重置 MCP server 的存储而不是本地字典,其余测试文件未改动即验证通过)
- [ ] Phase 2:Fraud Triage / Fraud Scoring / Policy Coverage(RAG)/ 拒赔信起草 换成真 LLM Agent,带启发式兜底
- [ ] `tests/eval/`——跑真实 LLM 路径的 eval 标记测试
- [ ] Phase 3:LangGraph `StateGraph` Supervisor 取代 `pipeline.py` 手写的分支跳转
- [ ] Phase 4(尚未排期):把 `claims-mcp-oauth-poc` 的 Authorization Server 接到 `mcp-server/` 前面,支持真实第三方访问

## 相关

- [ADR-006:Claims MCP OAuth POC——真实认证,不是占位符](006-claims-mcp-oauth-poc-real-auth.zh.md)——本 ADR 沿用的 OAuth/双墙建议的来源
- [ADR-007:Claims Partner API MCP POC——完整 API 覆盖,认证推迟](007-claims-partner-api-mcp-poc-full-coverage.zh.md)——"先对齐 scope 命名、认证以后再接"这套组合方案的来源
- [ADR-008:Claims Workflow v2 POC](008-claims-workflow-v2-poc.zh.md)——本 ADR 深化的 Phase-0 实现
- [pocs/claims-workflow-v2-poc/](../../pocs/claims-workflow-v2-poc/)
- [pocs/claims-mcp-oauth-poc/](../../pocs/claims-mcp-oauth-poc/)——Phase 4 复用的 Authorization Server
- [pocs/claims-multiagent-rag-poc/](../../pocs/claims-multiagent-rag-poc/)——Phase 2/3 复用的 LangGraph supervisor 与 RAG 模式
- `xingai-enterprise-ai-design` [Orchestrator vs MCP Gateway](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-06-13-orchestrator-vs-mcp-gateway.zh.md)——Phase 3"编排器不是 MCP Server"这条约束的来源
- `xingai-enterprise-ai-design` [第三方 MCP 访问——用 API Key 还是 OAuth 2.1?](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.zh.md)——本 ADR 的认证推理被提炼成的通用决策框架
