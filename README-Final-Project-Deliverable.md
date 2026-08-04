# Cortex, an Email Triage Agent for PMs

> A chief-of-staff agent that automates email triage, context-gathering, and drafting for fast, human-approved responses.

_Cari McClurkin · Advanced AI Agent Cohort · August 5, 2026_

Repo: https://github.com/petitebutterfly99-cmyk/pm-os-agent

This repo is my final project for the Run Your AI Agent Team Certification, **Cortex**. Each module’s artifact lives in its own folder; this README is the dashboard and the pitch.

---

## Module artifacts

### M1 · The Agent Line
- **Agent-line map**: [`01-agent-line/triage-agent-line-map.md`](01-agent-line/triage-agent-line-map.md)

### M2 · Loop Engineering
- **Loop spec**: [`02-loop-design/loop-spec.md`](02-loop-design/loop-spec.md)

### M3 · Orchestration &amp; Subagents
- **Orchestration map**: [`03-orchestration/triage-orchestration-map.md`](03-orchestration/triage-orchestration-map.md)

### M4 · Context Engineering &amp; Memory
- **Memory &amp; context plan**: [`04-memory-context/triage-memory-and-context.md`](04-memory-context/triage-memory-and-context.md)

### M5 · Bounds &amp; Evals
- **Bounds &amp; evals**: [`05-bounds-evals/triage-bounds-and-evals.md`](05-bounds-evals/triage-bounds-and-evals.md)

### M6 · Autonomy &amp; Production
- **Production &amp; autonomy plan**: [`06-autonomy/triage-production-and-autonomy.md`](06-autonomy/triage-production-and-autonomy.md)
- **Prototype write-up**: [`06-autonomy/triage-prototype.md`](06-autonomy/triage-prototype.md)

---

## Ship plan

### Autonomy dial (per segment)
- Solo PM (own inbox) — Supervised. Every category ends at a draft or an escalation banner; nothing auto-sends yet.
- Legal / Trust & Safety — Supervised, permanently capped. Isolates escalation + commitment requested — structurally blocked from ever graduating.
- Enterprise account managers — Supervised, permanently capped. Isolates commitment requested — a bad commitment or mishandled refusal risks the relationship.

### Trust Ladder rung + eval gate
- Current rung: Supervised — full loop runs unattended, human required at every checkpoint, no exceptions.
- Gate to Bounded-Autonomous (only for unrelated / issue / enhancement request):
1. 100% first-pass critic rate — 20/20 fixture replays, zero revisions
2. 4 consecutive weeks shadow-graded production traffic
3. 0 missed violations at 100% human-audit coverage of accepted drafts
- Incident = bypass, not firing. A guard catching something is the system working; an incident is a violation that got through undetected.

### Deployment plan
- Runtime: Serverless, Gmail-webhook-triggered, one invocation per inbound email
- On-call: AI product manager (named) — no backup on-call yet, flagged honestly, not papered over
- Rollback: revert prompt (git revert) · disable a tool (drop create_gmail_draft's schema) · drop a rung (.cortex_halt kill switch)
- Monitoring: live today, not aspirational — eval pass %, escalation rate, $/email, guard-firing rate, all pulled from logs/hitl-audit-log.jsonl

### ROI metrics + widen-autonomy rule
- Outcome: % of emails triaged without a human reclassifying the category
- Cost-to-serve: $ per email processed
- Trust incidents: guard bypass rate (audit-verified, not just guard-firing count)
- Widen rule: dial moves supervised → bounded-autonomous, unrelated/issue/enhancement request only, only when all 3 eval-gate metrics clear in full — never partial, never on a deadline alone

### Governance &amp; strategy
- Compliance: no PII redaction yet — a real gap, named rather than hidden
- Safety: commitment content, escalation/commitment requested, and sending itself stay above the line for every segment, always; no send tool exists in the codebase
- Reliability: iteration/cost/timeout/read-budget caps are real; no fallback yet if the model API itself goes down
- Next widen: unrelated category first — lowest blast radius, lighter eval (zero real issues misclassified as unrelated)

---

## Build insights

- **Friction point.** "A fix in one variant didn't propagate to its sibling. The repeat-call loop (a tool called seven times in a row with an identical error) got fixed in the triage agent early on, then showed up again, unpatched, in the PM agent during an unrelated M4 probe. Same underlying bug, same codebase family, and nothing forced the second instance to get caught until I happened to be testing something else entirely."
- **Key learning.** "A bound written in a prompt is not a bound. Every prompt-only rule tested this session, no-repeat-calls, escalate-for-unclear, no-commitment-language, eventually broke under a hard case, and the fix was always the same shape: move it into code."
- **Aha moment.** "The line map dictates the architecture, not the audit. Because I forgot to map 'commitment level,' the code guard never got built. Scoring the full map before touching tool code is the only way to ensure your guardrails actually match the intent."

---

_Certification submission, Run Your AI Agent Team Certification._
