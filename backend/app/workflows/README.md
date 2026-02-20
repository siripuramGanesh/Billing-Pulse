# Workflows

Workflows orchestrate multi-step business logic using [LangGraph](https://github.com/langchain-ai/langgraph).

## Post-call workflow

**Trigger:** Vapi webhook `end-of-call-report`.

**Graph:** `extract` → `apply` → `decide_follow_up` → (optional) `schedule` → END.

1. **extract** – LLM extraction from transcript (with RAG for denial codes / payer policies).
2. **apply** – Update claim and call record with extracted outcome (or fallback from ended reason).
3. **decide_follow_up** – If `next_steps`/summary mention callback/follow-up (e.g. "call back in 3 days"), set `schedule_after` and `schedule_reason`.
4. **schedule** – If `schedule_after` is set, create a `ScheduledCall` (Celery Beat will enqueue the call when due).

Follow-up detection uses keywords: `call back`, `callback`, `follow up`, `in N days`, `next week`, `recheck`, etc. The number of days is parsed from phrases like "in 3 days" (default 5, max 30).

## Extending

- Add nodes (e.g. "notify_staff", "escalate_appeal") and conditional edges in `post_call_workflow.py`.
- Add new workflows (e.g. pre-call prep, appeal pipeline) as new modules and register in `__init__.py`.
