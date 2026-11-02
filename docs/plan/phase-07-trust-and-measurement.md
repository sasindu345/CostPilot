# Phase 7: Trust and measurement

**You will see:** every answer shows its evidence and grade, and we can measure answer quality, speed and cost with real numbers.

This phase comes before the hybrid agents in Phase 8, because more AI-written text needs a checker first. See [decision 0010](../decisions/0010-hybrid-agents-after-trust-layer.md).

**Measure first**
- [ ] Time every step of an answer, and find the cause of the 15 to 25 second answers
- [ ] Record AI calls, input tokens, output tokens and time for each question in the audit log
- [ ] Scored test questions covering routes, correct figures, sources, refusals and honest "I do not know" answers
- [ ] `make eval-assistant`, and a saved baseline score for Phase 8 to beat

**Trust layer**
- [ ] Findings format in Pydantic: each claim lists the fact ids and documents behind it
- [ ] Evidence Validator: rejects unknown fact ids, unknown documents and typed numbers before the final answer
- [ ] Answer Checker with a retry and a template fallback, which also covers numbers copied from chat history
- [ ] Evidence grades A to D, given by code
- [ ] Coded protection against prompt injection in questions, bills and documents
- [ ] "How was this answer made?" view from the audit records

## Finish this phase

- [ ] All items above are ticked, or the change is explained
- [ ] `docs/plan/ROADMAP.md` is updated
- [ ] `docs/logs/BUILD-LOG.md` has a dated entry
- [ ] `make check` passes
