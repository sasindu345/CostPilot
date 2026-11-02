# 0010: Build hybrid agents after the trust layer

**Status:** Accepted, 2 Nov 2026

**Situation.** In Phase 6, only the supervisor and the final answer use AI. Specialists are plain code. We want deeper reasoning from specialist AI agents, while keeping money exact and AI calls low.

**Decision.** Build a hybrid system in two phases.

| Part | Type |
|---|---|
| Supervisor | AI, returns intent, specialists and cloud |
| Cost Specialist | Python. AI is added only if test scores show a gap |
| Anomaly Agent | Python detector first. AI only if something was found and line detail exists |
| Optimization Agent | AI, with its own instructions and tools |
| Knowledge Agent | AI, for pure documentation questions only |
| Document retrieval | Python, run once and shared |
| Evidence Validator and Answer Checker | Python |
| Final Response Agent | AI, receives validated findings only |

Phase 7 builds measurement and the trust layer. Phase 8 builds the agents. Each question has a limit of 4 AI calls, set in settings. If a specialist fails or the limit is reached, the answer still goes out using Python facts. All agents share one Gemini model at first.

**Why.**
- More AI-written text means more places for a wrong claim, so the checker must exist first.
- An AI can only guess at causes from monthly totals, so the Anomaly Agent needs breakdown tools.
- A shared retrieval step avoids repeat searches and a repeat AI call.
- Measuring against a baseline proves that each agent helps.

**Measured before deciding.** A router call took 1 to 2 seconds and about 120 tokens. An answer call with five document chunks used 1,347 input tokens. A four-call question is estimated at about $0.003, so money is not the main limit. Speed and free limits are. Google shows exact free limits in AI Studio, and they apply per project.

**Trade-offs.** New agents arrive later. A two-part question uses 4 AI calls instead of 2. The test question set is more work, and the free key limits how often it can run.
