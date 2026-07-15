# ADR-008:理赔工作流 v2 POC——欺诈排序、升级路由、合规审计三处修复的可运行实现

**日期:** 2026-07-14
**状态:** 已采纳
**作者:** Xing @ XingAI
**其他语言:** [English](008-claims-workflow-v2-poc.md)

## 背景

`xingai-enterprise-ai-design` 的文章 [重新设计理赔工作流](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md) 指出了一张流传较广的理赔自动化信息图中的三处结构性缺口,并分别给出了修复方案:把欺诈检测拆分为损失评估前的分诊(Triage)Agent 和损失评估后的评分(Scoring)Agent;用一个能回到具体环节的 Case Resolution Router 取代单一的笼统"人工审核与升级"盒子;以及用 XingAI 已在别处采用的同一套 Decision Ledger 形态,加上一个跨环节的合规与审计追踪 Agent。

那篇文章是设计文档,不是证明。本仓库已经有一条清晰的分界线——`claims-multiagent-rag-poc` 是本仓库现有的可运行理赔流水线,而它正是**未修复**的形态:一个在成本/损失数据存在之前就跑完的 `Fraud-Check Agent`,以及一个单独的 `Audit Logger` 步骤,而不是每个环节都会写入的跨环节账本。本仓库此前还没有任何东西证明这三处修复在代码里真的能跑通——尤其是,一旦欺诈检测真正拆成信息可用性不同的两个阶段,Router 那张"原因 → 回流环节"的映射表是否还站得住。

## 决策

**新增 `pocs/claims-workflow-v2-poc/`——一个依赖轻量的 Python POC,端到端实现全部三处修复,每处修复各有一个测试模块,外加端到端和 API 测试(共 26 个测试,全部通过)。**

关键实现选择:

- **两个流水线入口,而不是一个循环。** `pipeline.py` 暴露 `submit_claim()`(运行到结算/拒赔/第一次升级为止)和 `resume_claim()`(由 Router 决定回流环节)。这明确地建模了真实的"暂停等人工"边界,而不是在一个函数里传一个可选的 `human_decision` 参数敷衍过去。
- **Router 的键必须扩展。** 文章里的路由表以 `(原因, 结论)` 为键。把它对照一个真正拆成两阶段的欺诈流水线来实现时,暴露出文章那张表没有区分的一种情况:同样是 `fraud_investigation` 升级被人工清除,如果是 Triage 阶段升级的,还需要继续跑损失评估和欺诈评分;如果是 Scoring 阶段升级的,则可以直接跳到保单承保核实。`agents/router.py` 因此改用 `(原因, 阶段, 结论)` 作为键。这是设计文档没有预见到、只有真正写代码才发现的改进——详见 POC README 的"经验教训"部分。
- **不调用任何 LLM,不依赖任何外部服务。** Fraud Triage 和 Fraud Scoring 是确定性的启发式规则(velocity/tenure 阈值;成本异常比例 + 一个照片取证布尔值),`MOCK_POLICIES` 是一个 3 条记录的内存固定数据——与 `claims-mcp-oauth-poc` 的 `MOCK_CLAIMS` 是同一种"可运行但非生产"先例。这让 POC 在零 API key 的情况下也能跑,测试套件也是确定性的,同时让整个演示聚焦在**排序/路由/审计**这套架构本身,而不是模型质量。
- **账本同时是拒赔信和公平性审计的数据来源**,不只是一份日志。`DecisionLedger.adverse_action_letter()` 直接读取产生拒赔的那一条记录的 `policy_clause`;Fraud Triage 和 Fraud Scoring 各自钉住不同的 `model_version` 字符串,专门是为了让一次被标记的决策能追溯到具体是哪个模型做出的。

## 备选方案

- **直接在 `claims-multiagent-rag-poc` 上改**,而不是新建 POC——已否决。那个 POC 的全部价值在于证明 supervisor/RAG/引用这套模式已经完成第一阶段;把它唯一的 `Fraud-Check Agent` 拆成两个、把 `Audit Logger` 换掉,会改变那个 POC 本来要证明的东西,而不只是给它加内容。按照 `POC-STANDARDS.md` "每个 POC 只证明一种架构模式"的规则,这应该是一个独立的 POC。
- **只做"仅架构设计"**(把设计文章的路由表写得更细,不写代码)——在发现 Router 需要按阶段区分之后已否决;这个发现本身就是证据,说明这些修复需要被真正实现和测试才能被信任,而不是继续停留在图纸上。
- **复用 `claims-partner-api-mcp-poc` 的 TypeScript/OpenAPI 路线**,而不是纯 Python 包——已否决;这个 POC 要证明的是 Agent 排序和路由逻辑,不是 API 表面覆盖率,一个进程内的小型 Python 流水线比包一层外部契约的服务更容易逐环节单元测试(见 `tests/`)。

## 后果

积极的一面:

- 首次以可运行的方式证明设计文章里的三处修复确实可以按描述实现,且 Router 需要按阶段区分这一点是通过写代码和写测试发现的,而不是继续留在设计文档里的隐藏缺口。
- `tests/test_fraud_sequencing.py`、`test_router.py`、`test_audit_trail.py` 实质上是这三处修复的可执行规格说明——未来的理赔 POC(或真实实现)都可以拿同一批断言来检验。
- 建立了一套具体的"Fraud Triage vs. Fraud Scoring"模型版本管理模式(`fraud-triage-heuristic-v1` / `fraud-scoring-heuristic-v1`),本仓库中其他做风险评分的 POC 可以照此实现公平性审计的可追溯性。

权衡取舍:

- 本仓库现在有两个理赔流水线类 POC(`claims-multiagent-rag-poc`、`claims-workflow-v2-poc`),形态有重叠但不完全相同;新 POC 的 `enterprise-mapping.md` 已明确交叉引用,避免二者被误读为互相竞争而不是先后演进(v2 具体取代的是 v1 的欺诈检测/升级/审计这几个环节,而不是 v1 同时演示的 RAG/引用模式)。
- Router 按欺诈检测阶段区分状态(`escalation.stage`)这一维度,是原设计文章那张表里没有的——同时阅读文章和代码的人需要 POC README 里"经验教训"那段说明才能理解为什么会不一样。
- 仍然没有认证层,和 `claims-partner-api-mcp-poc` 在 ADR-007 把它与 `claims-mcp-oauth-poc` 的认证模型合并之前是同一个缺口;已在本 POC README 的"尚未生产就绪"部分明确记录,而非悄悄略过。

## 实现状态

- [x] `claims_workflow/` 包——9 个 Agent、`DecisionLedger`、双入口的 `pipeline.py`
- [x] `claims_workflow/api/main.py`——FastAPI 封装,6 个端点
- [x] `tests/`——26 个测试:`test_fraud_sequencing.py`(Fix 1)、`test_router.py`(Fix 2)、`test_audit_trail.py`(Fix 3)、`test_pipeline_e2e.py`(端到端 + API),全部通过
- [x] `docker-compose.yml` + `Dockerfile`
- [x] POC-STANDARDS.md 要求的必备文件:README(英文 + 中文)、architecture.md、enterprise-mapping.md、flow.mmd、references.md
- [ ] 认证/授权层——尚未开始,参考模式见 `claims-mcp-oauth-poc`
- [ ] 理赔/账本/赔付记录的持久化存储——尚未开始
- [ ] Fraud Triage / Fraud Scoring 的真实机器学习模型——尚未开始,目前只有启发式规则

## 相关

- [ADR-006:Claims MCP OAuth POC——真实认证,不是占位符](006-claims-mcp-oauth-poc-real-auth.zh.md)
- [ADR-007:Claims Partner API MCP POC——完整 API 覆盖,认证延后](007-claims-partner-api-mcp-poc-full-coverage.zh.md)
- [pocs/claims-workflow-v2-poc/](../../pocs/claims-workflow-v2-poc/)——README、architecture.md、enterprise-mapping.md
- [pocs/claims-multiagent-rag-poc/](../../pocs/claims-multiagent-rag-poc/)——本 POC 在欺诈检测/升级/审计方面所取代的早期单一欺诈检查流水线
- `xingai-enterprise-ai-design` [articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md)——本 POC 的直接设计来源
- `xingai-learn` ADR-003:Decision Ledger 采用——本 POC 复用的同一套账本形态
