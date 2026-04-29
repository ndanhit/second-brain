# Example raw note — delete or replace this

This file shows what a raw, free-form note looks like before ingestion. After
you've confirmed the pipeline works, delete this file (and anything it
generated under `1-projects/`, `2-areas/`, `3-resources/`).

---

## Sync with the platform team — 2026-04-29

Met with the platform team. Quick summary:

- We're standing up a new **Notification Service** to centralize email, push,
  and SMS. Current target: GA by end of Q3 2026.
- Architecture: HTTP API in front, RabbitMQ for fan-out, per-channel workers.
- Owner: platform-core team, on-call rotates weekly.
- Dependency on the existing **User Service** for recipient resolution.
- Retry policy: exponential backoff, 5 attempts max, dead-letter queue after
  that. We had an incident last month where a misconfigured retry loop hit
  the SMS provider's rate limit — playbook needed.

### Decisions
- Use RabbitMQ over Kafka — lower ops cost, our throughput needs are modest.
  This is ADR-0001 territory.

### Concepts I should capture
- **Dead-letter queue (DLQ)** — where events go when retries are exhausted.
  Separate from the main queue; reviewed weekly.
- **Fan-out** — one event triggers multiple downstream channels.

### Open questions
- Who owns the SMS provider relationship? Need to ask.
