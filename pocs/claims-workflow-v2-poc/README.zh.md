# 理赔结算工作流 v2(XingAI 修正版设计)

> **状态:可运行 · Phase 1 + 2 + 3**(MCP 工具访问、带启发式兜底的 LLM 欺诈/承保/信件 Agent、LangGraph Supervisor——见 [ADR-009](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.zh.md))

**模式:** 多智能体理赔流水线,拆分欺诈检测、显式升级路由器、跨环节合规审计追踪
**其他语言:** [English](README.md)

---

## 本 POC 要证明什么

一张流传较广的理赔自动化信息图,整体形状是对的——顺序专职 Agent、分级审批、人工升级路径——但一旦追问"这套系统连续跑一年、还要应付监管机构提问会怎样",就会在三个具体地方站不住脚:欺诈检测在拿到成本/照片数据之前就跑完了、每条升级路径都汇入同一个笼统的人工审核盒子且没有清晰的回流路径、也没有任何东西为以后留痕。本 POC 证明这三处修复不仅能画在图上,还真的能实现:欺诈检测拆分为损失评估前的分诊(Triage)和损失评估后的评分(Scoring)两个 Agent;Case Resolution Router 让每次升级都回到具体环节而不是从受理重新开始;以及一个每个环节都会写入的、Decision Ledger 形态的审计追踪。

## 体现的企业级模式

- 双入口(submit / resume)的多智能体流水线,用来建模真实的"暂停等人工"边界
- 按信息可用性拆分欺诈检测,而不仅仅是按流水线位置拆分
- 显式且有记录的路由决策,取代隐式的"重启整个工作流"回环
- 内建合规:每个 Agent 决策都是一条账本记录,而不是副作用
- 拒赔信复用产生拒赔决策的那条账本记录和具体保单条款生成,而非泛泛而谈
- 幂等的赔付写入,与 [claims-partner-api-mcp-poc](../claims-partner-api-mcp-poc/) 的要求一致
- 数据访问(保单查询、Decision Ledger、赔付)都在一个 MCP Server 后面,不再直接访问字典——见 [ADR-009](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.zh.md)
- 设置了 `ANTHROPIC_API_KEY` 时,Fraud Triage/Scoring、Policy Coverage、拒赔信起草都会跑真 LLM Agent,没设置时用启发式兜底(和 Phase 1 决策逻辑一致)——每条账本记录的 `model_version` 都记录了实际跑的是哪条路径
- Policy Coverage 的 LLM 路径通过一个依赖轻量的 RAG 层检索真实条款文本(包括除外条款),所以在扁平的承保查询会说"承保"的情况下,只要除外条款确实适用,它依然能拒赔
- 编排逻辑用图来表达(`claims_workflow/graph/`),不再是嵌套的 if/return 分支跳转——同样的 8 个 Agent 函数作为图节点,Case Resolution Router 负责挑图该从哪个节点恢复

## 尚未生产就绪

- 无持久化——理赔、Decision Ledger、赔付记录都存在内存字典里,重启即丢失
- API 前面没有认证/授权层,MCP Server 本身也只用一个静态内部服务 token——升级路径见 [claims-mcp-oauth-poc](../claims-mcp-oauth-poc/) 和 [ADR-009](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.zh.md)
- 没有 `ANTHROPIC_API_KEY` 时,每个 LLM Agent 都跑启发式兜底——LLM 路径是真实的,但只有 `tests/eval/`(`pytest -m eval`)和手动运行会真正触发它,默认测试套件不会
- `MOCK_POLICIES` / `policy_documents.py` 只是小型固定数据,不是真实保单管理系统的对接
- 没有多租户隔离、限流、可观测性
- `resume_claim()` 直接把人工决策当参数传入——还没有真正的审核队列 UI 或通知系统
- LangGraph Supervisor(`claims_workflow/graph/`)没有用真正的 checkpoint 机制——一次理赔的解决是在一次 `submit_claim`/`resume_claim` 调用内同步完成的,不是跨进程暂停再恢复;生产版本需要什么,见 ADR-009"Phase 3 实现笔记"
- 完整缺口分析(按 AI Agent / MCP / 自动化 / 理赔行业监管四个维度组织,附优先级建议)见 [PRODUCTION-READINESS.zh.md](PRODUCTION-READINESS.zh.md)

## 架构

完整图表见 [`flow.mmd`](flow.mmd),组件级细节见 [`architecture.md`](architecture.md)。概要:

```text
受理 → 单证核验 → 欺诈分诊 → 损失评估 → 欺诈评分
     → 保单承保核实 → 审批 → 赔付

任何环节都可以升级到 Case Resolution Router,由它根据升级原因 + 人工结论
决定回到哪个具体环节(而不是回到受理)。无论结果如何,每个环节都会写入
Decision Ledger。
```

## 快速开始

```bash
cd pocs/claims-workflow-v2-poc
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt

pytest -q                      # 40 个测试,不需要任何 API key——走启发式兜底路径
export ANTHROPIC_API_KEY=sk-...  # 可选——启用真实 LLM 路径
pytest -m eval -q              # 另外 5 个跑真实模型的测试(没有 key 时会跳过)

uvicorn claims_workflow.api.main:app --reload --port 8091
# 另开一个终端,可选: uvicorn mcp_server.main:app --port 8092
# (不是必须的——claims_workflow 默认走进程内直连 mcp_server;
#  想指向一个单独跑着的实例,设置 MCP_SERVER_URL 即可)
# 或者: docker compose up --build
```

## API

| 方法 | 路径 | 用途 |
|---|---|---|
| `POST` | `/claims/submit` | 提交新理赔;运行到结算、拒赔或第一次升级为止 |
| `GET` | `/claims/{id}` | 查询理赔当前状态 |
| `POST` | `/claims/{id}/resolve` | 用人工结论解决当前的升级;Router 决定回到哪个环节 |
| `GET` | `/claims/{id}/audit` | 该理赔完整的 Decision Ledger 历史 |
| `GET` | `/claims/{id}/adverse-action-letter` | 若理赔被拒,返回拒赔信 |
| `GET` | `/health` | 存活检查 |

## 团队演示脚本

1. `POST /claims/submit` 一个干净的车险理赔(`policy_id=POL-1001`,`reported_amount=3000`)→ 直接走到 `status=paid`。`GET /claims/{id}/audit` 显示全部 8 个环节都有记录。
2. 提交同样的理赔但 `prior_claims_count=5` → 在 `fraud_triage` 环节升级,**此时还没有任何损失估算**(响应里 `damage_cost` 为 `null`)。这是 Fix 1 的前半部分。
3. 提交 `reported_amount=3000`、`assessed_cost_hint=1000` 的理赔(损失评估阶段会用到这个提示)→ 顺利通过 Triage,但在 `fraud_scoring` 环节被抓住,因为此时成本异常才可见。这是 Fix 1 的后半部分——同一个理赔,两个不同的欺诈 Agent,能不能看见取决于跑在哪个阶段。
4. 用 `outcome=resolved` 和 `documents_added` 解决一个 `missing_docs` 升级 → 理赔回到单证核验环节并顺利完成;`GET /claims/{id}/audit` 显示只有一条 `intake` 记录——证明 Router 没有重启整条流水线。这是 Fix 2。
5. 提交 `loss_type=property` 但保单是 `POL-1001`(只承保车险)的理赔 → 被拒。`GET /claims/{id}/adverse-action-letter` 返回具体的保单条款,而不是一句笼统的话。这是 Fix 3。
6. 设置好 `ANTHROPIC_API_KEY` 后,提交一个 `loss_description="Was racing a friend on a closed course when I hit a wall."` 的车险理赔,保单用 `POL-1001`——LLM 版 Policy Coverage 会因为赛车除外条款拒赔,即便 `loss_type=auto` 在扁平查询里本来是"承保"的,这是扁平查询做不到的事。查 `GET /claims/{id}/audit`,`model_version` 会以 `policy-coverage-llm-` 开头。

## 经验教训

- Router 里"按阶段区分"的分支(`fraud_investigation` + `cleared` 时,如果升级来自 Triage 就回到 `damage_assessment`,如果来自 Scoring 就回到 `policy_coverage`)并不在设计文章最初的路由表里——那张表是在欺诈检测拆分之前写的。真正把 Router 写成代码时才发现:只按 `reason` 做键无法正确恢复一个 Triage 阶段的清除结果,因为这时候损失评估和欺诈评分确实还没跑过。文章里的表对单一欺诈环节是对的;拆分欺诈检测之后,Router 的键必须从 `(reason, outcome)` 扩展成 `(reason, stage, outcome)`。
- 把赔付幂等存储写成一个普通的模块级字典,让"重放返回同一条记录"这个测试几乎是显而易见地好写——也让偏差立刻暴露:早期草稿在重放时生成了新的 `settled_at` 时间戳,被测试当场抓住。
- 把 `submit_claim` / `resume_claim` 写成两个独立函数,而不是一个默认 `human_decision=None` 的循环,让 API 层的推理简单了很多(`POST /submit` 和 `POST /resolve` 可以直接对应过去)——单函数版本总是诱使 API handler 传入不完整的状态。
- (Phase 2)在测试里直接 monkeypatch `llm_client._call_anthropic` 来模拟网络故障,暴露出 `complete_json`/`complete_text` 一直在信任 `_call_anthropic` 总会抛 `LLMError`——一个被 monkeypatch(或者真的出故障)的版本抛出的原始异常,本会直接穿过每个 Agent 的 `except LLMError` 兜底逻辑。修法是在 `complete_json`/`complete_text` 自己内部再包一层(`_safe_call_anthropic`),而不是只依赖 `_call_anthropic` 内部那一层。
- (Phase 3)LangGraph 常规的恢复机制是持久化 checkpoint 加 `thread_id`——本 POC 不需要(一次理赔的解决是在一次调用内同步完成的),所以 `build_graph(entry_point)` 改成每次调用都编译一个从 Router 选中环节开始的全新图,而不是维护一个长期存活、带 checkpoint 的图。值得明确说这是一次缩小范围的替代,不是同一套机制——一个真的"暂停几天、由另一个进程恢复"的理赔需要的是本 POC 没有实现的那套真正的 checkpoint 机制。
- (Phase 2)Policy Coverage 的 RAG 不需要向量数据库——每个保单的条款语料库小到一个约 40 行的纯 Python 哈希词袋向量化就足够检索出正确的除外条款,依赖清单完全没变,没有像 `claims-multiagent-rag-poc` 那样为了更大规模的跨保单检索问题引入 `chromadb`。

## 相关设计文档

- EN: [Redesigning the Agentic Claims Workflow](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md)
- 中文: [重新设计理赔工作流](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md)
- [理赔结算工作流 v2 图表](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/assets/ARCHITECTURE-DIAGRAMS.md#claims-settlement-workflow-v2-xingai-corrected-design)
- [第三方 MCP 访问——用 API Key 还是 OAuth 2.1?](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.zh.md) · [EN](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-15-third-party-mcp-auth-api-key-vs-oauth2.md)
- [ADR-008: Claims Workflow v2 POC](../../docs/adr/008-claims-workflow-v2-poc.md) · [中文](../../docs/adr/008-claims-workflow-v2-poc.zh.md)
- [ADR-009:MCP 工具访问、LLM Agent、LangGraph Supervisor](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.zh.md) · [EN](../../docs/adr/009-claims-workflow-v2-mcp-multiagent.md)
- [PRODUCTION-READINESS.zh.md](PRODUCTION-READINESS.zh.md) · [EN](PRODUCTION-READINESS.md) —— 生产就绪度缺口分析
- 完整列表(含兄弟 POC)见 [`references.md`](references.md)
