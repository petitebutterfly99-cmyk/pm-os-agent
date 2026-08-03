# Production & Autonomy: Cortex Email Triage Agent

> Module 6 · ★ Deliverable 5, how you'd ship it and widen trust over time

## Autonomy Dial by segment

_Autonomy is a product decision per user, not one global setting. Named for the email triage variant, complements the classification-based segmentation in `../05-bounds-evals/triage-bounds-and-evals.md` (Section 3), which segments by inbound category rather than by human operator._

| Segment | Desired autonomy (Trust Ladder rung) | Why |
|---|---|---|
| Solo product manager triaging their own inbox | Supervised | Every category ends at an email draft or an escalation banner, nothing auto-sends for any category yet |
| Legal / Trust & Safety | Supervised, permanently capped | Isolates the `escalation` and `commitment requested` categories, which are structurally blocked from ever graduating past supervised, no eval gate raises this ceiling |
| Account managers for enterprise customers | Supervised, permanently capped | Isolates `commitment requested` emails specifically, since a bad commitment or a mishandled refusal both risk the customer relationship and open orders |

## Trust Ladder

- **Current rung:** Supervised. The loop runs fetch → classify → draft-or-refuse → critic fully unattended, but the terminal action is structurally incapable of executing without a human, for every classification, no exceptions.
- **Eval gate to reach the next rung** (applies only to the `unrelated` and `issue`/`enhancement request` classifications, per the Autonomy Dial above, everything else stays permanently capped at supervised):

  | # | Metric | Threshold | Window |
  |---|---|---|---|
  | 1 | Fixture-replay first-pass rate | 100% (20/20 runs, zero revisions) | One-time regression check, run before the production window opens |
  | 2 | Guard firing rate (`guard_rejections` in `logs/hitl-audit-log.jsonl`) | Tracked, not required to be zero, a guard firing means it caught something, that's the system working | 4 consecutive weeks of shadow-graded production traffic |
  | 3 | Human-audit finding rate | 0 missed violations, at 100% coverage of accepted drafts | Same 4-week window |

- **Incident record:** an incident is any accepted draft (commitment-bearing or `unclear`-classified) that a human auditor finds *should* have been rejected by `commitment_bound_violation` or `escalation_required_no_draft` but wasn't, a guard bypass, not a guard firing. Clean = zero such findings across 100% of the window's accepted drafts. Sender-integrity is not yet a code-level guard (only a critic judgment call, see check 6 in `triageprompt.CRITIC_SYSTEM`), so a sender-impersonation miss would also only surface via this same human audit, not via `guard_rejections`.

## Deployment plan

- **Runtime:** Serverless, triggered by a Gmail push notification / new-message webhook, one invocation per inbound email. Follows directly from the M2 loop shape: `triageagent.run(which)` is a single bounded, stateless run per email (fetch → classify → draft-or-refuse → critic → stop), not a persistent polling process, so paying for an always-on service between emails wouldn't match how the loop actually behaves.
- **Operator / on-call owner:** The AI product manager. No secondary on-call/escalation path is defined yet, single point of failure until a backup owner is named, noting that honestly rather than inventing a team that doesn't exist.
- **Rollback:** Three real mechanisms, not hypothetical: (1) revert prompt/version, `triageprompt.py` is versioned, rollback is a `git revert`; (2) disable a tool, remove `create_gmail_draft`'s schema from `TOOL_SCHEMAS`, forcing every run to end in escalation instead of a draft; (3) drop the dial a rung, the `.cortex_halt` kill switch already halts everything, nothing further to build.
- **Monitoring:** Already implemented, not aspirational, pulled from `logs/hitl-audit-log.jsonl`: eval pass % (`outcome == "hitl_checkpoint_pass"` rate), escalation rate (`revision_cap_escalation` / `max_iterations_escalation` / `classification == "escalation"` rate), cost-to-serve (`cost_usd`, rolled up via `logs/cost-ledger.json`), trust incidents (`guard_rejections` firing rate, cross-checked against human-audit bypass findings).

## ROI metrics (beyond adoption & tokens)

| Axis | Metric | How you'd capture it |
|---|---|---|
| Outcome | % of inbound emails triaged without a human reclassifying Cortex's category | Audit log's `classification` field vs. a periodic human relabel spot-check |
| Cost-to-serve | $ per email processed | `cost_usd` ÷ email count, from the audit log |
| Trust incidents | Guard bypass rate (not firing rate, see the Trust Ladder incident record) | The 100%-coverage human audit defined in the incident record |

## Widen-autonomy decision rule

*The dial widens from supervised to bounded-autonomous, for the `unrelated` and `issue`/`enhancement request` classifications only, the moment all three rows of the Trust Ladder eval gate clear in full, never partially, never for the other three classifications, and never on a deadline alone.*

## Governance & forward strategy

- **Compliance:** Nothing currently redacts PII if it shows up in an inbound email body, a real gap, not a solved problem.
- **Safety:** Commitment content, the `escalation`/`commitment requested` categories, and sending itself all stay above the line for every segment regardless of rung, already established in the agent-line map, and structurally enforced (no send tool exists in the codebase). Kill switch: `.cortex_halt` locally, the Space's Pause button in production.
- **Reliability:** Caps are all real (iteration, cost, timeout, read-budget), but there's no fallback if the OpenAI API itself is down or erroring repeatedly, today that just burns iterations until `MAX_ITERATIONS` or `RUN_DEADLINE_S` trips and escalates. Slower than ideal, not unsafe.
- **Next widen:** `unrelated` first, lowest blast radius, easiest to eval (a lighter gate: zero real-issue-mislabeled-as-unrelated over N samples), before ever touching `issue`/`enhancement request`.
