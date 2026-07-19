# Agent-Line Map: Cortex

## Decisions, scored

| # | Decision | Reversibility | Blast radius | Measurability | Verdict |
|---|---|---|---|---|---|
| 1 | Pull a project’s state and recent activity | High | Low | High | Below |
| 2 | Decide which past updates / context are relevant | High | Low | Med | Below |
| 3 | Draft the leadership status update | High | Low | High | Below |
| 4 | Decide the tone / commitment level of the update | Low | Med | Med | Above |
| 5 | Choose which risk call to escalate | Med | Med | Med | HITL |
| 6 | Propose a story batch within the cap | Med | Med | Low | HITL |
| 7 | Post an update, or approve a company-wide one | Low | High | Low | Above |

## One-line justifications

1. **Pull a project’s state and recent activity** (Below): Read-only and checkable, so Cortex owns it.
2. **Decide which past updates / context are relevant** (Below): Cheap to correct and low-risk; a wrong pick just makes a weaker draft.
3. **Draft the leadership status update** (Below): Nothing leaves the building until a human sends, so Cortex owns the draft.
4. **Decide the tone / commitment level of the update** (Above): All three axes are middling, so a human confirms the call.
5. **Choose which risk call to escalate** (HITL): All three axes are middling, so a human confirms the call.
6. **Propose a story batch within the cap** (HITL): A commitment is hard to walk back and tone is fuzzy to measure, human approves.
7. **Post an update, or approve a company-wide one** (Above): Irreversible and high blast radius, a human owns this, always.
