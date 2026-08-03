# Production & Autonomy: Cortex PM Chief-of-Staff Agent

> Module 6 · ★ Deliverable 5, how you'd ship it and widen trust over time

## Autonomy Dial by segment

_Autonomy is a product decision per user, not one global setting. Name real segments, not invented personas._

| Segment | Desired autonomy (Trust Ladder rung) | Why |
|---|---|---|
| _…_ | _…_ | _…_ |

## Trust Ladder

- **Current rung:** _shadow · assisted · supervised · bounded-autonomous · autonomous_
- **Eval gate to reach the next rung:** _a number over a window, sourced from the actual M5 evals in `05-bounds-evals/bounds-and-evals.md`_
- **Incident record so far:** _what counts as clean for that window_

## Deployment plan

- **Runtime:** _managed agent platform · serverless · self-hosted, tied to the M2 loop type, and why_
- **Operator / on-call owner:** _named person + escalation path, not "the team"_
- **Rollback:** _revert prompt/version, disable a tool, or drop the dial a rung_
- **Monitoring:** _eval pass %, escalation rate, cost-to-serve, trust incidents_

## ROI metrics (beyond adoption & tokens)

| Axis | Metric | How you'd capture it |
|---|---|---|
| Outcome | _…_ | _…_ |
| Cost-to-serve | _…_ | _…_ |
| Trust incidents | _…_ | _…_ |

## Widen-autonomy decision rule

_The exact evidence that turns the dial up one notch, stated in advance._

## Governance & forward strategy

- **Compliance:** _data that must never enter a prompt; PII handling_
- **Safety:** _what stays above the line for everyone, no matter the segment or rung; kill switch_
- **Reliability:** _caps; escalate-on-stuck; model-down fallback_
- **Next widen:** _the next segment/capability to widen into + the eval that gates it_
