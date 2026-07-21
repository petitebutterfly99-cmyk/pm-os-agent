"""Cortex Email Triage Agent mock tools, the tools your agent is allowed to call.

These are plain Python functions over the files in `fixtures/`. They are imported
directly by `agent.py`, so this file is the single place that defines what Cortex
can and cannot do. 

Design note: there is deliberately NO send or publish tool. Cortex can read 
incoming emails, fetch thread history, and CREATE Gmail drafts for human review, 
but it can never send an email or make external commitments.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

FIXTURES = Path(__file__).parent / "fixtures"


def _load_json(name: str) -> dict:
    path = FIXTURES / name
    if not path.exists():
        return {}
    return json.loads(path.read_text())


def _extract_body(data: dict) -> str:
    if "fixtures" in data and len(data["fixtures"]) > 0:
        return data["fixtures"][0]["body"]
    if "body" in data:
        return data["body"]
    return json.dumps(data)


def get_task(which: str = "happy") -> dict:
    """Read the inbound email task brief to work on.

    Args:
        which: one of "happy", "missing-data", "jailbreak".
    Returns the raw task text plus its source label.
    """
    path = FIXTURES / f"triage-task-{which}.json"
    if not path.exists():
        return {"error": f"no task fixture named '{which}' (expected {path.name})",
                "available": ["happy", "missing-data", "jailbreak"]}

    data = json.loads(path.read_text())
    return {"which": which, "body": _extract_body(data)}


def get_unread_emails(which: str = "happy") -> dict:
    """Fetch incoming unread emails matching the active test scenario."""
    # Look for a specific scenario fixture file first (e.g., inbound-emails-missing-data.json)
    scenario_file = f"inbound-emails-{which}.json"
    emails = _load_json(scenario_file)
    
    if emails:
        return emails
        
    # Fallback to reading the active task JSON directly if a scenario email file doesn't exist
    task_path = FIXTURES / f"triage-task-{which}.json"
    if task_path.exists():
        task_data = json.loads(task_path.read_text())
        body_text = _extract_body(task_data)
        return {
            "unread_count": 1,
            "emails": [{
                "message_id": f"msg_{which}_001",
                "sender": "user@example.com",
                "subject": f"Triage Task - {which.title()}",
                "body": body_text
            }]
        }
        
    # Final default fallback
    return {
        "unread_count": 1, 
        "emails": [{
            "message_id": "msg_001", 
            "sender": "customer@example.com", 
            "subject": "Support Request", 
            "body": "Standard issue report."
        }]
    }


def get_thread_history(thread_id: str) -> dict:
    """Read prior messages from the same Gmail thread context."""
    thread_id = str(thread_id).strip()
    threads = _load_json("thread-history.json")
    history = threads.get(thread_id, [])
    return {"thread_id": thread_id, "history": history, "note": "prior thread messages for context."}


def create_gmail_draft(thread_id: str, draft_body: str, classification: str) -> dict:
    """Create a reply draft in the correct Gmail thread. 
    
    CRITICAL: This creates a saved draft ONLY. It never sends emails.
    """
    return {
        "status": "draft_created_for_review",
        "thread_id": str(thread_id).strip(),
        "classification": classification,
        "draft_body": draft_body,
        "note": "Draft saved in Gmail successfully. Awaiting human PM review and approval before any send action."
    }


def mark_email_processed(message_id: str) -> dict:
    """Apply internal processed marker/label to prevent duplicate work."""
    return {
        "status": "marked_processed",
        "message_id": str(message_id).strip(),
        "note": "Internal label applied to prevent duplicate processing loops."
    }


# Registry the agent loop reads. Add a tool here and the agent can call it.
# Note what is ABSENT: there is no send_email tool, no auto-reply, no publish tool.
TOOLS = {
    "get_task": get_task,
    "get_unread_emails": get_unread_emails,
    "get_thread_history": get_thread_history,
    "create_gmail_draft": create_gmail_draft,
    "mark_email_processed": mark_email_processed,
}