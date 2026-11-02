# 0009: Use gemini-3.5-flash-lite for answers

**Status:** Accepted, 2 Nov 2026

**Situation.** The plan used `gemini-3.8-flash` for answers. On the free plan it failed all four test calls with timeouts and "high demand" errors. `gemini-3.5-flash-lite` answered all four test calls in 1 to 3 seconds.

**Decision.** Use `gemini-3.5-flash-lite` for answers and routing. The model is a setting, so `GEMINI_ANSWER_MODEL` can change it at any time.

**Why.** A reliable answer matters more here than a more capable model, as the facts come from our own code.

**Trade-offs.** Answers may be plainer. Review this with a paid key.
