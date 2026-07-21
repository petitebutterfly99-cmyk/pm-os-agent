# Orchestration Map: Cortex Email Triage Agent

## Why split (single agent vs a team)

Cortex Email Triage Agent stays a single agent because none of the four splitting criteria genuinely apply to its current architecture. Separation of concerns is maintained within a single workflow, parallelism is unnecessary for the bounded lab volume, context-window pressure is actively managed via per-thread isolation and compression, and safety/validation is successfully handled by the required human review rather than an autonomous critic subagent.

## Topology

Critic / validator loop
```text
[ Inbound Gmail Message ]
         │
         ▼
┌─────────────────────────────────┐
│        CORTEX (Primary)         │
│   - Reads & classifies email    │
│   - Drafts response/summary     │
└────────────────┬────────────────┘
                 │
                 │ (Passes draft + source data)
                 ▼
┌─────────────────────────────────┐
│      VALIDATOR (Critic)         │
│   - Checks commitment boundaries│
│   - Validates data traceability │
│   - Enforces tone & safety rules│
└──────┬───────────────────┬──────┘
       │                   │
       │ (Fail + feedback) │ (Pass)
       ▼                   ▼
  [ Return to Cortex ]  [ Human PM Review Checkpoint ]
  (Max 2 revisions)      (Gmail draft saved, never auto-sent)
```
## Agent roster

| Agent | Role | Model tier |
|---|---|---|
| Cortex (Primary Agent) | Processes inbound emails, reads thread history, classifies messages, drafts responses, and manages state/escalations. | Fast |
| Validator (Critic Subagent) | Evaluates Cortex's draft and classification against strict safety bounds, data traceability, tone, and commitment rules. | Fast |

## The validating subagent (critic)

- **What it checks**: Commitment Boundary Check: Verifies that the draft contains zero unapproved commitments, including release dates, roadmap deliverables, feature guarantees, discounts, refunds, or policy exceptions.
Data Traceability Check: Ensures every statement or issue reference matches the pulled email body and thread history without introducing invented facts, fabricated technical causes, or hallucinated details.
Classification Alignment Check: Validates that the assigned classification (issue, enhancement request, unclear, or unrelated) matches the actual content of the inbound message.
Tone and Safety Check: Confirms the tone aligns with professional customer support standards and that no sensitive security, legal, or privacy disclosures are present in the text.
- **Fail-action**: If any check fails, the critic rejects the draft and returns it directly to Cortex with specific failure annotations.
- **Revision cap**: Cortex is allowed a maximum of 2 revision passes to fix the flagged errors. If the draft still fails validation after 2 attempts, the loop automatically halts local drafting and escalates the thread directly to the human PM with all failure logs attache

## Hand-offs

Cortex → Validator: Passes the drafted email response, classification metadata, and the source email body/thread history as structured text. (Protocol: Plain in-process hand-off; MCP/A2A optional/not required)

Validator → Cortex (Pass): Passes a clear pass signal allowing the draft to advance to the human review checkpoint.

Validator → Cortex (Fail): Passes a fail signal along with an itemized list of failed checks and specific failure annotations, up to the maximum 2-revision limit.

Validator → Human PM (Escalation): If revision limits are exceeded or critical risk triggers are hit, routes the failure context directly to the human review queue.

## Shared state

Shared State: The source email content, thread history, current draft, and processing metadata are accessible for the task execution.

Isolated State: The validator's internal reasoning, intermediate evaluation notes, and critique steps are strictly isolated in a separate workspace so they do not pollute Cortex's context window or influence subsequent generation drafts directly.

## Cost and latency budget

Extra Model Calls: The independent validator adds exactly one extra model call per processing iteration.

Worst-Case with Revision Cap: Under the maximum revision limit (MAX_REVISIONS=2), a failing draft triggers up to 2 validation cycles, resulting in a worst-case total of 3 model calls (1 initial generation + 2 revisions) plus 2 critic evaluations before escalation.

Added Latency: This introduces approximately 2 to 5 seconds of additional latency per item before a validated draft securely reaches the human PM review checkpoint.

Forward Link (M5 Bounds): This cost and latency overhead establishes the baseline spending and round-trip limit that will be formally bound and enforced under M5 Cost & Blast Radius constraints.

