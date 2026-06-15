# POC Standards

POCs in this repo are architecture proofs. They exist to test enterprise AI patterns before those patterns become production systems.

## Required Files

Each POC folder must include:

```text
README.md               — overview, quick start, API, demo script
architecture.md         — component design and responsibilities
enterprise-mapping.md   — POC vs Platform mapping table + leadership positioning
flow.mmd                — Mermaid flow diagram (embeddable in articles)
references.md           — bilingual design doc links + external references
```

For runnable POCs, also include:

```text
backend/
  Dockerfile
  docker-compose.yml    (at poc root level)
  requirements.txt
  requirements-dev.txt
  pytest.ini
  tests/
    conftest.py
    test_api.py
    test_orchestrator.py (or equivalent)
```

Use `flow.mmd` for Mermaid diagrams that can be embedded in articles or exported to images.

## Status Label

Every POC README must open with one of these status labels:

```md
> **Status: Runnable · Phase N**

> **Status: Architecture Design Only — not yet runnable.**
```

This prevents contributors from searching for code that does not exist.

## Required README Sections

Every POC README must include:

- `What This Proves` — the specific architecture pattern this validates (1 paragraph)
- `Enterprise Pattern` — bullet list of enterprise concepts demonstrated
- `Not Production Yet` — explicit list of missing production controls
- `Architecture` — Mermaid diagram or component table
- `Quick Start` — runnable POCs must include working commands
- `API` — endpoint table for runnable POCs
- `Team Demo Script` — how to walk a 5-minute leadership demo
- `Lessons Learned` — see guidance below
- `Related Design Docs` — bilingual links

## Lessons Learned: How to Fill It

The `Lessons Learned` section is the most valuable part of a POC. Fill it after you first run the POC end-to-end. Good lessons describe:

- **What surprised you** — something the architecture diagram did not predict
- **What broke** — a real failure and how you fixed it or worked around it
- **What you would do differently** — a decision you would reverse in Phase 2
- **What the demo revealed** — audience reactions that changed your understanding

Bad lessons: "The POC worked as expected." That is not a lesson.

Good example:

```md
## Lessons Learned

- The orchestrator planning step (step 1) adds ~50ms and no value in the trace UI.
  In Phase 2, collapse it into the first specialist call to clean up the timeline.
- Audience assumed the fake_research_tool was real. Add a clearer "simulated" label
  in the trace step — the current "(POC demo)" text is too subtle.
- Running the same prompt twice immediately reveals cache behavior,
  which was the most compelling moment in every demo we ran.
```

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
