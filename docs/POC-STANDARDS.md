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

Each POC must link back to one or more design docs in:

[xingai-enterprise-ai-design](https://github.com/xingaiapp/xingai-enterprise-ai-design)

## Bilingual Design References

Every POC must include design links in both places:

- `README.md` → `Related Design Docs`
- `references.md` → `XingAI Design Docs`

When the matching design doc exists in both languages, link both:

```md
- EN: [Article title](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/example.md)
- 中文: [中文标题](https://github.com/xingaiapp/xingai-enterprise-ai-design/blob/main/articles/example.zh.md)
```

If the Chinese design doc does not exist yet, write:

```md
- 中文: TODO — add Chinese design doc in `xingai-enterprise-ai-design`
```

Do not leave a POC with only an English design link unless the missing Chinese doc is explicitly marked.

The design repo may link back here when a runnable reference exists.
