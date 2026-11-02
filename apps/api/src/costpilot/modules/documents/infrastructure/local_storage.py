import asyncio
import shutil
from pathlib import Path


class LocalFileStorage:
    """Keeps files in a folder. Used during development."""

    def __init__(self, root: str) -> None:
        self._root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self._root / key).resolve()
        if not path.is_relative_to(self._root):
            raise ValueError("Storage key leaves the storage folder")
        return path

    async def put(self, key: str, source: Path) -> None:
        path = self._path(key)
        await asyncio.to_thread(path.parent.mkdir, parents=True, exist_ok=True)
        await asyncio.to_thread(shutil.copyfile, source, path)

    async def fetch(self, key: str, destination: Path) -> None:
        await asyncio.to_thread(shutil.copyfile, self._path(key), destination)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self._path(key).unlink, missing_ok=True)
