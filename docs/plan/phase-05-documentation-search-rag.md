# Phase 5: Documentation search (RAG)

**You will see:** a test search returns the right AWS advice.
- [x] `knowledge/sources.yaml`: the list of trusted documents
- [x] Load, split, create embeddings, save to Qdrant, tagged by provider
- [x] `make reindex`, safe to run repeatedly
- [x] Search with a relevance check
- [x] Starter set of test questions, to measure search quality
- [x] Weekly job to keep the free Qdrant cluster awake

**Result with real Gemini embeddings:** `make eval-search` found an expected source for 10 of 10 questions. The target is 80%.

## Finish this phase

- [x] All items above are ticked, or the change is explained
- [x] `docs/plan/ROADMAP.md` is updated
- [x] `docs/logs/BUILD-LOG.md` has a dated entry
- [x] `make check` passes
