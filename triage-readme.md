# Cortex Email Triage Agent

A supervised chief-of-staff agent that turns messy inbound email into a context-rich, pre-drafted decision ready for human approval — never a decision made on its own.

---

## Overview

The **Cortex Email Triage Agent** automates the heavy lifting of managing an inbox. It ingests inbound emails, pulls thread history and institutional policy, classifies intent into one of six categories, and drafts a structured reply, or refuses to draft at all when policy requires escalation, all under infrastructure bounds enforced in code and a mandatory human-in-the-loop (HITL) checkpoint at the end of every run. It is deliberately **not** autonomous: there is no send tool anywhere in the codebase, so nothing it produces reaches a customer without a human reading it first.

---

## Would You Ship This? (For the skeptical VP of Operations, 90 seconds)

**1. Would you ship it at the autonomy it claims?**
Yes. The claim is narrow on purpose, read, classify, draft-or-refuse, then stop, every category, every run, no exceptions. There's no send tool to misuse, so the worst case is a human reviewing an awkward draft, not an unauthorized action.

**2. Is the dial set where the blast radius justifies, or too high for the trust earned?**
The dial itself is conservative, not too high, everything sits at Supervised, two of three user segments permanently capped there. The real gap is a question the dial doesn't cover at all:
> "Nothing currently redacts PII if it shows up in an inbound email body, a real gap, not a solved problem." — `06-autonomy/triage-production-and-autonomy.md`

**3. Where does the operator handoff break if Cortex fails at 2am?**
Before the named owner even gets involved. The monitoring signals are real (`logs/hitl-audit-log.jsonl` records eval pass rate, escalation rate, cost-to-serve, guard-firing rate) but they're passive, nothing pages anyone. A stuck run sits quietly escalated in a log nobody's watching, with a single named owner (the AI product manager) and no backup even if someone were paged. The gap is alerting, not headcount.

**4. Which ROI claim would you push back on first?**
"% of emails triaged without a human reclassifying Cortex's category." It's measured against seven mock fixtures, not real volume, and a fatigued reviewer skipping a reclassification would make this number look better than it is, not worse. What would change my mind: a blinded audit, an independent reviewer re-classifying a random sample of real production output at real volume, not fixtures run twenty times.

**5. Single addition that moves this from "good cohort submission" to "production-fundable"?**
Run the eval gate that's already fully specified, for real. Every bound, guard, and log needed to clear it exists today; what's missing is the actual 4 weeks of real shadow-graded traffic proving it clears. Not more engineering, proof.

---

## Key Features

* **Six-way inbound classification:** issue, enhancement request, commitment requested, escalation, unclear, unrelated, each with different handling rules, not a flat triage bucket.
* **Context & policy retrieval:** pulls prior thread history and the support triage policy to ground every classification and draft.
* **Independent critic validation:** every draft passes through a separate model call with its own rubric before a human ever sees it, no default rubric, no silent fallback (`critic_system` is a required parameter, not an optional one).
* **Infrastructure-enforced bounds, not prompt requests:** iteration cap, per-run and rolling-daily cost caps, per-call and whole-run timeouts, a read-tool budget, a file-based kill switch, and two content guards (no commitment-bearing drafts, no drafts at all for unclear emails) that reject in code regardless of what the model intends.
* **No send capability, structurally:** not a permission that's revoked, a capability that was never built. There is nothing for a jailbreak or a bug to escalate into.

---

## Repository Structure

* `00-build/` — Agent runtime: `triageagent.py` (loop), `triagetools.py` (tools + code-level guards), `triageprompt.py` (system + critic prompts), `critic.py` (shared independent validator), `fixtures/` (test scenarios), `hf-space/` (deployable Gradio demo).
* `01-agent-line/triage-agent-line-map.md` — Decisions scored by reversibility, blast radius, and measurability; what Cortex owns vs. what stays human-owned.
* `04-memory-context/triage-memory-and-context.md` — Working, episodic, and semantic memory configuration.
* `05-bounds-evals/triage-bounds-and-evals.md` — The bounds table, the Trust Ladder, and the autonomy dial by inbound category.
* `06-autonomy/triage-production-and-autonomy.md` — Autonomy dial by user segment, eval gate (numbers, not feelings), deployment plan, ROI metrics, governance.
* `06-autonomy/triage-prototype.md` — What it does, how it was built, required run screenshots.
* `06-autonomy/triage-build-insights.md` — Friction, learning, the aha moment, what changed as a result.

---

## The Agent Line: What Cortex Owns vs. Human Control

| Decision / Action | Line | Enforced Guardrail |
| :--- | :--- | :--- |
| Fetch inbound email & thread history | Below | Read-only; `thread_id` validated against the id this run actually fetched |
| Classify intent (6 categories) & draft a reply | Below | Model + independent critic, critic rubric is a required parameter |
| Draft an `unclear`-classified reply | **Blocked in code** | `escalation_required_no_draft`, no draft permitted, ESCALATE only |
| Draft a commitment (date, discount, refund, guarantee) | **Blocked in code** | `commitment_bound_violation`, rejected regardless of what the model intends |
| Escalate to a human / HITL checkpoint | HITL | Every run ends here or at a saved draft, no exceptions |
| Send an outbound reply | **Above, structurally absent** | No send tool exists anywhere in the codebase, not a permission, a missing capability |

---

## Quickstart & Execution

```bash
cd 00-build
pip install -r requirements.txt
cp .env.example .env        # add your OPENAI_API_KEY

python3 triageagent.py happy                       # routine bug report
python3 triageagent.py missing-data                 # vague report, no-draft escalation
python3 triageagent.py jailbreak                    # commitment-trap injection, refused
python3 triageagent.py jailbreak-security-threat    # legal-threat / extortion sub-fixture
```

Trip a bound on purpose:

```bash
CORTEX_MAX_ITERATIONS=2 python3 triageagent.py happy
touch .cortex_halt && python3 triageagent.py happy; rm .cortex_halt
```
