# ADR-005: Loop Engineering and 17-Layer Platform Reference Architecture

**Date:** 2026-07-03
**Status:** Accepted
**Author:** Xing @ XingAI
**Also available:** [中文](005-loop-engineering-platform-layers.zh.md)

## Context

ADR-001 through ADR-004 established the POC patterns for supervisor orchestration, RAG, MCP gateway placeholders, and event bus design. These cover **Layer 2 (Harness Engineering)** of the enterprise agent stack.

The [Enterprise Agent Platform](../ENTERPRISE-AGENT-PLATFORM.md) document describes the vision: goal-driven agent collaboration. But it does not specify how **Layer 3 (Loop Engineering)** — autonomous scheduling, reflection, and stop conditions — fits into the platform architecture, or how the functional and governance layers decompose.

The [Beyond Prompt Engineering](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/2026-07-03-beyond-prompt-engineering-loop-engineering.md) article introduces the three-layer architecture (Context → Harness → Loop) and a 17-layer platform decomposition. This ADR adopts that framework as the reference architecture for future POCs and enterprise platform design.

## Decision

### 1. Three-Layer Agent Architecture

Every POC and production agent follows three layers:

```text
┌──────────────────────────────┐
│ Layer 3: Loop Engineering    │
│ Entry point • Loop body •    │
│ Stop condition • Guardrails  │
└──────────────────────────────┘
┌──────────────────────────────┐
│ Layer 2: Harness Engineering │
│ Tools • Skills • Memory •    │
│ Multi-Agent • Permissions    │
└──────────────────────────────┘
┌──────────────────────────────┐
│ Layer 1: Context Engineering │
│ Prompt • RAG • User profile •│
│ Conversation • Runtime state │
└──────────────────────────────┘
```

POC-level work validates one or two layers at a time. Production work must address all three.

### 2. 17-Layer Platform Decomposition

The enterprise platform decomposes into 11 functional layers and 6 governance layers:

**Functional (11):** Traffic, API Gateway, Message Queue, Planner Agent, Business Agent, Skills, AI Gateway, Model Layer, MCP/Tools, Knowledge, Memory.

**Governance (6):** Configuration Center, Agent Registry, Evaluation Center, AI Security, AI Governance, Elastic Scaling.

The model is one of seventeen layers. POCs should clearly label which layers they validate.

### 3. Loop Guardrails Are Mandatory

Any POC or production agent that loops must define:

| Guardrail | Requirement |
|-----------|-------------|
| Max iterations | Hard cap (e.g., 5) |
| Token budget | Enforced by harness, not prompt |
| No-progress detection | Auto-stop after 2 stalled iterations |
| Wall-clock timeout | Prevent hung agents |
| Human approval gate | Required for high-risk actions |

### 4. Micro Loop Engine as Target Pattern

The long-term target is dynamic agent assembly (Micro Loop Engine) rather than hardcoded agents. POCs should design their skills, tools, and memory as composable components that a future engine can assemble.

## Alternatives

| Option | Outcome |
|--------|---------|
| Keep building POCs without layer labels | Teams can't map POC findings to production architecture |
| Adopt a different layer model | The three-layer + 17-layer model aligns with the existing Enterprise Agent Platform doc and XingAI product architectures |
| Skip loop guardrails in POCs | Bad habits carry into production; cost overruns in POC stage |

## Consequences

- Every new POC README must state which of the three layers and which of the 17 platform layers it validates
- Loop-based POCs must implement at least max iterations + token budget guardrails
- The Enterprise Agent Platform doc should be updated to reference this three-layer + 17-layer framework
- Skills, tools, and memory designed for POCs should follow composable interfaces so they can be reused by a Micro Loop Engine

## Migration Triggers

- If the industry converges on a different standard layering (e.g., a widely-adopted framework defines different layers), revisit and align
- If Micro Loop Engine moves from design-only to POC, create ADR-006 for the engine's assembly contract
