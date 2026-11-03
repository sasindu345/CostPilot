# Phase 9: Other clouds

**You will see:** a bill from each cloud shows up in the same dashboard.
- [x] FOCUS reader tested with Azure, Google Cloud and Oracle samples, using `ProviderName` and the newer `ServiceProviderName`
- [x] Native readers for Azure, Google Cloud and Oracle
- [x] DigitalOcean invoice reader
- [x] Provider filter in the dashboard
- [x] Documentation for each cloud added to Qdrant
- [x] Provider profiles and recommendation rules for each cloud. DigitalOcean has a profile but no rules, as it has no commitment discounts or cost advice to cite

**Added during the work:** a question can name several clouds, and one search covers them all. The Knowledge Agent was re-tested on harder questions and stays off. See decision 0010.

**Not yet tested:** none of the six readers has seen a real bill from its cloud. All formats come from official documentation, checked on 3 Nov 2026.

## Finish this phase

- [x] All items above are ticked, or the change is explained
- [x] `docs/plan/ROADMAP.md` is updated
- [x] `docs/logs/BUILD-LOG.md` has a dated entry
- [x] `make check` passes
