# Agent Line Map: Cortex Email Triage Agent

## 1. Decision, scored

| # | Decision / Action | Reversibility | Blast Radius | Measurability | Line | HITL / Verdict |
|---| :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | Fetch unread inbound emails and fixtures | High | Low | High | Below | · |
| 2 | Read prior thread history (`get_thread_history`) | High | Low | Med | Below | · |
| 3 | Classify inbound email (issue, enhancement, etc.) | High | Low | High | Below | · |
| 4 | Draft the email reply response | High | Low | High | Below | Spot-check |
| 5 | Decide the commitment content of the draft (dates, discounts/refunds, guarantees) | Low | Med | Med | Above | Required |
| 6 | Pass draft through the independent Critic | High | Low | High | Below | · |
| 7 | Determine whether to escalate or request human review | Med | Med | Med | HITL | Required |
| 8 | Create final Gmail draft for PM review | High | Med | High | Below | HITL (Never sends) |
| 9 | Send an outbound email reply automatically | Low | High | Low | Above | Required (Blocked) |

---

## 2. One-Sentence Justifications

1. **Fetch unread inbound emails and fixtures:** Pull project state / activity sits **below** the line because it's high to reverse (read-only), has a low blast radius, and is high to verify, so the deciding factor is **reversibility and read-only safety**.
2. **Read prior thread history:** Deciding relevant context sits **below** the line because it's cheap to correct and low-risk, has a low blast radius, and is medium to verify, so the deciding factor is **low blast radius**.
3. **Classify inbound email:** Classifying intent sits **below** the line because misclassification is easily corrected before action, has a low blast radius, and is high to verify against routing rules, so the deciding factor is **reversibility**.
4. **Draft the email reply response:** Drafting the status update sits **below** the line because it's easy to reverse, has a low blast radius (nothing's posted), and is easy to verify on read, so the deciding factor is **reversibility (nothing leaves unapproved)**.
5. **Decide the commitment content of the draft:** Whether the draft implies a release date, discount/refund, or guarantee sits **above** the line because once a customer reads a commitment it's hard to walk back (low reversibility) and it carries real financial/legal weight (medium blast radius), so a human owns this call, not the drafting model. This is the axis the PM agent's map scores separately (its row 4, "tone/commitment level") and is enforced two ways here: the critic's Commitment Boundary Check, and a code-level reject in `create_gmail_draft` (dates, %, guarantee/promise/commit/confirm language) that mirrors the PM agent's `MAX_QUEUE_ITEMS` cap in `tools.py`.
6. **Pass draft through the independent Critic:** Independent validation sits **below** the line because it is fully internal to the agent loop, completely reversible, and easily audited via run logs, so the deciding factor is **read-only internal automation**.
7. **Determine whether to escalate or request human review:** Deciding to escalate sits **above/HITL** the line because all three axes are middling (medium reversibility, blast radius, and measurability), so a human must confirm the boundary call.
8. **Create final Gmail draft for PM review:** Saving a draft sits **below** the line because creation is non-destructive, has a medium blast radius (held in draft state), and requires a mandatory human review checkpoint before any external action.
9. **Send an outbound email reply automatically:** Posting an unapproved update sits **above** the line because it's near-impossible to reverse once delivered and has a high blast radius, so the deciding factor is **reversibility and blast radius (always human-owned)**.