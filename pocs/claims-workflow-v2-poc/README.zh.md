# 理赔结算工作流 v2(XingAI 修正版设计)

> **状态:可运行 · 第一阶段**

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

## 尚未生产就绪

- 无持久化——理赔、Decision Ledger、赔付记录都存在内存字典里,重启即丢失
- API 前面没有认证/授权层——可运行的参考实现见 [claims-mcp-oauth-poc](../claims-mcp-oauth-poc/)
- Fraud Triage / Fraud Scoring 是启发式规则(`agents/fraud_triage.py`、`agents/fraud_scoring.py`),不是训练出来的模型——在换成真实模型之前无法做真正的公平性/偏见审计
- `MOCK_POLICIES` 只是一个 3 条记录的固定数据,不是真实保单管理系统的对接
- 没有多租户隔离、限流、可观测性
- `resume_claim()` 直接把人工决策当参数传入——还没有真正的审核队列 UI 或通知系统

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

pytest -q                      # 26 个测试——每处修复各有覆盖,外加端到端和 API 测试

uvicorn claims_workflow.api.main:app --reload --port 8091
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

## 经验教训

- Router 里"按阶段区分"的分支(`fraud_investigation` + `cleared` 时,如果升级来自 Triage 就回到 `damage_assessment`,如果来自 Scoring 就回到 `policy_coverage`)并不在设计文章最初的路由表里——那张表是在欺诈检测拆分之前写的。真正把 Router 写成代码时才发现:只按 `reason` 做键无法正确恢复一个 Triage 阶段的清除结果,因为这时候损失评估和欺诈评分确实还没跑过。文章里的表对单一欺诈环节是对的;拆分欺诈检测之后,Router 的键必须从 `(reason, outcome)` 扩展成 `(reason, stage, outcome)`。
- 把赔付幂等存储写成一个普通的模块级字典,让"重放返回同一条记录"这个测试几乎是显而易见地好写——也让偏差立刻暴露:早期草稿在重放时生成了新的 `settled_at` 时间戳,被测试当场抓住。
- 把 `submit_claim` / `resume_claim` 写成两个独立函数,而不是一个默认 `human_decision=None` 的循环,让 API 层的推理简单了很多(`POST /submit` 和 `POST /resolve` 可以直接对应过去)——单函数版本总是诱使 API handler 传入不完整的状态。

## 相关设计文档

- EN: [Redesigning the Agentic Claims Workflow](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.md)
- 中文: [重新设计理赔工作流](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-14-claims-workflow-redesign-fraud-routing-audit.zh.md)
- [理赔结算工作流 v2 图表](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/assets/ARCHITECTURE-DIAGRAMS.md#claims-settlement-workflow-v2-xingai-corrected-design)
- [ADR-008: Claims Workflow v2 POC](../../docs/adr/008-claims-workflow-v2-poc.md) · [中文](../../docs/adr/008-claims-workflow-v2-poc.zh.md)
- 完整列表(含兄弟 POC)见 [`references.md`](references.md)
