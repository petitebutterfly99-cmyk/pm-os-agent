# Agent Line Map: Cortex Email Triage Agent

## 1. Decision, scored

| # | Decision / Action | Reversibility | Blast Radius | Measurability | Line | HITL / Verdict |
|---| :--- | :---: | :---: | :---: | :---: | :--- |
| 1 | Fetch unread inbound emails and fixtures | High | Low | High | Below | · |
| 2 | Read prior thread history (`get_thread_history`) | High | Low | Med | Below | · |
| 3 | Classify inbound email (issue, enhancement, etc.) | High | Low | High | Below | · |
| 4 | Draft the email reply response | High | Low | High | Below | Spot-check |
| 5 | Pass draft through the independent Critic | High | Low | High | Below | · |
| 6 | Determine whether to escalate or request human review | Med | Med | Med | HITL | Required |
| 7 | Create final Gmail draft for PM review | High | Med | High | Below | HITL (Never sends) |
| 8 | Send an outbound email reply automatically | Low | High | Low | Above | Required (Blocked) |

---

## 2. One-Sentence Justifications

1. **Fetch unread inbound emails and fixtures:** Pull project state / activity sits **below** the line because it's high to reverse (read-only), has a low blast radius, and is high to verify, so the deciding factor is **reversibility and read-only safety**.
2. **Read prior thread history:** Deciding relevant context sits **below** the line because it's cheap to correct and low-risk, has a low blast radius, and is medium to verify, so the deciding factor is **low blast radius**.
3. **Classify inbound email:** Classifying intent sits **below** the line because misclassification is easily corrected before action, has a low blast radius, and is high to verify against routing rules, so the deciding factor is **reversibility**.
4. **Draft the email reply response:** Drafting the status update sits **below** the line because it's easy to reverse, has a low blast radius (nothing's posted), and is easy to verify on read, so the deciding factor is **reversibility (nothing leaves unapproved)**.
5. **Pass draft through the independent Critic:** Independent validation sits **below** the line because it is fully internal to the agent loop, completely reversible, and easily audited via run logs, so the deciding factor is **read-only internal automation**.
6. **Determine whether to escalate or request human review:** Deciding to escalate sits **above/HITL** the line because all three axes are middling (medium reversibility, blast radius, and measurability), so a human must confirm the boundary call.
7. **Create final Gmail draft for PM review:** Saving a draft sits **below** the line because creation is non-destructive, has a medium blast radius (held in draft state), and requires a mandatory human review checkpoint before any external action.
8. **Send an outbound email reply automatically:** Posting an unapproved update sits **above** the line because it's near-impossible to reverse once delivered and has a high blast radius, so the deciding factor is **reversibility and blast radius (always human-owned)**.