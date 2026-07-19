# Loop Spec: Cortex Email Triage Agent

> Module 2 · Loop Engineering, ★ Deliverable 2
>
> Your one-page blueprint for how the work you handed to the agent (M1) actually *runs*.
> An agent is just a prompt that fires itself, this spec says when it fires, what "done" means, and what it needs to do the job. Living document; refine as the course progresses.


## Trigger and loop type

Hook + cron backup

## Why this loop type

The hook with scheduled cron backup is appropriate because it balances responsiveness with reliability..  This loop is primarily event-driven. Cortex begins processing when a new email arrives in Gmail. A scheduled sweep runs as a backup to identify any unread emails that were missed or not processed correctly.

## Definition of done

A run is complete when Cortex has reviewed the incoming email, classified it as an issue, enhancement request, unclear, or unrelated, and created an appropriate Gmail reply draft when a response is needed.
The draft is saved for human review. Cortex never sends the email.

## Stop conditions

- **Success**: The loop ends successfully when:
The email has been read and understood.
The email has been classified.
A concise summary has been created.
A reply draft has been saved in the correct Gmail thread, when appropriate.
The message has been marked as processed to prevent duplicate work.
Any uncertainty or risk has been clearly flagged for the reviewer.
For an unrelated email, success means Cortex records it as reviewed and creates no reply draft.
- **Stuck / give up**: Cortex should consider the run stuck and stop when:
It cannot retrieve the email body or thread history after three attempts.
Gmail fails to create or save the draft after three attempts.
The same processing step fails three times with no new information.
Cortex cannot determine the sender’s request because the content is missing, corrupted, or unreadable.
Cortex detects that it is repeatedly processing the same email.
No progress has been made across three processing attempts.
When Cortex is stuck, it should:
Stop processing the email.
Avoid creating an incomplete or misleading draft.
Record the failed step and reason.
Mark the email for human review.
Continue to the next email rather than stopping the entire inbox run.
- **Escalate to human**: Cortex should stop normal drafting and escalate the email to a human when:
It cannot confidently determine whether the email is an issue or enhancement request.
The email mentions a security incident, privacy concern, unauthorized access, or data loss.
The email raises legal, regulatory, compliance, or contractual concerns.
The sender requests a refund, compensation, service credit, or exception.
The sender asks for a release date, roadmap commitment, delivery promise, or guarantee.
The email appears to report a critical outage or widespread customer impact.
The sender threatens legal action, executive escalation, cancellation, or public criticism.
The message comes from an executive, regulator, legal representative, or other sensitive stakeholder.
The response requires access to technical, customer, or product information Cortex does not have.
The email contains sensitive personal, financial, health, or customer data.
A reply would require Cortex to guess at the cause of an issue.
A reply would communicate that a bug will be fixed or an enhancement will be delivered.
The existing email thread already contains conflicting commitments or sensitive discussion.
For escalated messages, Cortex may create a brief internal summary, but it should not create a customer-facing response that could be mistaken for an approved answer.

## State

Cortex maintains per-email thread state for 30 days to track which emails have already been processed, their classification (issue, enhancement request, unclear, or unrelated), whether a draft response was created, the processing status (pending review, escalated, or complete), and any errors encountered during processing. This prevents duplicate processing and allows Cortex to resume work if a run is interrupted.

## The five components

- **Work tree**: For each email, Cortex uses a separate per-message workspace containing:
The email subject, sender, and body
Relevant thread history
The proposed classification
A short summary
The draft response
Validation results and escalation notes
This prevents information from one email thread from being mixed with another.
Not needed at full complexity yet, because each lab run handles a small, bounded email task. A lightweight per-message scratch space is sufficient.
- **Skills**: Cortex needs a small set of reusable skills:
classify-email: determine whether the message is an issue, enhancement request, unclear, or unrelated
summarize-request: create a concise summary of the sender’s need
draft-issue-response: prepare a response for a reported issue
draft-enhancement-response: prepare a response for an enhancement request
draft-clarification-response: request more information when the message is unclear
check-for-commitments: detect promises, dates, guarantees, or unsupported claims
detect-escalation-risk: identify security, legal, privacy, outage, or sensitive stakeholder concerns
Only basic skills are needed now, because Cortex is classifying and drafting rather than planning or executing a complex sequence of actions.
- **Plugins / connectors**: Cortex needs a Gmail connector with permission to:
Detect or search for new, unread, and unprocessed emails
Read the sender, subject, email body, and thread history
Create a reply draft in the correct thread
Apply internal processing labels or another processed marker
Check whether a draft already exists
The Gmail connector must have read and draft permissions only. Cortex must not have permission to send emails.
For the lab version, Cortex does not need Jira, Teams, a CRM, a data warehouse, or engineering systems.
- **Subagents**: Not needed yet, because every draft will be reviewed by a human before it is sent, and the task has a narrow definition of done.
As autonomy increases, Cortex could use a policy-check subagent to independently confirm that a draft:
Contains no unsupported promises
Includes no release-date or roadmap commitments
Does not claim a root cause without evidence
Uses an appropriate and professional tone
Does not expose sensitive information
- **State tracking**: Cortex should retain enough state to prevent duplicate processing and support recovery from failures.
For each email or thread, it should track:
Gmail message and thread identifier
Whether the message has already been reviewed
Classification and confidence
Whether a draft was created
Draft status: created, awaiting review, edited, or sent by a human
Number of failed read or draft attempts
Last completed processing step
Escalation reason, when applicable
Processing timestamp
State should be scoped per email thread so that replies in the same conversation remain connected.

## Context plan

## Context plan

For each iteration, Cortex builds a small, thread-specific context package.

**Written:** Cortex writes the email classification, a short summary, confidence level, escalation flags, and the proposed reply draft.

**Selected:** Cortex includes only the current email, relevant messages from the same Gmail thread, sender information, and the stored processing state for that thread.

**Compressed:** Long email threads are reduced to a concise summary containing the original request, important follow-up details, prior commitments, and unresolved questions.

**Isolated:** Each email thread is processed in its own workspace so content, classifications, and drafts from different customers or conversations cannot be mixed.

After the iteration, only the required state and draft status persist; temporary reasoning and unrelated email content are discarded.

## Hand-off to bounds and evals (M5)

In Module 5, Cortex will be tested against explicit safety bounds and quality evaluations before any increase in autonomy.
The bounds will confirm that Cortex can read and classify emails, create drafts, and mark items for review, but cannot send messages, make commitments, expose sensitive information, or process high-risk requests without human involvement.
The evaluations will measure classification accuracy, draft quality, escalation accuracy, duplicate-processing prevention, and compliance with the human-approval requirement.

## Debrief (jot it for yourself)

## Debrief

The **escalate-to-human stop condition** is what keeps commitments safe. Cortex must stop when an email asks for a delivery date, roadmap promise, refund, guarantee, policy exception, or any response that could commit the product team or company.

If Cortex were allowed to post under a defined threshold, the loop would need stricter bounds and evaluations. It could send only low-risk responses, such as acknowledgments or requests for clarification, when confidence is high and no commitment, sensitive topic, or escalation signal is present. Anything outside that threshold would still be drafted and routed to a human for approval.
