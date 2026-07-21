"""Cortex Email Triage Agent, a minimal, explicit agent loop.
Updated to process inbound Gmail messages, classify them, draft responses,
and pass them through an independent critic before hitting the human review checkpoint.
"""

from __future__ import annotations

import json
import os
import sys

from openai import OpenAI

import triagetools
from critic import review
from triageprompt import CORTEX_SYSTEM

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

# --- Bounds ------------------------------------------------------------------
MODEL = os.environ.get("CORTEX_MODEL", "gpt-4o-mini")
MAX_ITERATIONS = int(os.environ.get("CORTEX_MAX_ITERATIONS", "8"))
MAX_REVISIONS = int(os.environ.get("CORTEX_MAX_REVISIONS", "2"))
COST_CAP_USD = float(os.environ.get("CORTEX_COST_CAP_USD", "0.50"))
PRICE_IN = float(os.environ.get("CORTEX_PRICE_IN_PER_M", "0.15"))
PRICE_OUT = float(os.environ.get("CORTEX_PRICE_OUT_PER_M", "0.60"))

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
        "name": "create_gmail_draft",
        "description": "Create a reply draft in the correct Gmail thread. Never sends emails.",
        "parameters": {"type": "object", "properties": {
            "thread_id": {"type": "string"},
            "draft_body": {"type": "string"},
            "classification": {"type": "string"}}, "required": ["thread_id", "draft_body", "classification"]}}},
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


def run(which: str = "happy") -> None:
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

    for step in range(1, MAX_ITERATIONS + 1):
        if bounds.over_cap():
            banner(f"BOUND TRIPPED, cost cap ${COST_CAP_USD} hit at "
                   f"${bounds.cost:.4f}. Halting and escalating to a human.")
            return

        resp = client.chat.completions.create(
            model=MODEL, messages=messages, tools=TOOL_SCHEMAS)
        bounds.add(resp.usage)
        msg = resp.choices[0].message

        if msg.tool_calls:
            messages.append(msg)
            for call in msg.tool_calls:
                fn = call.function.name
                args = json.loads(call.function.arguments or "{}")
                if fn == "get_unread_emails":
                    args["which"] = which
                result = triagetools.TOOLS[fn](**args)
                source_log.append(f"{fn}({args}) -> {json.dumps(result)}")
                print(f"\n[step {step}] TOOL {fn}({args})")
                print(f"          -> {json.dumps(result)[:300]}")
                messages.append({"role": "tool", "tool_call_id": call.id,
                                 "content": json.dumps(result)})
            continue

        # No tool calls => Cortex produced a proposed output. Validate it.
        proposed = msg.content or ""
        print(f"\n[step {step}] PROPOSED OUTPUT:\n{proposed}")
        
        # Explicit debug print for tracking initial/revised drafts
        print(f"\n--- [DEBUG] CORTEX INITIAL DRAFT ---\n{proposed}\n-----------------------------------\n")

        banner("CRITIC, independent validation")
        verdict = review(client, MODEL, proposed, "\n".join(source_log))
        bounds.cost += (verdict["_usage"]["prompt"] * PRICE_IN
                        + verdict["_usage"]["completion"] * PRICE_OUT) / 1_000_000
        
        # Explicit debug print for critic verdict and rejection reasons
        print(f"\n--- [DEBUG] CRITIC VERDICT ---\nVerdict: {verdict.get('verdict')}\nReasons: {verdict.get('reasons')}\n-----------------------------\n")
        
        print(json.dumps({k: v for k, v in verdict.items() if k != "_usage"}, indent=2))

        if verdict["verdict"] == "pass":
            banner(f"HITL CHECKPOINT, email classified and draft saved for PM review. "
                   f"Never auto-sent. Run cost ≈ ${bounds.cost:.4f}")
            return

        if revisions >= MAX_REVISIONS:
            banner(f"REVISION CAP hit ({MAX_REVISIONS}). Escalating to a human "
                   f"PM instead of looping. Run cost ≈ ${bounds.cost:.4f}")
            return

        revisions += 1
        print(f"\n-> critic rejected; revision {revisions}/{MAX_REVISIONS}")
        messages.append(msg)
        messages.append({"role": "user", "content":
                         "A validator rejected that draft for these reasons: "
                         f"{verdict['reasons']}. Fix it or escalate."})

    banner(f"MAX ITERATIONS ({MAX_ITERATIONS}) reached without finishing. "
           f"Escalating. Run cost ≈ ${bounds.cost:.4f}")


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else "happy")