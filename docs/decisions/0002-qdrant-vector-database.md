# 0002: Use Qdrant for documentation search

**Status:** Accepted, 2 Nov 2026

**Situation.** The AI needs to search trusted cloud documentation. The brief suggested ChromaDB. pgvector would add no new service, but the owner has already used it and wants to learn a dedicated vector database.

**Decision.** Use Qdrant: a local container in development, and the free Qdrant Cloud plan in production. The code uses an interface, so it can be replaced.

**Why.** The free cloud plan (1 GB memory, 4 GB disk) saves memory on our small server, and it filters by provider well.

**Trade-offs.** Free clusters are paused after a week without use and deleted after four weeks. A weekly job keeps it awake, and `make reindex` rebuilds it, as it only holds public documentation. If it is down, the AI still answers bill questions and says documents were unavailable.
