class KnowledgeUnavailableError(Exception):
    """Search or embeddings cannot be reached right now."""


class SourceRejectedError(Exception):
    """A source is not on the trusted list, or cannot be used."""
