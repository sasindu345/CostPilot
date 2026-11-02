# Edge cases

Unusual situations and how CostPilot handles them. Add new ones as you find them, with a test.

The Phase column shows where each one was or will be built. Items for Phase 6 and 7 are not built yet.

| Situation | What happens | Phase |
|---|---|---|
| Same file uploaded twice | Detected by its fingerprint; the user is told and nothing is counted twice | 2 |
| Two files cover the same month | The newest or more detailed file wins; the other is marked "Replaced" | 3 |
| AWS updates a bill after month end | The new version replaces the old one | 3 |
| Wrong or broken file | Rejected with a clear reason, and the row number where possible | 2, 3 |
| Very large file or compressed bomb | Size limits, and reading stops once a file unpacks too large | 2 |
| Upload fails halfway | The job can be retried safely, with no half-saved data | 2 |
| Credits, refunds, tax, Savings Plans, reserved instances | Handled as separate charge types, using FOCUS rules | 3 |
| Different currencies | Never added together; shown separately | 3, 4 |
| Formula tricks in a CSV | File names are cleaned on upload, and bill text is cleaned when read. Exports arrive in Phase 10 | 2, 3 |
| Summary-only file (Cost Explorer) | Each record stores its detail level. The AI uses this from Phase 6 | 3, 6 |
| Gemini rate limit or downtime | Embeddings already retry. Chat follows in Phase 6; dashboards do not use Gemini | 5, 6 |
| Qdrant asleep | Search reports it is unavailable and never crashes. The AI uses this from Phase 6 | 5, 6 |
| Document deleted | Its data, summaries and file are removed, and totals are recalculated | 2, 4 |
| User asks about other users or tries to break the AI | Blocked and logged | 7 |
| New user with no data | Friendly empty screens and a sample-data option | 4 |
| User cancels at Keycloak | They return to the app, with no error page | 1 |
| Half-finished month | Compared with the same days of last month, or no percentage if the file has no daily data | 4 |
| Month with no bill | Stays empty, and is never shown as $0 | 4 |
| Document deleted while processing | The job stops safely | 2 |
| Worker crashes during a job | The job returns to the queue | 2 |
| Source page redirects off a trusted site | Refused | 5 |
