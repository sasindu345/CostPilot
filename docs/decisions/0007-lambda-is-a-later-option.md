# 0007: Keep everything on EC2 for now, and review Lambda later

**Status:** Deferred, 2 Nov 2026. Review after Phase 8.

**Situation.** We asked if the AI assistant should run on AWS Lambda or Fargate instead of EC2.

**Decision.** Stay on EC2 for now. After Phase 8, measure real memory use and answer speed, then decide.

**Why not now.**
- The assistant mostly waits for Gemini, so it gains little from more server power.
- Lambda inside the private network needs a NAT gateway to reach Gemini and Qdrant, which costs money. Outside it, Lambda cannot safely reach our database without extra API code.
- Python on Lambda has no built-in response streaming, so live answers need an add-on.
- Keycloak and PostgreSQL must run all the time, so EC2 stays either way.
- Fargate has no free allowance listed, which breaks the $0 goal.

**Options to review later.**

| Option | When it makes sense | Work needed |
|---|---|---|
| Stay on EC2 | The server copes with real use | None |
| Bill processing on Lambda | Large bills strain the 2 GB server | Small. `JobRunner.process` already knows nothing about the queue |
| AI assistant on Lambda | Many people chat at once | Medium: streaming, cold starts, and a private data API |
| Fargate | Paid hosting is acceptable | Medium: new Terraform, and a load balancer if needed |

**Check before choosing.** Confirm whether Lambda's free allowance is permanent for your account.
