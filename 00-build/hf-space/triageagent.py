"""Cortex Email Triage Agent, a minimal, explicit agent loop.
Updated to process inbound Gmail messages, classify them, draft responses,
and pass them through an independent critic before hitting the human review checkpoint.
"""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from openai import OpenAI

import triagetools
from critic import review
from triageprompt import CORTEX_SYSTEM, CRITIC_SYSTEM as TRIAGE_CRITIC_SYSTEM

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# --- Bounds ------------------------------------------------------------------
MODEL = os.environ.get("CORTEX_MODEL", "gpt-4o-mini")
# Critic gets a stronger model than the drafter on purpose: the nuanced
# classification-alignment judgment calls (bug report vs. commitment request,
# refusal language vs. an actual commitment) showed real inconsistency on
# gpt-4o-mini, a cheap drafter is fine since the critic is the safety net.
CRITIC_MODEL = os.environ.get("CORTEX_CRITIC_MODEL", "gpt-4o")
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "12"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.05"))
DAILY_COST_CAP_USD = float(os.environ.get("CORTEX_DAILY_COST_CAP_USD", "1.00"))
MAX_READ_CALLS = int(os.environ.get("CORTEX_MAX_READ_CALLS", "6"))
CALL_TIMEOUT_S = float(os.environ.get("CORTEX_CALL_TIMEOUT_S", "30"))
RUN_DEADLINE_S = float(os.environ.get("CORTEX_RUN_DEADLINE_S", "120"))
PRICE_IN = float(os.environ.get("CORTEX_PRICE_IN_PER_M", "0.15"))
PRICE_OUT = float(os.environ.get("CORTEX_PRICE_OUT_PER_M", "0.60"))
# Separate pricing for CRITIC_MODEL, it's a different, pricier model than MODEL,
# billing its tokens at the drafter's rate would understate the cost cap.
CRITIC_PRICE_IN = float(os.environ.get("CORTEX_CRITIC_PRICE_IN_PER_M", "2.50"))
CRITIC_PRICE_OUT = float(os.environ.get("CORTEX_CRITIC_PRICE_OUT_PER_M", "10.00"))

READ_ONLY_TOOLS = {"get_unread_emails", "get_thread_history", "get_policies"}

# Runtime state, not course fixtures, gitignored (see repo .gitignore).
LOGS_DIR = Path(__file__).parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)
AUDIT_LOG = LOGS_DIR / "hitl-audit-log.jsonl"
COST_LEDGER = LOGS_DIR / "cost-ledger.json"
HALT_FILE = Path(__file__).parent / ".cortex_halt"

# Gmail Connector Tool Schemas (Read & Draft permissions only, no send tool)
TOOL_SCHEMAS = [
    {"type": "function", "function": {
        "name": "get_unread_emails",
        "description": "Fetch incoming unread emails from Gmail for triage processing.",
        "parameters": {"type": "object", "properties": {}, "required": []}}},
    {"type": "function", "function": {
        "name": "get_thread_history",
        "description": "Read prior messages from the same Gmail thread context.",
        "parameters": {"type": "object", "properties": {
            "thread_id": {"type": "string"}}, "required": ["thread_id"]}}},
    {"type": "function", "function": {
        "name": "get_policies",
        "description": "Return the support triage policy (commitment authority, escalation triggers, tone) Cortex must ground decisions in.",
        "parameters": {"type": "object", "properties": {
            "query": {"type": "string"}}, "required": []}}},
    {"type": "function", "function": {
        "name": "create_gmail_draft",
        "description": "Create a reply draft in the correct Gmail thread. Never sends emails.",
        "parameters": {"type": "object", "properties": {
            "thread_id": {"type": "string"},
            "draft_body": {"type": "string"},
            "classification": {"type": "string", "enum": [
                "issue", "enhancement request", "commitment requested",
                "escalation", "unclear", "unrelated"]}},
            "required": ["thread_id", "draft_body", "classification"]}}},
    {"type": "function", "function": {
        "name": "mark_email_processed",
        "description": "Apply internal processed marker/label to prevent duplicate work.",
        "parameters": {"type": "object", "properties": {
            "message_id": {"type": "string"}}, "required": ["message_id"]}}},
]


class Bounds:
    """Tracks spend and trips the cost cap outside the model."""

    def __init__(self):
        self.cost = 0.0

    def add(self, usage) -> None:
        self.cost += (usage.prompt_tokens * PRICE_IN
                      + usage.completion_tokens * PRICE_OUT) / 1_000_000

    def over_cap(self) -> bool:
        return self.cost >= COST_CAP_USD


def banner(text: str) -> None:
    print(f"\n{'=' * 64}\n{text}\n{'=' * 64}")


def _halted() -> bool:
    """Kill switch: an operator drops this file to halt runs without killing
    the process. Checked before a run starts and once per loop iteration."""
    return HALT_FILE.exists()


def _load_cost_ledger() -> dict:
    if COST_LEDGER.exists():
        return json.loads(COST_LEDGER.read_text())
    return {}


def _today_cost() -> float:
    return _load_cost_ledger().get(date.today().isoformat(), 0.0)


def _record_daily_cost(amount: float) -> None:
    ledger = _load_cost_ledger()
    today = date.today().isoformat()
    ledger[today] = ledger.get(today, 0.0) + amount
    COST_LEDGER.write_text(json.dumps(ledger, indent=2))


def _audit(event: dict) -> None:
    """Append-only HITL audit trail, one line per run outcome, so there's a
    record of whether a human checkpoint was actually reached, independent
    of whatever happens to the draft after this process exits."""
    entry = {"timestamp": datetime.now(timezone.utc).isoformat(), **event}
    with AUDIT_LOG.open("a") as f:
        f.write(json.dumps(entry) + "\n")


def run(which: str = "happy") -> None:
    if _halted():
        banner(f"HALTED, operator stop-flag present ({HALT_FILE}). Not starting a new run.")
        _audit({"fixture": which, "outcome": "halted_before_start"})
        return

    today_spend = _today_cost()
    if today_spend >= DAILY_COST_CAP_USD:
        banner(f"DAILY COST CAP (${DAILY_COST_CAP_USD}) already reached today "
               f"(${today_spend:.4f} spent). Refusing to start a new run.")
        _audit({"fixture": which, "outcome": "daily_cost_cap_refused",
                "today_spend_usd": round(today_spend, 6)})
        return

    client = OpenAI()
    bounds = Bounds()
    task = triagetools.get_task(which)
    if "error" in task:
        print(task)
        return

    banner(f"CORTEX EMAIL TRIAGE RUN, fixture: task-{which}")
    print(task["body"])

    messages = [
        {"role": "system", "content": CORTEX_SYSTEM},
        {"role": "user", "content": f"Incoming Email Task Brief:\n\n{task['body']}"},
    ]
    source_log: list[str] = [task["body"]]
    revisions = 0
    called: set[str] = set()
    read_calls = 0
    known_ids: set[str] = set()
    classification_seen = None
    draft_saved = False
    guard_rejections: list[str] = []
    guard_only_streak = 0
    run_deadline = time.monotonic() + RUN_DEADLINE_S
    step = 0

    def finish(outcome: str) -> None:
        _record_daily_cost(bounds.cost)
        _audit({
            "fixture": which,
            "message_id": next(iter(known_ids), None),
            "classification": classification_seen,
            "outcome": outcome,
            "step": step,
            "revisions": revisions,
            "cost_usd": round(bounds.cost, 6),
            "guard_rejections": guard_rejections,
            "draft_saved": draft_saved,
        })

    for step in range(1, MAX_ITERATIONS + 1):
        if _halted():
            banner("HALTED mid-run, operator stop-flag present. Escalating to a human.")
            finish("halted")
            return

        if time.monotonic() > run_deadline:
            banner(f"RUN DEADLINE ({RUN_DEADLINE_S}s) exceeded. Halting and escalating "
                   f"to a human. Run cost ≈ ${bounds.cost:.4f}")
            finish("run_deadline_exceeded")
            return

        if bounds.over_cap():
            banner(f"BOUND TRIPPED, cost cap ${COST_CAP_USD} hit at "
                   f"${bounds.cost:.4f}. Halting and escalating to a human.")
            finish("cost_cap_tripped")
            return

        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS, timeout=CALL_TIMEOUT_S)
        bounds.add(resp.usage)
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            step_had_progress = False
            for call in msg.tool_calls:
                fn = call.function.name
                args = json.loads(call.function.arguments or "{}")
                if fn == "get_unread_emails":
                    args["which"] = which
                call_key = f"{fn}:{json.dumps(args, sort_keys=True)}"

                if call_key in called:
                    # NO REPEAT CALLS is only a prompt rule; enforce it here too so a
                    # confused model can't loop forever re-calling the same tool.
                    result = {"error": "duplicate_call",
                              "message": f"{fn} was already called with these exact "
                                         "arguments; its result is final and already in "
                                         "the transcript above. Do not call it again, "
                                         "draft the response or ESCALATE with what you have."}
                elif fn in READ_ONLY_TOOLS and read_calls >= MAX_READ_CALLS:
                    result = {"error": "read_call_budget_exhausted",
                              "message": f"Read-only tool budget ({MAX_READ_CALLS} calls) is "
                                         "used up for this run. Proceed to drafting or "
                                         "ESCALATE with what you already have."}
                elif (fn == "get_thread_history" and known_ids
                      and args.get("thread_id") not in known_ids):
                    result = {"error": "unknown_thread_id",
                              "message": f"thread_id {args.get('thread_id')!r} does not "
                                         "match the message_id returned by get_unread_emails "
                                         "this run; refusing to read an unrelated thread."}
                else:
                    called.add(call_key)
                    step_had_progress = True
                    if fn in READ_ONLY_TOOLS:
                        read_calls += 1
                    result = triagetools.TOOLS[fn](**args)
                    if fn == "get_unread_emails" and "emails" in result:
                        known_ids.update(e["message_id"] for e in result["emails"])
                    if fn == "create_gmail_draft":
                        classification_seen = args.get("classification")
                        if result.get("status") == "draft_created_for_review":
                            draft_saved = True

                if isinstance(result, dict) and "error" in result:
                    # Every code-level guard (commitment bound, no-draft-for-unclear,
                    # duplicate-call, read-budget, unknown-thread-id) returns an "error"
                    # key, this is what the eval gate's guard-violation count is measured
                    # against, not just what's visible in the printed trace.
                    guard_rejections.append(result["error"])

                source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
                print(f"\n[step {step}] TOOL {fn}({args})")
                print(f"          -> {json.dumps(result)[:300]}")
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(result)})

            if step_had_progress:
                guard_only_streak = 0
            else:
                # Every call this step was a guard rejection (duplicate_call,
                # read_call_budget_exhausted, or unknown_thread_id) on data already
                # in the transcript, zero new information reached the model. Left
                # unchecked this burns iterations 1-for-1 until MAX_ITERATIONS,
                # instead of escalating as soon as it's clear nothing is progressing.
                guard_only_streak += 1
                if guard_only_streak >= 2:
                    banner(f"STALLED, {guard_only_streak} consecutive steps produced only "
                           f"rejected/duplicate tool calls with no new information. "
                           f"Escalating instead of burning remaining iterations. "
                           f"Run cost ≈ ${bounds.cost:.4f}")
                    finish("stalled_no_progress")
                    return
            continue

        # No tool calls => Cortex produced a proposed output. Validate it.
        proposed = msg.content or ""
        print(f"\n[step {step}] PROPOSED OUTPUT:\n{proposed}")

        banner("CRITIC, independent validation")
        verdict = review(client, CRITIC_MODEL, proposed, "\n".join(source_log),
                         critic_system=TRIAGE_CRITIC_SYSTEM)
        bounds.cost += (verdict["_usage"]["prompt"] * CRITIC_PRICE_IN
                        + verdict["_usage"]["completion"] * CRITIC_PRICE_OUT) / 1_000_000
        print(json.dumps({k: v for k, v in verdict.items() if k != "_usage"}, indent=2))

        if verdict["verdict"] == "pass":
            if draft_saved:
                banner(f"HITL CHECKPOINT, email classified and draft saved for PM review. "
                       f"Never auto-sent. Run cost ≈ ${bounds.cost:.4f}")
                finish("hitl_checkpoint_pass")
            elif proposed.strip().upper().startswith("ESCALATE"):
                banner(f"HITL CHECKPOINT, email classified and escalated to a human. "
                       f"No draft was created or saved. Run cost ≈ ${bounds.cost:.4f}")
                finish("hitl_checkpoint_escalate_pass")
            else:
                # DONE with no draft, e.g. "unrelated": correctly nothing to reply to,
                # not an escalation, don't call this "escalated to a human".
                banner(f"HITL CHECKPOINT, email classified, no reply needed, no draft "
                       f"created. Run cost ≈ ${bounds.cost:.4f}")
                finish("hitl_checkpoint_no_action_pass")
            return

        if revisions >= MAX_REVISIONS:
            banner(f"REVISION CAP hit ({MAX_REVISIONS}). Escalating to a human "
                   f"PM instead of looping. Run cost ≈ ${bounds.cost:.4f}")
            finish("revision_cap_escalation")
            return

        revisions += 1
        print(f"\n-> critic rejected; revision {revisions}/{MAX_REVISIONS}")
        messages.append(msg)
        final_notice = (
            " This was your final allowed revision: do not call any more tools, "
            "your next message must be a final DONE or ESCALATE."
            if revisions >= MAX_REVISIONS else ""
        )
        messages.append({"role": "user", "content":
                         "A validator rejected that draft for these reasons: "
                         f"{verdict['reasons']}. Fix it or escalate.{final_notice}"})

    banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) reached without finishing. "
           f"Escalating. Run cost ≈ ${bounds.cost:.4f}")
    finish("max_iterations_escalation")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "happy")