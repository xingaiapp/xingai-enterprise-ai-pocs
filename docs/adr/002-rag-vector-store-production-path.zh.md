# ADR-002：RAG 向量库 — POC Chroma 到生产路径

**状态：** Accepted  
**日期：** 2026-06-27  
**作者：** Xing @ XingAI  
**语言：** [English](002-rag-vector-store-production-path.md) · 中文

## 背景

[Claims Multi-Agent RAG POC](../../pocs/claims-multiagent-rag-poc/) 使用**本地 ChromaDB** 与可选 OpenAI embedding（CI 用离线 hash 回退）。适合 demo — 零基础设施、代码可读。

企业评审常问：*保险或合规 RAG 上生产要改什么？* 需要仓库级 ADR，避免 POC 默认 Chroma 即生产。

## 决策

### 1. POC 默认（不变）

| 层 | POC 选择 |
|----|----------|
| 向量库 | Chroma `PersistentClient`，`.cache/chroma` |
| Embedding | 有 key 时用 OpenAI `text-embedding-3-small`；离线 hash |
| 集合 | 按域分离（保单 / 历史 / 法规 — 不混用） |
| 引用 | 每 chunk：`document_id`、`chunk_id`、相似度 |

### 2. 生产路径（文档化，POC 不实现）

| 需求 | 生产目标 |
|------|----------|
| HA / 多实例 | 托管向量库（Pinecone、Weaviate、RDS pgvector） |
| 加密 | 静态 + 传输 TLS； regulated 租户可 CMK |
| PII | embed 前字段级脱敏；按数据类分集合 |
| 保留 | 源文档 TTL + legal hold |
| 审计 | 每次查询记 trace_id、集合、top-k id；日志无原始 PII |
| Embedding | 托管模型 + 合同；无 DPA 不向第三方 embed 原始 PII |

**接口规则：** Retrieval agent 依赖抽象 `VectorStoreClient` — POC 用 Chroma；生产换实现，不改 agent prompt 与 citation schema。

### 3. 何时迁离 Chroma

**任一**触发：

- 多租户隔离
- >50 万 chunk 或 >50 QPS 并发查询
- 合规要求 SOC2 托管向量服务
- 跨区复制

此前 Chroma 单 worker 卷仅适合**内部** staging — 非客户生产。

### 4. MCP / 摄入（生产扩展）

POC 用合成 markdown。生产增加 PDF/邮件 intake、政策系统 MCP **只读**、入向量库前人工审核队列。

## 备选方案

- **POC 直接用 Pinecone** — 拒绝（demo 基础设施过重）。
- **单一混合集合** — 拒绝（跨域噪声；违反 ADR-001 引用纪律）。

## 实现状态

- [x] ADR-002 文档
- [x] Claims POC Chroma + hash 回退
- [ ] `VectorStoreClient` 接口抽取
- [ ] Pinecone adapter 文档占位

## 相关

- [ADR-001](./001-supervisor-audit-human-in-the-loop.zh.md)
- [Claims POC 架构](../../pocs/claims-multiagent-rag-poc/architecture.md)
