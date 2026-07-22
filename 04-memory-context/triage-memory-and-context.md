# Context Engineering and Memory Plan: Cortex Email Triage Agent 

## Context budget

Each iteration gets the incoming email task brief, any pulled thread history or unread email tool results, and critic feedback, nothing else to keep the context window tight and cheap.

## Per-source: retrieve vs long-context

| Source | Decision | Why |
|---|---|---|
| Inbound Task Brief (`task['body']`) | Long-context | Small, bounded corpus; required entirely for every run to understand the immediate email context. |
| Thread History (`get_thread_history`) | Retrieve | Volatile and potentially long per-thread; fetched selectively only when an active thread ID is present. |
| Unread Emails / Fixtures (`get_unread_emails`) | Retrieve | Dynamic corpus depending on active test scenario or inbox state; retrieved on-demand with explicit parameters. |
| System Prompts & Norms (`CORTEX_SYSTEM`) | Long-context | Fixed foundational rules governing agent behavior, safety guardrails, and compliance limits. |

## Retrieval quality plan

To avoid naive RAG and ensure strict grounding, the retrieved sources implement the following quality moves:

| Retrieved Source | Routing | Document Grading | Reranking | Self-Verification | Caching |
| :--- | :---: | :---: | :---: | :---: | :---: |
| **Unread Emails (`get_unread_emails`)** | ✓ | ✓ | · | ✓ | · |
| **Thread History (`get_thread_history`)** | ✓ | ✓ | ✓ | ✓ | · |

* **Document Grading & Self-Verification:** Every payload fetched must pass structural checks (e.g., verifying `fixtures[0]["body"]` exists) to prevent fallback stubs from masquerading as real context.

## Memory map

| Memory Type | What Cortex Stores | Lifetime / Scope |
| :--- | :--- | :--- |
| Working Memory | The inbound email body, pulled message IDs, current run details, and the drafted email replies/classifications generated during the run. | Current run only (cleared after execution or HITL checkpoint). |
| Episodic Memory | Prior interactions within the same customer thread or ticket history. | Per-thread; ages out or resets per session. |
| Semantic Memory| Durable classification categories, safety boundaries, and escalation triggers. | Long-lived; updated deliberately via prompt/code versioning. |
| Shared Memory| Independent critic validations, verification verdicts (`pass`/`fail`), and reasons. | Scoped strictly to the collaboration loop between Cortex and the Critic. |

## Memory risks and mitigations

| Risk | Mitigation |
|---|---|
| Drift | Source validation rules; mandatory re-fetching of volatile fixtures/payloads per run. |
| Poisoning | Strict system guardrails (`IGNORE` instructions trying to change rules); first-party validation. |
| Staleness | Zero long-term caching of volatile email data; strict TTL/run-scoping. |
| PII / Retention | Minimal retention scope; working memory clears immediately upon run completion. |

