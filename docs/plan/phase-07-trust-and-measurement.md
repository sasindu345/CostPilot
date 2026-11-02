# Phase 7: Trust and measurement

**You will see:** every answer shows its evidence and grade, and we can measure answer quality, speed and cost with real numbers.

This phase comes before the hybrid agents in Phase 8, because more AI-written text needs a checker first. See [decision 0010](../decisions/0010-hybrid-agents-after-trust-layer.md).

**Measure first**
- [x] Time every step of an answer, and find the cause of the 15 to 25 second answers
- [x] Record AI calls, input tokens, output tokens and time for each question in the audit log
- [x] Scored test questions covering routes, correct figures, sources, refusals and honest "I do not know" answers
- [x] `make eval-assistant`, and a saved baseline score for Phase 8 to beat

**Trust layer**
- [x] Findings format in Pydantic: each claim lists the fact ids and documents behind it
- [x] Evidence Validator: rejects unknown fact ids, unknown documents and typed numbers before the final answer
- [x] Answer Checker with a retry and a template fallback, which also covers numbers copied from chat history
- [x] Evidence grades A to D, given by code
- [x] Coded protection against prompt injection in questions, bills and documents
- [x] "How was this answer made?" view from the audit records

**Result.** `make eval-assistant` scored 15 of 15, saved in `knowledge/assistant-baseline.json`. See the limits in [technical verification](../architecture/technical-verification.md).

**Changed from the plan.** Answers are now checked before they are shown, so the text appears all at once, not word by word. A wrong number must never be visible, even for a moment.

## Finish this phase

- [x] All items above are ticked, or the change is explained
- [x] `docs/plan/ROADMAP.md` is updated
- [x] `docs/logs/BUILD-LOG.md` has a dated entry
- [x] `make check` passes
