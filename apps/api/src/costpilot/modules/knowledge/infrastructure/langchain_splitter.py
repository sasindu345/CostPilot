from langchain_text_splitters import RecursiveCharacterTextSplitter


class LangChainTextSplitter:
    def __init__(self, chunk_size: int, chunk_overlap: int) -> None:
        self._splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, chunk_overlap=chunk_overlap
        )

    def split(self, text: str) -> list[str]:
        return self._splitter.split_text(text)
