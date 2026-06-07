# XingAI Enterprise AI POCs

**Version:** 0.1.2

Runnable proof-of-concept projects for enterprise AI decision systems and architecture patterns.

This repository pairs with [xingai-enterprise-ai-design](https://github.com/xingaiapp/xingai-enterprise-ai-design), which explains the architecture patterns. This repo keeps the runnable POCs, reference implementations, experiments, and deployment notes.

## What This Repository Is

- A home for runnable enterprise AI POCs
- A place to test architecture patterns before productizing them
- A reference implementation library for articles in `xingai-enterprise-ai-design`
- A record of tradeoffs, failures, and lessons learned

## What This Repository Is Not

- Not a product repo
- Not a marketing demo collection
- Not production-ready enterprise software
- Not a replacement for product-specific XingAI apps

## POC Index

| POC | Pattern | Status | Related Design Topic |
|---|---|---|---|
| Event Bus AI Review | Event-driven AI decisions | Planned | Enterprise AI decision systems |
| Human-in-the-Loop Decision | Approval workflow | Planned | Human approval layers |
| Memory Layer Demo | User + organization memory | Planned | Memory architectures |
| MCP Tool Gateway | Tool routing and governance | Planned | MCP in enterprise AI |

## Repository Structure

```text
pocs/
  event-bus-ai-review/
  human-in-the-loop-decision/
  memory-layer-demo/
  mcp-tool-gateway/
shared/
  schemas/
  docker/
docs/
  CONTRIBUTING.md
  POC-STANDARDS.md
```

## POC Standard

Every POC should answer four questions:

1. What architecture pattern does this prove?
2. What is intentionally missing because this is not production?
3. What did we learn from building it?
4. Which English and Chinese design docs does it support?

See [`docs/POC-STANDARDS.md`](docs/POC-STANDARDS.md).

## Contributing

See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) for contribution guidelines.

## Version Notes

### 0.1.2

- Add contribution guidelines for new POCs
- Require contributors to update POC index, version notes, and bilingual design references

### 0.1.1

- Require every POC to reference matching `xingai-enterprise-ai-design` docs in both English and Chinese when available
- Update the Event Bus AI Review placeholder with bilingual design links

### 0.1.0

- Initial repository structure
- POC standards
- First POC placeholders for enterprise AI decision-system patterns

## Related Repositories

- [xingai-enterprise-ai-design](https://github.com/xingaiapp/xingai-enterprise-ai-design) — architecture articles, diagrams, and design patterns
- [xingai-tech-blog](https://github.com/xingaiapp/xingai-tech-blog) — engineering stories and implementation notes
- [xingai-dot-app](https://github.com/xingaiapp/xingai-dot-app) — XingAI marketing site

## License

Code and docs are owned by XingAI unless a specific POC folder declares a different license.
