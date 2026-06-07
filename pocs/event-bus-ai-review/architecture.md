# Architecture: Event Bus AI Review

This POC starts with a narrow workflow:

```text
event -> AI review -> compliance review -> human approval -> audit log
```

The key design point is that AI review and compliance review subscribe to the same business event independently. The orchestrator should not hide compliance checks inside the agent prompt.

## Components

- `event bus` — receives events and fans out work
- `ai review worker` — builds a recommendation packet
- `compliance checker` — adds policy constraints
- `human approval` — confirms or rejects the action
- `audit log` — stores inputs, outputs, reviewer action, and timestamps

## Success Criteria

- AI and compliance workers are independently replaceable.
- Every decision has an audit record.
- Human approval receives enough context to act without reading raw logs.
- Failure in one worker does not erase the original event.
