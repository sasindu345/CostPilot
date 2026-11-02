# Phase 8: Hybrid agents

**You will see:** deeper answers from specialist agents, proven better than the Phase 7 baseline, while simple questions cost no more than before.

**Rule for this phase:** an AI agent stays only if it beats the Phase 7 baseline on the test questions. Keep the scores in `docs/logs/BUILD-LOG.md`.

**Python tools first**
- [x] Breakdown tools: cost by usage type and region, with a resource count. Resource names never reach the AI (Rule 7)
- [x] Recommendation rules, with provable savings or "Needs usage data"
- [x] Recommendations on the Overview page
- [x] Provider profiles: each cloud supplies its documents and rules, so no new agents are needed later
- [x] Shared document retrieval, run once per question

**Agents**
- [x] Supervisor upgrade: returns intent, specialists and cloud in a checked format
- [x] Anomaly Agent: Python detector first, and AI only if something was found and line detail exists
- [x] Optimization Agent: its own instructions and tools, using validated bill facts and documents
- [x] Knowledge Agent: built, but **off by default**, because it did not beat the baseline
- [x] Final Response Agent: receives validated findings only
- [x] Cost Specialist stays Python. Add AI reasoning only if the scores show a real gap

**Limits and proof**
- [x] Limit of 4 AI calls per question, as a setting
- [x] If a specialist fails or the limit is reached, the answer still goes out using Python facts
- [x] Compare each AI agent with the baseline, and remove any that does not help
- [x] Workspace isolation, privacy and audit tests cover every new agent
- [x] Review the Lambda options in decision 0007, using real memory and speed numbers

## Result

Scored with real Gemini. The scores are in `knowledge/eval-*.json`.

| Test | Without AI specialists | With them |
|---|---|---|
| 10 hard questions | 6 passed | 10 passed |
| Average AI calls | 2.1 | 3.0 |
| Average tokens | 1,364 in, 138 out | 3,294 in, 311 out |

| Agent | Result | Decision |
|---|---|---|
| Anomaly | Fixed the questions about the cause of a rise | Kept |
| Optimization | Fixed the question that matches a user's services to advice | Kept |
| Knowledge | 3 of 3 with or without it | Off by default |

The Knowledge Agent can be turned back on with `ASSISTANT_AI_SPECIALISTS`.

## Finish this phase

- [x] All items above are ticked, or the change is explained
- [x] `docs/plan/ROADMAP.md` is updated
- [x] `docs/logs/BUILD-LOG.md` has a dated entry
- [x] `make check` passes
