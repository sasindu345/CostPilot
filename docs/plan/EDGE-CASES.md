# Edge cases

Unusual situations and how CostPilot handles them. Add new ones as you find them, with a test.

| Situation | What happens | Phase |
|---|---|---|
| Same file uploaded twice | Detected by its fingerprint; the user is told and nothing is counted twice | 2 |
| Two files cover the same month | The newest or more detailed file wins; the other is marked "Replaced" | 3 |
| AWS updates a bill after month end | The new version replaces the old one | 3 |
| Wrong or broken file | Rejected with a clear reason, and the row number where possible | 2, 3 |
| Very large file or compressed bomb | Size limits and read-in-chunks | 2 |
| Upload fails halfway | The job can be retried safely, with no half-saved data | 2 |
| Credits, refunds, tax, Savings Plans, reserved instances | Handled as separate charge types, using FOCUS rules | 3 |
| Different currencies | Never added together; shown separately | 3, 4 |
| Formula tricks in a CSV | Cleaned when read and when exported | 2 |
| Summary-only file (Cost Explorer) | The AI knows it has no detail and says so honestly | 6 |
| Gemini rate limit or downtime | Retry, then a clear message; dashboards keep working | 6 |
| Qdrant asleep | The AI still answers bill questions and says documents were unavailable | 6 |
| Document deleted | Its data, summaries and file are removed, and totals are recalculated | 2, 4 |
| User asks about other users or tries to break the AI | Blocked and logged | 7 |
| New user with no data | Friendly empty screens and a sample-data option | 4 |
