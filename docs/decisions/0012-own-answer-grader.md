# 0012: Grade answers with our own small grader, not DeepEval or Ragas

**Status:** Accepted, 3 Nov 2026

**Situation.** The plan said "AI quality tests with DeepEval or Ragas". Both use a second AI model as a judge. Both also bring many extra packages, and both expect OpenAI by default. DeepEval also sends usage data to its company unless you switch it off.

**Decision.** `scripts/eval_quality.py` asks a second Gemini model to compare each answer with a reference answer. It scores correctness, completeness, relevance and clarity from 1 to 5. An answer passes when correctness and relevance are both at least 4. The reference answers live in `knowledge/quality-cases.yaml`.

**Why.**

- The measures are the same ideas those tools use, written in about 30 lines that anyone can read.
- No new packages, and nothing is sent anywhere except Gemini.
- The judge model is a setting, `GEMINI_JUDGE_MODEL`, so a stronger model can be used without code changes.

**What the first runs showed (3 Nov 2026).**

| Run | Passed | Notes |
|---|---|---|
| 1 | 10 of 12 | Found a real bug: "Which month cost the most?" said October. It was September |
| After the fix | 9 of 12 | The month question now scores 5 of 5. Two of the three failures were the judge marking down extra true detail. One was a real weak answer about RDS |

The fix: code now works out the highest and lowest months and gives them to the AI as facts. The number checks could not catch the bug, because no wrong number was typed. Only the meaning was wrong.

**Trade-offs.**

- The judge is the same small model that writes the answers, and its scores change from run to run. Use a stronger judge model once you have a paid key.
- The reference answers count as human-checked only after a person checks them and fills in `checked_by`. None are checked yet.
- Twelve questions show direction, not general quality.
