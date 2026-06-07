# Contributing Guidelines

Thank you for contributing to XingAI Enterprise AI POCs.

This repository is for runnable proof-of-concept projects that validate enterprise AI architecture patterns. A good POC is small, honest, and tied to a design document.

## What We Accept

### Accepted

- Runnable POCs for enterprise AI architecture patterns
- Reference implementations tied to `xingai-enterprise-ai-design`
- Architecture experiments with clear tradeoffs
- Reusable schemas, fixtures, Docker setup, or test harnesses for POCs
- Lessons learned from failed or incomplete experiments

### Not Accepted

- Marketing demos
- Product apps
- One-off scripts without an architecture pattern
- POCs with no linked design doc
- Code that hides production gaps instead of naming them

## Required Before Adding a POC

Every POC must include:

- A `README.md`
- An `architecture.md`
- A `flow.mmd`
- A `references.md`
- Links to the matching English and Chinese design docs in `xingai-enterprise-ai-design`
- A clear `Not Production Yet` section

See [`POC-STANDARDS.md`](POC-STANDARDS.md).

## Contribution Flow

1. Pick or create a design topic in `xingai-enterprise-ai-design`.
2. Make sure the design topic has English and Chinese versions, or add a TODO for the missing Chinese version.
3. Create a POC folder under `pocs/<kebab-case-name>/`.
4. Keep the first version narrow. Prove one pattern.
5. Update the root `README.md` POC index and version notes.
6. Open a PR with a short summary of what the POC proves.

## POC README Checklist

- [ ] The POC proves one clear architecture pattern.
- [ ] `Related Design Docs` includes EN + 中文 links.
- [ ] `Not Production Yet` names missing production controls.
- [ ] Mermaid diagram exists in `flow.mmd`.
- [ ] `references.md` repeats the design links and adds implementation notes.
- [ ] Root `README.md` index is updated.
- [ ] `VERSION` and root README version notes are updated when needed.

## Review Standard

Reviewers should ask:

- Is this an architecture proof, or just a demo?
- Is the design doc linked in both languages?
- Is the production boundary honest?
- Can another engineer run or extend it?
- Does it support the enterprise AI decision-system positioning?
