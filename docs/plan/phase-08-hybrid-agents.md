# Phase 8: Hybrid agents

**You will see:** deeper answers from specialist agents, proven better than the Phase 7 baseline, while simple questions cost no more than before.

**Rule for this phase:** an AI agent stays only if it beats the Phase 7 baseline on the test questions. Keep the scores in `docs/logs/BUILD-LOG.md`.

**Python tools first**
- [ ] Breakdown tools: cost by usage type, region and resource
- [ ] Recommendation rules, with provable savings or "Needs usage data"
- [ ] Recommendations on the Overview page
- [ ] Provider profiles: each cloud supplies its documents and rules, so no new agents are needed later
- [ ] Shared document retrieval, run once per question

**Agents**
- [ ] Supervisor upgrade: returns intent, specialists and cloud in a checked format
- [ ] Anomaly Agent: Python detector first, and AI only if something was found and line detail exists
- [ ] Optimization Agent: its own instructions and tools, using validated bill facts and documents
- [ ] Knowledge Agent: AI for pure documentation questions only
- [ ] Final Response Agent: receives validated findings only
- [ ] Cost Specialist stays Python. Add AI reasoning only if the scores show a real gap

**Limits and proof**
- [ ] Limit of 4 AI calls per question, as a setting
- [ ] If a specialist fails or the limit is reached, the answer still goes out using Python facts
- [ ] Compare each AI agent with the baseline, and remove any that does not help
- [ ] Workspace isolation, privacy and audit tests cover every new agent
- [ ] Review the Lambda options in decision 0007, using real memory and speed numbers

## Finish this phase

- [ ] All items above are ticked, or the change is explained
- [ ] `docs/plan/ROADMAP.md` is updated
- [ ] `docs/logs/BUILD-LOG.md` has a dated entry
- [ ] `make check` passes
