# Phase 5: Documentation search (RAG)

**You will see:** a test search returns the right AWS advice.
- [x] `knowledge/sources.yaml`: the list of trusted documents
- [ ] Load, split, create embeddings, save to Qdrant, tagged by provider
- [ ] `make reindex`, safe to run repeatedly
- [x] Search with a relevance check
- [x] Starter set of test questions, to measure search quality
- [x] Weekly job to keep the free Qdrant cluster awake

**Waiting for a Gemini key.** The two open items are built and tested with a fake embedder, a real Qdrant and the real AWS pages. Only real embeddings are missing. To finish:

1. Create a key at https://aistudio.google.com/apikey.
2. Add it to `.env` as `GEMINI_API_KEY=...`.
3. Run `make reindex`, then `make eval-search`. The target is 80%.

`search_min_score` may need adjusting once real scores are known. The embedding model also needs confirming, as a change of model means indexing everything again.

## Finish this phase

- [ ] All items above are ticked, or the change is explained
- [ ] `docs/plan/ROADMAP.md` is updated
- [ ] `docs/logs/BUILD-LOG.md` has a dated entry
- [ ] `make check` passes
