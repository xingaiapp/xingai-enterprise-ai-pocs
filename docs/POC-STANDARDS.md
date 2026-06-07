# POC Standards

POCs in this repo are architecture proofs. They exist to test enterprise AI patterns before those patterns become production systems.

## Required Files

Each POC folder should include:

```text
README.md
architecture.md
flow.mmd
references.md
```

Use `flow.mmd` for Mermaid diagrams that can be embedded in articles or exported to images.

## Required README Sections

Every POC README should include:

- `What This Proves`
- `Enterprise Pattern`
- `Not Production Yet`
- `Architecture`
- `Flow`
- `Lessons Learned`
- `Related Design Docs`

## Naming

Use lowercase kebab-case:

```text
pocs/event-bus-ai-review
pocs/human-in-the-loop-decision
pocs/memory-layer-demo
```

Avoid `demo` unless the folder is explicitly a visual demo. Prefer `poc`, `reference`, or a pattern name.

## Production Boundary

Every POC must clearly state what is missing before production:

- authentication and authorization
- tenant isolation
- secrets management
- audit retention
- observability
- compliance controls
- cost controls
- deployment hardening

## Cross-Repository Links

Each POC should link back to one or more design docs in:

[xingai-enterprise-ai-design](https://github.com/xingaiapp/xingai-enterprise-ai-design)

The design repo may link back here when a runnable reference exists.
